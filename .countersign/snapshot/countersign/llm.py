"""Model-agnostic reviewer runner: any OpenAI-compatible chat-completions endpoint, stdlib only (urllib).

    countersign review-llm <change> --reviewer nemotron|gemini     stage 2: a structured review from a model API
    countersign adjudicate <change>                                 disputes only: the adjudicator's rulings

    preset    base URL                                                    key env          default model
    nemotron  https://integrate.api.nvidia.com/v1                         NVIDIA_API_KEY   nvidia/nemotron-3.5-super-vl-120b-a12b
    gemini    https://generativelanguage.googleapis.com/v1beta/openai/    GEMINI_API_KEY   gemini-4-hydrogen (COUNTERSIGN_GEMINI_MODEL)

COUNTERSIGN_<NAME>_BASE_URL / COUNTERSIGN_<NAME>_MODEL override a preset (e.g. a self-hosted Nemotron for a
confidential repo). The prompt is a versioned file (prompts/review-v1.md); the runner builds the context itself and
stamps reviewer/model/vendor/prompt_version/reviewed_at, so none of that is ever taken from the model.
API keys are read from the environment only and are never written to files, logs or error messages.
"""

from __future__ import annotations

import json
import os
import random
import re
import subprocess
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from . import costs, decide as decide_mod, mandate as mandate_mod
from .common import Workspace, is_mutant, read_json, sha256_hex, write_json

REVIEW_PROMPT = "review-v1"
ADJUDICATE_PROMPT = "adjudicate-v1"
DEFAULT_CONTEXT_CHARS = 180_000  # ~50k tokens: room for the answer and reasoning on free tiers
RETRY_STATUS = {408, 409, 425, 429, 500, 502, 503, 504, 529}
VERDICTS = {"met", "not_met", "cannot_determine"}
SEVERITIES = {"blocker", "major", "minor", "info"}
CATEGORIES = {"correctness", "security", "performance", "maintainability", "docs", "tests", "scope"}
EVIDENCE_KINDS = {"code", "test", "check", "requirement", "issue"}

PRESETS: dict[str, dict] = {
    # Nemotron 3.5 Super (open weights, 120B MoE / 12B active) on NVIDIA's API catalog. Free tier ~40 req/min.
    # Reasoning is a chat-template switch; on for reviews (deliberation is the job), off for the JSON repair turn.
    "nemotron": {"base_url": "https://integrate.api.nvidia.com/v1", "key_env": "NVIDIA_API_KEY",
                 "model": "nvidia/nemotron-3.5-super-vl-120b-a12b", "vendor": "NVIDIA", "provider": "nvidia",
                 "temperature": 0.6, "top_p": 0.95, "max_tokens": 32768,  # reasoning tokens count here: 16k cut a review off
                 "thinking": {"chat_template_kwargs": {"enable_thinking": True}},
                 "no_thinking": {"chat_template_kwargs": {"enable_thinking": False}}},
    "gemini": {"base_url": "https://generativelanguage.googleapis.com/v1beta/openai/", "key_env": "GEMINI_API_KEY",
               "model": "gemini-4-hydrogen", "model_env": "COUNTERSIGN_GEMINI_MODEL", "vendor": "Google", "provider": "google",
               "temperature": None, "top_p": None, "max_tokens": 16384,
               "thinking": {"reasoning_effort": "medium"}, "no_thinking": {"reasoning_effort": "low"}},
}


class LLMError(RuntimeError):
    """A provider or parsing failure. The message never contains the API key."""


@dataclass
class LLMConfig:
    name: str
    base_url: str
    model: str
    vendor: str
    provider: str
    api_key: str = field(default="", repr=False)
    temperature: float | None = None
    top_p: float | None = None
    max_tokens: int | None = 16384
    timeout_s: float = 600.0
    max_retries: int = 6
    thinking: dict = field(default_factory=dict)
    no_thinking: dict = field(default_factory=dict)
    hosted_default: bool = True  # False when the base URL was overridden (e.g. a self-hosted endpoint)


def config(name: str, env: dict | None = None) -> LLMConfig:
    env = os.environ if env is None else env
    if name not in PRESETS:
        raise SystemExit(f"unknown reviewer preset {name!r}; use one of {sorted(PRESETS)}")
    p = PRESETS[name]
    up = name.upper()
    base = env.get(f"COUNTERSIGN_{up}_BASE_URL") or p["base_url"]
    model = env.get(f"COUNTERSIGN_{up}_MODEL") or (env.get(p["model_env"]) if p.get("model_env") else None) or p["model"]
    return LLMConfig(name=name, base_url=base.rstrip("/"), model=model, vendor=p["vendor"], provider=p["provider"],
                     api_key=env.get(f"COUNTERSIGN_{up}_API_KEY") or env.get(p["key_env"], ""),
                     temperature=p["temperature"], top_p=p["top_p"],
                     max_tokens=int(env.get("COUNTERSIGN_MAX_TOKENS") or p["max_tokens"]),
                     thinking=p["thinking"], no_thinking=p["no_thinking"],
                     hosted_default=not env.get(f"COUNTERSIGN_{up}_BASE_URL"))


# --- HTTP ---------------------------------------------------------------------------------------

def urllib_post(url: str, body: bytes, headers: dict, timeout: float) -> tuple[int, dict, bytes]:
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, dict(r.headers), r.read()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers or {}), e.read() or b""


@dataclass
class ChatResult:
    content: str
    finish_reason: str | None
    usage: dict
    raw: dict
    latency_ms: int
    retries: int


class ChatClient:
    """chat(messages) -> ChatResult with retries and backoff on 429 / 5xx / network errors.
    `post` is injectable (tests pass a stub); `sleep` too."""

    def __init__(self, cfg: LLMConfig, post=urllib_post, sleep=time.sleep):
        self.cfg, self._post, self._sleep = cfg, post, sleep

    def chat(self, messages: list[dict], thinking: bool = True) -> ChatResult:
        c = self.cfg
        body: dict = {"model": c.model, "messages": messages}
        for k in ("temperature", "top_p", "max_tokens"):
            if getattr(c, k) is not None:
                body[k] = getattr(c, k)
        body.update(c.thinking if thinking else c.no_thinking)
        headers = {"Content-Type": "application/json", "Accept": "application/json", "User-Agent": "countersign"}
        if c.api_key:
            headers["Authorization"] = f"Bearer {c.api_key}"
        url = f"{c.base_url}/chat/completions"
        data = json.dumps(body).encode()
        t0, last = time.perf_counter(), ""
        for attempt in range(c.max_retries + 1):
            try:
                status, hdrs, raw = self._post(url, data, headers, c.timeout_s)
            except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as e:
                status, hdrs, raw, last = None, {}, b"", type(e).__name__
            if status == 200:
                try:
                    payload = json.loads(raw)
                except ValueError as e:
                    raise LLMError(f"{c.name}: response is not JSON ({e})") from None
                choice = (payload.get("choices") or [{}])[0]
                msg = choice.get("message") or {}
                content = msg.get("content")
                if isinstance(content, list):
                    content = "".join(x.get("text", "") for x in content if isinstance(x, dict))
                u = payload.get("usage") or {}
                return ChatResult(content=content or "", finish_reason=choice.get("finish_reason"),
                                  usage={k: int(u.get(k) or 0) for k in ("prompt_tokens", "completion_tokens", "total_tokens")},
                                  raw=payload, latency_ms=round((time.perf_counter() - t0) * 1000), retries=attempt)
            if status is not None:
                last = f"HTTP {status}: {raw[:300].decode('utf-8', 'replace')}"
                if status not in RETRY_STATUS:
                    break
            if attempt == c.max_retries:
                break
            self._sleep(_retry_after(hdrs) or _backoff(attempt))
        raise LLMError(f"{c.name} ({c.model}) chat completion failed: {last}".replace(c.api_key or "\0", "***"))


def _backoff(attempt: int) -> float:
    return min(60.0, 2.0 * 2 ** attempt) * (0.8 + 0.4 * random.random())


def _retry_after(headers: dict) -> float | None:
    v = next((v for k, v in headers.items() if k.lower() == "retry-after"), None)
    try:
        return min(120.0, float(v)) if v is not None else None
    except ValueError:
        return None


# --- JSON parsing -------------------------------------------------------------------------------

def extract_json(text: str):
    """Strip <think> blocks and Markdown fences, then parse the outermost JSON object."""
    t = re.sub(r"<think>.*?</think>", "", text or "", flags=re.S).strip()
    fence = re.search(r"```(?:json)?\s*(.*?)```", t, flags=re.S)
    if fence and "{" in fence.group(1):
        t = fence.group(1)
    start, end = t.find("{"), t.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("no JSON object found in the response")
    return json.loads(t[start:end + 1])


def _evidence_problems(items, where: str) -> list[str]:
    if not isinstance(items, list):
        return [f"{where}.evidence must be a list"]
    out = []
    for i, e in enumerate(items):
        if not isinstance(e, dict) or e.get("kind") not in EVIDENCE_KINDS:
            out.append(f"{where}.evidence[{i}] needs kind in {sorted(EVIDENCE_KINDS)}")
    return out


def review_problems(r, req_ids: list[str]) -> list[str]:
    """Shape errors that justify the one repair retry (content is judged by the verifier, not here)."""
    if not isinstance(r, dict):
        return ["top level must be a JSON object"]
    p = []
    vs = r.get("requirement_verdicts")
    if not isinstance(vs, list):
        p.append("requirement_verdicts must be a list")
        vs = []
    for i, v in enumerate(vs):
        if not isinstance(v, dict) or v.get("req") not in req_ids or v.get("verdict") not in VERDICTS:
            p.append(f"requirement_verdicts[{i}] needs req in {req_ids} and verdict in {sorted(VERDICTS)}")
            continue
        p += _evidence_problems(v.get("evidence", []), f"requirement_verdicts[{i}]")
    for i, f in enumerate(r.get("findings", []) if isinstance(r.get("findings", []), list) else [None]):
        if not isinstance(f, dict) or f.get("severity") not in SEVERITIES or f.get("category") not in CATEGORIES \
                or not f.get("title") or not f.get("claim"):
            p.append(f"findings[{i}] needs title, claim, severity in {sorted(SEVERITIES)}, category in {sorted(CATEGORIES)}")
            continue
        p += _evidence_problems(f.get("evidence", []), f"findings[{i}]")
    for i, x in enumerate(r.get("refusals", []) if isinstance(r.get("refusals", []), list) else [None]):
        if not isinstance(x, dict) or not x.get("topic") or not x.get("reason"):
            p.append(f"refusals[{i}] needs topic, reason, who_should_decide")
    return p


def adjudication_problems(r, dispute_ids: list[str]) -> list[str]:
    if not isinstance(r, dict) or not isinstance(r.get("rulings"), list):
        return ["top level must be an object with a rulings list"]
    return [f"rulings[{i}].dispute must be one of {dispute_ids}" for i, x in enumerate(r["rulings"])
            if not isinstance(x, dict) or x.get("dispute") not in dispute_ids]


def ask_json(client: ChatClient, system: str, user: str, check, log: list) -> tuple[dict, bool]:
    """One call; if the answer is not valid JSON of the right shape, one repair turn. Returns (parsed, repaired)."""
    messages = [{"role": "system", "content": system}, {"role": "user", "content": user}]
    res = client.chat(messages)
    log.append(res)
    try:
        parsed = extract_json(res.content)
        problems = check(parsed)
    except ValueError as e:
        parsed, problems = None, [str(e)]
    if not problems:
        return parsed, False
    answer = re.sub(r"<think>.*?(</think>|$)", "", res.content, flags=re.S).strip() or "(empty answer)"
    messages += [{"role": "assistant", "content": answer},
                 {"role": "user", "content": "That was not valid JSON for the requested schema: " + "; ".join(problems[:12])
                  + (" (the answer was cut off: finish_reason=length)" if res.finish_reason == "length" else "")
                  + ". Return only the corrected JSON object, nothing else."}]
    res2 = client.chat(messages, thinking=False)
    log.append(res2)
    try:
        parsed = extract_json(res2.content)
        problems = check(parsed)
    except ValueError as e:
        problems = [str(e)]
    if problems:
        raise LLMError(f"{client.cfg.name}: still not valid after one repair: " + "; ".join(problems[:6]))
    return parsed, True


# --- context ------------------------------------------------------------------------------------

def _git(repo: str, *args) -> str | None:
    r = subprocess.run(["git", "-C", repo, *args], capture_output=True)
    return r.stdout.decode("utf-8", "replace") if r.returncode == 0 else None


def _numbered(text: str, ranges: list[tuple[int, int]] | None = None) -> str:
    lines = text.splitlines()
    if not ranges:
        return "\n".join(f"{n:>5}| {line}" for n, line in enumerate(lines, 1))
    out, last = [], 0
    for a, b in ranges:
        a, b = max(1, a), min(len(lines), b)
        if a > last + 1:
            out.append(f"  ... lines {last + 1}-{a - 1} not shown ...")
        out += [f"{n:>5}| {lines[n - 1]}" for n in range(a, b + 1)]
        last = b
    if last < len(lines):
        out.append(f"  ... lines {last + 1}-{len(lines)} not shown ...")
    return "\n".join(out)


def _hunks(diff: str, side: str) -> list[tuple[int, int]]:
    """Changed line ranges from a unified diff: side '+' (head) or '-' (base)."""
    out = []
    for m in re.finditer(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@", diff, flags=re.M):
        start, n = (int(m.group(3)), int(m.group(4) or 1)) if side == "+" else (int(m.group(1)), int(m.group(2) or 1))
        out.append((start, start + max(n, 1) - 1))
    return out


def _windows(hunks: list[tuple[int, int]], pad: int = 30) -> list[tuple[int, int]]:
    merged: list[list[int]] = []
    for a, b in sorted((a - pad, b + pad) for a, b in hunks):
        if merged and a <= merged[-1][1] + 1:
            merged[-1][1] = max(merged[-1][1], b)
        else:
            merged.append([a, b])
    return [(a, b) for a, b in merged]


def _compact_facts(facts: dict) -> dict:
    """facts.json minus noise: long error texts trimmed (test names and outcomes kept in full)."""
    f = json.loads(json.dumps(facts))
    for c in f.get("checks", []):
        for t in c.get("tests", []):
            if isinstance(t.get("error"), str) and len(t["error"]) > 400:
                t["error"] = t["error"][:400] + " [...]"
        for k in ("failures_not_on_base",):
            for t in c.get(k, []) or []:
                if isinstance(t, dict) and isinstance(t.get("error"), str) and len(t["error"]) > 400:
                    t["error"] = t["error"][:400] + " [...]"
    return f


def build_review_context(ws: Workspace, change: str, repo: str, budget: int = DEFAULT_CONTEXT_CHARS) -> dict:
    """Everything the reviewer sees, as one text, plus the list of what it did not get.

    Priority under the character budget: requirements, issue, facts, diff of non-generated files (always); then head
    and base contents of changed source files, then head contents of changed test files. Files that do not fit in
    full are cut to windows around the changed hunks; files that do not fit even then are left out and listed.
    Generated files are never sent (only listed)."""
    facts = read_json(ws.facts_path(change))
    reqs = ws.requirements(change)
    req_path = Path(reqs["_path"]) if Path(reqs["_path"]).is_absolute() else ws.root / reqs["_path"]
    base, head = facts.get("base_full") or facts["base"], facts.get("head_full") or facts["head"]
    files = facts.get("diff", {}).get("by_file", [])
    generated = [f for f in files if f.get("kind") == "generated"]
    normal = [f for f in files if f.get("kind") != "generated"]
    not_given: list[str] = []

    req_text = req_path.read_text(encoding="utf-8")
    facts_text = json.dumps(_compact_facts(facts), indent=1, ensure_ascii=False)
    diffs = {f["path"]: (_git(repo, "diff", base, head, "--", f["path"]) or "") for f in normal}
    if any(v == "" for v in diffs.values()) and _git(repo, "cat-file", "-e", f"{head}^{{commit}}") is None:
        raise SystemExit(f"{repo} does not have head {head}: clone/fetch the challenge repo (--repo)")
    head_section = [
        f"# Change {change}: branch {facts.get('branch')}, base {base}, head {head}",
        f"Commit message: {facts.get('commit_message')}",
        f"Upstream issue: {reqs.get('source')}",
        "", f"## Requirement set ({reqs['_path']})", "```yaml", req_text.strip(), "```",
        "", "## facts.json (deterministic checks; cite their ids and test names)", "```json", facts_text, "```",
        "", f"## Files changed ({len(files)}: {len(normal)} non-generated, {len(generated)} generated)",
        *[f"- {f['path']} (+{f.get('ins', 0)} -{f.get('del', 0)}, {f.get('kind')})" for f in files if f.get("kind") != "generated"],
    ]
    if generated:
        head_section += ["", f"Generated files ({len(generated)}; contents and diffs NOT provided):",
                         *[f"- {f['path']} (+{f.get('ins', 0)} -{f.get('del', 0)})" for f in generated]]
        not_given.append(f"the contents and diffs of {len(generated)} generated files (listed above by name only)")
    diff_text = "\n".join(diffs[f["path"]] for f in normal)
    fixed = "\n".join(head_section) + "\n\n## Diff (non-generated files)\n```diff\n" + diff_text + "\n```\n"
    if len(fixed) > budget:  # keep the diff, trimmed from the end; say so
        keep = max(0, budget - len(fixed) + len(diff_text) - 200)
        cut = diff_text[:keep]
        fixed = "\n".join(head_section) + "\n\n## Diff (non-generated files; TRUNCATED)\n```diff\n" + cut + "\n```\n"
        not_given.append(f"the end of the diff ({len(diff_text) - keep} characters) did not fit the context budget")
    remaining = budget - len(fixed)

    # Pass 1: every changed source file (head and base) and test file (head) gets windows around its changed lines.
    # Pass 2: upgrade to the full file, in priority order (source head, test head, source base), while budget allows.
    wanted = [(f, "head") for f in normal if f.get("kind") == "source"] + [(f, "head") for f in normal if f.get("kind") == "test"]
    wanted += [(f, "base") for f in normal if f.get("kind") == "source"]
    blocks: dict[tuple[str, str], str] = {}
    texts: dict[tuple[str, str], tuple[str, str]] = {}
    for f, rev in wanted:
        sha = head if rev == "head" else base
        text = _git(repo, "show", f"{sha}:{f['path']}")
        if text is None:
            if rev == "head":
                not_given.append(f"{f['path']} at head (not readable)")
            continue  # at base: a new file, nothing to show
        texts[(f["path"], rev)] = (sha, text)
        win = _windows(_hunks(diffs[f["path"]], "+" if rev == "head" else "-"))
        part = f"### {f['path']} at {rev} ({sha[:8]}), around the changed lines\n```\n{_numbered(text, win)}\n```\n"
        if win and len(part) <= remaining:
            blocks[(f["path"], rev)] = part
            remaining -= len(part)
        else:
            not_given.append(f"{f['path']} at {rev}: not provided (did not fit the context budget)")
    for (path, rev), (sha, text) in texts.items():
        full = f"### {path} at {rev} ({sha[:8]}), full file\n```\n{_numbered(text)}\n```\n"
        have = len(blocks.get((path, rev), ""))
        if (path, rev) in blocks and len(full) - have <= remaining:
            blocks[(path, rev)] = full
            remaining -= len(full) - have
        elif (path, rev) in blocks:
            not_given.append(f"{path} at {rev}: only ±30 lines around the changes (the full file did not fit the budget)")
    order = {k: i for i, k in enumerate((f["path"], rev) for f, rev in wanted)}
    blocks = dict(sorted(blocks.items(), key=lambda kv: order[kv[0]]))
    for f in normal:
        if f.get("kind") not in ("source", "test"):
            not_given.append(f"{f['path']}: diff only, full file not provided ({f.get('kind')})")
    not_given.append("the upstream issue page itself (only its URL); other files of the repository; build and test logs (only the facts.json summaries)")
    text = fixed + "\n## File contents (line numbers in the gutter; quote the text after '| ')\n\n" + "\n".join(blocks.values())
    text += "\n## What you did NOT get (refuse anything that depends on it)\n" + "\n".join(f"- {x}" for x in not_given) + "\n"
    inputs = [f"requirements: {reqs['_path']}", f"issue: {reqs.get('source')}", f"facts: evidence/{change}/facts.json",
              f"diff {base[:8]}..{head[:8]} ({len(normal)} non-generated files)",
              f"file contents: {len(blocks)} blocks", f"context: {len(text)} chars (budget {budget})"]
    return {"text": text, "inputs": inputs, "not_given": not_given, "req_ids": [r["id"] for r in reqs.get("requirements", [])],
            "chars": len(text)}


# --- policy checks -----------------------------------------------------------------------------

def _panel(ws: Workspace, change: str) -> tuple[mandate_mod.Mandate, dict]:
    m = mandate_mod.load(ws)
    facts = read_json(ws.facts_path(change))
    return m, m.panel([a["name"] for a in decide_mod.touched_areas(facts, m)])


def check_allowed(ws: Workspace, change: str, cfg: LLMConfig, role: str) -> dict:
    """The mandate decides who may read the code. Raise SystemExit (nothing is sent) if this call is not allowed."""
    m, panel = _panel(ws, change)
    reg = m.reviewers.get(cfg.name)
    if reg is None:
        raise SystemExit(f"{cfg.name} is not in the mandate's reviewer registry")
    excluded = next((x for x in panel["excluded"] if x["name"] == cfg.name), None)
    if excluded:
        raise SystemExit(f"refused: {cfg.name} may not read change {change}: {excluded['reason']}")
    if panel["confidential"] and cfg.hosted_default:
        raise SystemExit(f"refused: change {change} is confidential ({panel['why']}); {cfg.name} is self-hostable, but this "
                         f"call would go to the vendor-hosted endpoint {cfg.base_url}. Set COUNTERSIGN_{cfg.name.upper()}_BASE_URL "
                         "to your own server.")
    if role == "adjudicator" and reg.get("role") != "adjudicator":
        raise SystemExit(f"{cfg.name} is not the adjudicator in the mandate (role {reg.get('role')})")
    return reg


def _stamp(when: datetime | None) -> str:
    return (when or datetime.now(timezone.utc)).astimezone(ZoneInfo("Europe/Helsinki")).replace(microsecond=0).isoformat()


def _log_costs(ws: Workspace, cfg: LLMConfig, change: str, purpose: str, log: list[ChatResult]) -> None:
    for i, r in enumerate(log):
        costs.append(ws, provider=cfg.provider, model=cfg.model, change=change,
                     purpose=purpose + (" (JSON repair turn)" if i else ""),
                     tokens_in=r.usage.get("prompt_tokens"), tokens_out=r.usage.get("completion_tokens"),
                     source="api usage field" if r.usage.get("total_tokens") else "unknown")


def _save_raw(folder: Path, stem: str, cfg: LLMConfig, system: str, user: str, log: list[ChatResult], extra: dict) -> None:
    raw = folder / "raw"
    raw.mkdir(parents=True, exist_ok=True)
    (raw / f"{stem}.context.md").write_text(f"<!-- system prompt -->\n{system}\n\n<!-- user message -->\n{user}", encoding="utf-8")
    write_json(raw / f"{stem}.response.json", {
        "endpoint": f"{cfg.base_url}/chat/completions", "model": cfg.model, "vendor": cfg.vendor,
        "context_sha256": sha256_hex((system + "\n" + user).encode()), "context_file": f"raw/{stem}.context.md", **extra,
        "calls": [{"latency_ms": r.latency_ms, "retries": r.retries, "finish_reason": r.finish_reason, "usage": r.usage,
                   "response": r.raw} for r in log]})


# --- review-llm ---------------------------------------------------------------------------------

def run_review(ws: Workspace, change: str, reviewer: str, repo: str, env: dict | None = None, post=urllib_post,
               sleep=time.sleep, when: datetime | None = None, budget: int | None = None) -> Path:
    env = os.environ if env is None else env
    if is_mutant(change):
        raise SystemExit("review-llm reviews real branches; seeded mutants are uncommitted edits it cannot diff")
    cfg = config(reviewer, env)
    reg = check_allowed(ws, change, cfg, "reviewer")
    if not cfg.api_key:
        raise SystemExit(f"no API key for {reviewer}: set {PRESETS[reviewer]['key_env']} (a CI secret; never commit it)")
    budget = budget or int(env.get("COUNTERSIGN_CONTEXT_CHARS") or DEFAULT_CONTEXT_CHARS)
    ctx = build_review_context(ws, change, repo, budget)
    system = (ws.root / "prompts" / f"{REVIEW_PROMPT}.md").read_text(encoding="utf-8")
    user = ctx["text"] + "\nReturn only the JSON object described in the brief."
    log: list[ChatResult] = []
    started = _stamp(when)
    try:
        parsed, repaired = ask_json(ChatClient(cfg, post, sleep), system, user, lambda r: review_problems(r, ctx["req_ids"]), log)
    finally:
        folder = ws.inputs / "reviews" / change
        _save_raw(folder, reviewer, cfg, system, user, log, {"prompt_version": REVIEW_PROMPT, "started": started})
        _log_costs(ws, cfg, change, f"review {change} ({reviewer}, {REVIEW_PROMPT})", log)
    review = {
        "reviewer": reviewer, "model": cfg.model, "vendor": cfg.vendor, "prompt_version": REVIEW_PROMPT, "reviewed_at": started,
        "inputs": ctx["inputs"], "not_given": ctx["not_given"],
        "runner": {"tool": "countersign review-llm", "endpoint": cfg.base_url, "self_hostable": bool(reg.get("self_hostable")),
                   "calls": len(log), "json_repaired": repaired, "raw": f"reviews/{change}/raw/{reviewer}.response.json",
                   "usage": {k: sum(r.usage.get(k, 0) for r in log) for k in ("prompt_tokens", "completion_tokens")}},
        "summary": str(parsed.get("summary", "")),
        "requirement_verdicts": [{"req": v["req"], "verdict": v["verdict"], "confidence_basis": str(v.get("confidence_basis", "")),
                                  "evidence": v.get("evidence", [])} for v in parsed["requirement_verdicts"]],
        "findings": [{"id": str(f.get("id") or f"{reviewer[0].upper()}{i}"), **{k: f[k] for k in ("title", "severity", "category", "claim")},
                      "evidence": f.get("evidence", []), **({"suggested_fix": f["suggested_fix"]} if f.get("suggested_fix") else {})}
                     for i, f in enumerate(parsed.get("findings", []), 1)],
        "refusals": [{"topic": x["topic"], "reason": x["reason"], "who_should_decide": x.get("who_should_decide", "area owner")}
                     for x in parsed.get("refusals", [])],
    }
    folder = ws.inputs / "reviews" / change
    write_json(folder / f"{reviewer}.json", review)
    (folder / f"{reviewer}.md").write_text(review_markdown(review, change), encoding="utf-8")
    return folder / f"{reviewer}.json"


def review_markdown(r: dict, change: str) -> str:
    out = [f"# Review of {change} by {r['reviewer']} ({r['model']}, {r['prompt_version']})", "",
           f"_Run by `countersign review-llm` at {r['reviewed_at']}; raw response in `{r['runner']['raw']}`. "
           f"Tokens in/out: {r['runner']['usage']['prompt_tokens']}/{r['runner']['usage']['completion_tokens']}._", "",
           f"**Summary:** {r['summary'] or '(none given)'}", "", "| Req | Verdict | Basis |", "|---|---|---|"]
    out += [f"| {v['req']} | {v['verdict']} | {v['confidence_basis'].replace('|', '/')} |" for v in r["requirement_verdicts"]]
    out += ["", "## Findings", ""] + [f"- **{f['id']}** [{f['severity']}, {f['category']}] {f['title']}: {f['claim']}" for f in r["findings"]]
    if not r["findings"]:
        out.append("- none")
    out += ["", "## Refusals", ""] + [f"- {x['topic']}: {x['reason']} (decide: {x['who_should_decide']})" for x in r["refusals"]]
    if not r["refusals"]:
        out.append("- none")
    out += ["", "## Not given to the model", ""] + [f"- {x}" for x in r.get("not_given", [])]
    return "\n".join(out) + "\n"


# --- adjudicate ---------------------------------------------------------------------------------

def _code_excerpt(repo: str, facts: dict, e: dict, pad: int = 8) -> str | None:
    if e.get("kind") != "code":
        return None
    rev = e.get("rev", "head")
    sha = facts.get(f"{rev}_full") or facts.get(rev) if rev in ("head", "base") else rev
    text = _git(repo, "show", f"{sha}:{e.get('file', '')}")
    if text is None:
        return None
    line = int(e.get("line") or 0)
    return _numbered(text, [(line - pad, line + pad)])


def build_adjudication_context(ws: Workspace, change: str, pack: dict, disputes: list[dict], repo: str) -> str:
    facts = read_json(ws.facts_path(change))
    items = []
    for d in disputes:
        sides = []
        for s in d["sides"]:
            ev = []
            for e in s["evidence"]:
                x = {k: v for k, v in e.items() if k not in ("verified", "note")}
                x["engine_verified"], x["engine_note"] = e.get("verified"), e.get("note")
                ex = _code_excerpt(repo, facts, e)
                if ex:
                    x["code_around_cited_line"] = ex
                ev.append(x)
            sides.append({"reviewer": s["reviewer"], "verdict": s["verdict"], "basis": s["basis"], "evidence": ev})
        items.append({"id": d["id"], "kind": d["kind"], "text": d["text"], "sides": sides,
                      **({"not_raised_by": d["not_raised_by"]} if d.get("not_raised_by") else {})})
    checks = [{k: c.get(k) for k in ("id", "status", "summary")} for c in facts.get("checks", [])]
    return (f"# Change {change}: disputes to adjudicate ({len(items)})\n\n"
            f"Requirement clauses and their engine status:\n```json\n{json.dumps([{k: c[k] for k in ('id', 'text', 'status')} for c in pack['requirements']], indent=1)}\n```\n"
            f"Deterministic checks (facts.json):\n```json\n{json.dumps(checks, indent=1)}\n```\n"
            f"Disputed items:\n```json\n{json.dumps(items, indent=1, ensure_ascii=False)}\n```\n"
            "Return only the JSON object described in the brief, one ruling per disputed item.")


def run_adjudication(ws: Workspace, change: str, repo: str, adjudicator: str | None = None, env: dict | None = None,
                     post=urllib_post, sleep=time.sleep, when: datetime | None = None) -> Path | None:
    """Only when reviewers disagree. Returns None (and sends nothing) when there is nothing in dispute."""
    from . import pack as pack_mod  # local import: pack imports decide, which this module also uses
    env = os.environ if env is None else env
    m, panel = _panel(ws, change)
    name = adjudicator or panel["adjudicator"] or next((n for n, r in m.reviewers.items() if r.get("role") == "adjudicator"), None)
    if name is None:
        raise SystemExit("the mandate names no adjudicator")
    cfg = config(name, env)
    check_allowed(ws, change, cfg, "adjudicator")
    p = pack_mod.build(ws, change)
    # disputes are computed from the reviews alone (an earlier adjudication file is not an input to the next one)
    disputes = [d for d in p["disputes"]]
    if not disputes:
        return None
    full = _disputes_with_sides(ws, change)
    if not cfg.api_key:
        raise SystemExit(f"no API key for {name}: set {PRESETS[name]['key_env']}")
    system = (ws.root / "prompts" / f"{ADJUDICATE_PROMPT}.md").read_text(encoding="utf-8")
    user = build_adjudication_context(ws, change, p, full, repo)
    ids = [d["id"] for d in full]
    log: list[ChatResult] = []
    started = _stamp(when)
    stem = f"adjudication.{name}"
    try:
        parsed, repaired = ask_json(ChatClient(cfg, post, sleep), system, user, lambda r: adjudication_problems(r, ids), log)
    finally:
        _save_raw(ws.inputs / "reviews" / change, stem, cfg, system, user, log, {"prompt_version": ADJUDICATE_PROMPT, "started": started})
        _log_costs(ws, cfg, change, f"adjudicate {change} ({name}, {ADJUDICATE_PROMPT})", log)
    keep = ("dispute", "supported", "unsupported", "evidence_that_would_settle", "route_to", "note")
    out = {"reviewer": name, "model": cfg.model, "vendor": cfg.vendor, "prompt_version": ADJUDICATE_PROMPT, "reviewed_at": started,
           "role": "adjudicator: advisory; can add reasons and route to a human, never clears",
           "disputes_given": ids,
           "runner": {"tool": "countersign adjudicate", "endpoint": cfg.base_url, "calls": len(log), "json_repaired": repaired,
                      "raw": f"reviews/{change}/raw/{stem}.response.json"},
           # only the fields the brief asks for: anything else the model adds (e.g. "verdict": "met") is dropped
           "rulings": [{k: r[k] for k in keep if k in r} for r in parsed["rulings"]]}
    path = ws.inputs / "reviews" / change / f"{stem}.json"
    write_json(path, out)
    return path


def _disputes_with_sides(ws: Workspace, change: str) -> list[dict]:
    """Disputes with each side's evidence and the engine's verification results (the pack keeps only ids)."""
    from . import ledger, trust, verify
    m = mandate_mod.load(ws)
    facts = read_json(ws.facts_path(change))
    reqs = ws.requirements(change)
    panel = m.panel([a["name"] for a in decide_mod.touched_areas(facts, m)])
    v = verify.Verifier(ws.repo, facts, reqs, m["decision"]["code_line_tolerance"])
    reviews = {n: verify.verify_review(r, v) for n, r in ws.reviews(change).items() if n in panel["reviewers"]}
    d = decide_mod.decide(facts, reviews, reqs, m, mandate_mod.signature_status(ws, m), trust.caps(trust.derive(m, ledger.read(ws))), panel)
    return d["disputes"]

