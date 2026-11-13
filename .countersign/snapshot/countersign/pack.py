"""Stage 5: the evidence pack (pack.json, pack.md, pack.html) a named owner signs.

pack.json is deterministic for the same inputs, mandate and trust state (no timestamps inside), so its
sha256 identifies exactly what the owner saw. The renderers only format what is in pack.json.
"""

from __future__ import annotations

import re
import subprocess
from copy import deepcopy
from pathlib import Path

from . import __version__, decide as decide_mod, ledger, mandate as mandate_mod, trust, verify
from .common import HUMAN_TIERS, Workspace, canonical, read_json, sha256_hex, write_json

SCHEMA = "countersign.pack/v1"


def _file_ref(path: Path, root: Path) -> dict:
    p = Path(path)
    shown = str(p.relative_to(root)) if p.is_relative_to(root) else str(p)
    return {"path": shown, "sha256": sha256_hex(p.read_bytes())}


def build(ws: Workspace, change: str, use_trust: bool = True) -> dict:
    """verify + decide + assemble. Reads facts, reviews, requirements, mandate and the ledger; writes nothing.
    use_trust=False ignores trust events (caps = mandate), so a replay measures the reviewer, not the ledger state."""
    facts_path = ws.facts_path(change)
    if not facts_path.exists():
        raise FileNotFoundError(f"no {facts_path}: run the deterministic checks first (stage 1)")
    facts = read_json(facts_path)
    reqs = ws.requirements(change)
    m = mandate_mod.load(ws)
    msig = mandate_mod.signature_status(ws, m)
    state = trust.derive(m, ledger.read(ws) if use_trust else [])

    v = verify.Verifier(ws.repo, facts, reqs, m["decision"]["code_line_tolerance"])
    # Who may read this change (reviewer registry + confidentiality). Reviews by anyone else are not used.
    panel = m.panel([a["name"] for a in decide_mod.touched_areas(facts, m)])
    all_reviews = ws.reviews(change)
    raw_reviews = {n: r for n, r in all_reviews.items() if n in panel["reviewers"]}
    ignored = [{"name": n, "reason": next((x["reason"] for x in panel["excluded"] if x["name"] == n),
                                          "not a participating reviewer in the mandate's registry")}
               for n in all_reviews if n not in raw_reviews]
    reviews = {name: verify.verify_review(r, v) for name, r in raw_reviews.items()}
    adj_path = ws.adjudication_path(change)
    adj = read_json(adj_path) if adj_path else None
    if adj and adj.get("reviewer") != panel["adjudicator"]:
        ignored.append({"name": adj_path.name, "reason": f"{adj.get('reviewer')} is not the adjudicator allowed for this change"})
        adj = None
    d = decide_mod.decide(facts, reviews, reqs, m, msig, trust.caps(state), panel, deepcopy(adj))
    # What the AI would recommend under the mandate's own caps. During probation this is what spot-checks grade.
    ai_alone = decide_mod.decide(facts, reviews, reqs, m, msig, {}, panel, deepcopy(adj))["tier"]

    req_file = ws.root / reqs["_path"] if not Path(reqs["_path"]).is_absolute() else Path(reqs["_path"])
    inputs = {"facts": _file_ref(facts_path, ws.root), "requirements": _file_ref(req_file, ws.root),
              "reviews": {n: _file_ref(ws.inputs / "reviews" / change / f"{n}.json", ws.root) for n in raw_reviews}}
    if adj:
        inputs["adjudication"] = _file_ref(adj_path, ws.root)
    simulated = bool(facts.get("simulated")) or any(r.get("simulated") for r in raw_reviews.values())

    tools = [{k: c.get(k) for k in ("id", "tool", "tool_version", "status", "summary", "duration_s", "log")} for c in facts.get("checks", [])]
    reviewers = []
    for name, r in reviews.items():
        fs = r.get("findings", [])
        reviewers.append({"reviewer": name, "model": r.get("model"), "vendor": r.get("vendor"),
                          "prompt_version": r.get("prompt_version"), "reviewed_at": r.get("reviewed_at"),
                          "inputs": r.get("inputs", []), "findings": len(fs),
                          "verified": sum(f["status"] == "verified" for f in fs),
                          "rejected": sum(f["status"] == "rejected" for f in fs),
                          "refusals": len(r.get("refusals", []))})

    not_checked = [{"id": n["id"], "reason": n["reason"], "source": "facts.json not_run"} for n in facts.get("not_run", [])]
    not_checked += [{"id": c["id"], "reason": f"{c['status']}: {c.get('summary', '')}", "source": "check did not pass or fail"}
                    for c in facts.get("checks", []) if c["status"] in ("skipped", "error")]
    known = {c["id"] for c in facts.get("checks", [])}
    for a in d["areas"]:
        not_checked += [{"id": c, "reason": f"mandated by area {a['name']} but absent from facts.json", "source": "mandate"}
                        for c in a["checks"] if c not in known and c not in {x["id"] for x in not_checked}]
    not_checked += [{"id": g["id"], "reason": g["reason"], "source": "mandate known gap"} for g in m["known_gaps"]]

    verified = [f for f in d["findings"] if f["status"] == "verified"]
    rejected = [f for f in d["findings"] if f["status"] == "rejected"]
    residual = [f"{c['id']} not proven: " + _codes(c) for c in d["clauses"] if c["status"] == "refused"]
    residual += [f"{c['id']} held before this change (met, but not achieved by it)" for c in d["clauses"] if c["status"] == "held_before"]
    residual += [f"Reviewer refusal ({r['reviewer']}): {r['topic']}" for r in d["reviewer_refusals"]]
    residual += [f"Open {f['severity']} finding {f['reviewer']}:{f['id']}: {f['title']}" for f in verified if f["severity"] in ("blocker", "major")]
    residual += [f"Unsupported {f['severity']} claim {f['reviewer']}:{f['id']} was rejected for lack of evidence, not disproven: {f['title']}"
                 for f in rejected if f["severity"] in ("blocker", "major")]
    residual += [f"{x['id']} not run ({x['reason']})" for x in not_checked if x["source"] != "mandate known gap"]
    residual += [f"Area {a['name']} is on probation: {a['cap_reason']}" for a in d["areas"] if state[a["name"]]["probation"]]
    residual += [f"Reviewer {x['name']} ({x['vendor']}) did not read this change: {x['reason']}" for x in panel["excluded"]]
    if d["disputes"] and not adj:
        residual.append(f"{len(d['disputes'])} disputed item(s) were not adjudicated"
                        + (f" (adjudicator {panel['adjudicator']} has not run)" if panel["adjudicator"] else " (no adjudicator allowed)"))
    residual.append(f"Standing gaps of this pipeline: {', '.join(g['id'] for g in m['known_gaps'])} (see not checked)")

    tier = d["tier"]
    p = {
        "schema": SCHEMA,
        "change": change,
        "branch": facts.get("branch"), "base": facts.get("base"), "head": facts.get("head"),
        "commit_message": facts.get("commit_message"), "author": facts.get("author"), "agent_written": facts.get("agent_written"),
        "diff": {k: facts.get("diff", {}).get(k) for k in ("files", "insertions", "deletions")},
        "simulated": simulated,
        "mutation": facts.get("mutation"),
        "engine": {"name": "countersign", "version": __version__},
        "mandate": m.summary(ws),
        "inputs": inputs,
        "requirement_set": {"source": reqs.get("source"), "official": reqs.get("official", False)},
        "tier": tier,
        "ai_recommendation": ai_alone,
        "why": d["decisive"],
        "drivers": d["drivers"],
        "owner": d["owner"],
        "primary_area": d["primary_area"],
        "notify": d["notify"],
        "areas": [{k: a[k] for k in ("name", "owner", "sensitivity", "max_ai_tier", "cap", "cap_reason", "files")} for a in d["areas"]],
        "requirements": d["clauses"],
        "reviewer_panel": {**panel, "ignored_files": ignored,
                           "rule": "proven needs every participating reviewer to say met with verified evidence, and the clause's checks to pass"},
        "disputes": [{"id": x["id"], "kind": x["kind"], "about": x["about"], "reviewers": [s["reviewer"] for s in x["sides"]]} for x in d["disputes"]],
        "adjudication": _adjudication_summary(adj, d["disputes"]),
        "checked_by": {"tools": tools, "reviewers": reviewers,
                       "engine": f"countersign {__version__} under mandate {m['id']} v{m.version} ({m.sha256[:12]})"},
        "findings": verified,
        "refused": {"clauses": [c for c in d["clauses"] if c["status"] == "refused"], "reviewer_refusals": d["reviewer_refusals"]},
        "rejected_claims": rejected,
        "not_checked": not_checked,
        "residual_risk": residual,
        "risk": d["risk"],
        "rules_fired": d["rules_fired"],
        "signoff": {
            "required": tier in HUMAN_TIERS,
            "owner": d["owner"],
            "allowed_decisions": ["reject", "request-changes"] if tier == "block" else ["accept", "reject", "request-changes"],
            "command": f"countersign sign {change} --as {d['owner']} --decision <accept|reject|request-changes> --note \"...\"",
            "statement": (f"I, {d['owner']}, have read what was checked and by whom, what was not checked and why, "
                          "and the residual risk listed in this pack, and I own this decision."),
        },
    }
    # The reader's view (card, trust chains, panel, evidence with code excerpts). Deterministic, so it is hashed too.
    idx = _evidence_index(ws, facts, d, reqs, m["decision"]["code_line_tolerance"])
    refusal_groups = _dedupe_refusals(d["reviewer_refusals"])
    trust_rows = _trust(p, d, facts, idx)
    p["story"] = _story(p, facts, reqs)
    p["card"] = _card(p, d, trust_rows, refusal_groups)
    p["trust"] = trust_rows
    p["panel"] = _panel(p, d, reviews)
    p["evidence_index"] = idx
    return p


def _codes(c: dict) -> str:
    return "; ".join(dict.fromkeys(r["code"] for r in c["reasons"]))


def _adjudication_summary(adj: dict | None, disputes: list[dict]) -> dict | None:
    """The adjudicator's rulings as shown beside the refusals. Advisory only: decide.apply_adjudication can add
    reasons and route to a human, it never clears anything."""
    if not adj:
        return None
    live = {x["id"] for x in disputes}
    return {"reviewer": adj.get("reviewer"), "model": adj.get("model"), "vendor": adj.get("vendor"),
            "prompt_version": adj.get("prompt_version"), "reviewed_at": adj.get("reviewed_at"),
            "role": "adjudicator (can add reasons and route to a human; never clears)",
            "rulings": [{**r, "stale": str(r.get("dispute")) not in live} for r in adj.get("rulings", [])]}


# Renderers live in pack_render.py; re-exported so callers keep using pack.card / pack.to_markdown / pack.to_html.
from .pack_render import card, to_html, to_markdown  # noqa: E402


def write(ws: Workspace, pack: dict) -> Path:
    out = ws.pack_dir(pack["change"])
    write_json(out / "pack.json", pack)
    (out / "pack.md").write_text(to_markdown(pack), encoding="utf-8")
    (out / "pack.html").write_text(to_html(pack), encoding="utf-8")
    return out




# --- the reader's view: story, sign-off card, trust chains, reviewer panel, evidence index ---------------------
# Everything below is derived deterministically from the decision and the repo, and stored in pack.json, so the
# owner signs exactly what the card showed. The renderers (pack_render.py) only format it.

SEVERITIES = ["blocker", "major", "minor", "info"]
CONTEXT_LINES = 3  # lines of code shown around a cited line


def _name(n: str) -> str:
    return {"claude": "Claude", "codex": "Codex", "nemotron": "Nemotron", "gemini": "Gemini"}.get(n, n[:1].upper() + n[1:])


def _names(ns) -> str:
    ns = [_name(n) for n in ns]
    return ns[0] if len(ns) == 1 else ", ".join(ns[:-1]) + " and " + ns[-1] if ns else "nobody"


def _plural(n: int, one: str, many: str | None = None) -> str:
    return f"{n} {one if n == 1 else (many or one + 's')}"


def _norm_ws(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()


def _logs(c: dict) -> list[str]:
    log = c.get("log")
    return [log] if isinstance(log, str) else list(log or [])


def ev_ref(e: dict) -> str:
    """Stable anchor for one piece of evidence: the same citation by two reviewers is one item."""
    keys = ("kind", "file", "line", "rev", "quote", "name", "outcome", "id", "req", "url", "check", "status")
    return "ev-" + sha256_hex(canonical({k: e.get(k) for k in keys}))[:10]


def ev_label(e: dict) -> str:
    k = e.get("kind")
    if k == "code":
        rev = str(e.get("rev", "head"))
        return f"{Path(str(e.get('file'))).name}:{e.get('line')} @{rev if rev in ('head', 'base') else rev[:8]}"
    if k == "test":
        return f"test {str(e.get('name', '')).rsplit('.', 1)[-1]} {e.get('outcome', '')}".rstrip()
    if k == "check":
        return f"check {e.get('id')}" + (f" {e['status']}" if e.get("status") else "")
    if k == "requirement":
        return f"{e.get('req')} text"
    if k == "issue":
        return "issue " + str(e.get("url", "")).rstrip("/").rsplit("/", 1)[-1]
    return str(k)


class _Git:
    def __init__(self, repo: str, facts: dict):
        self.repo, self.facts, self.cache = repo, facts, {}

    def lines(self, rev_name: str, path: str) -> tuple[str, list[str] | None]:
        rev = self.facts.get(rev_name, rev_name) if rev_name in ("head", "base") else rev_name
        if (rev, path) not in self.cache:
            r = subprocess.run(["git", "-C", self.repo, "show", f"{rev}:{path}"], capture_output=True)
            lines = r.stdout.decode("utf-8", "replace").splitlines() if r.returncode == 0 else None
            mut = self.facts.get("mutation") or {}
            if lines and rev_name == "head" and mut.get("file") == path and mut.get("line") and mut.get("before") is not None:
                n = int(mut["line"]) - 1
                if n < len(lines) and mut["before"] in lines[n]:
                    lines[n] = lines[n].replace(mut["before"], mut.get("after", ""))
            self.cache[(rev, path)] = lines
        return rev, self.cache[(rev, path)]


def _excerpt(git: _Git, e: dict, tolerance: int) -> dict | None:
    rev, lines = git.lines(e.get("rev", "head"), str(e.get("file", "")))
    if not lines:
        return None
    try:
        line = int(e.get("line", 0))
    except (TypeError, ValueError):
        line = 0
    quote = _norm_ws(e.get("quote", ""))
    hits = [n for n in range(max(1, line - tolerance), min(len(lines), line + tolerance) + 1) if quote and quote in _norm_ws(lines[n - 1])]
    hl = min(hits, key=lambda n: abs(n - line)) if hits else None
    center = hl or (line if 1 <= line <= len(lines) else None)
    if center is None:
        return None
    start, end = max(1, center - CONTEXT_LINES), min(len(lines), center + CONTEXT_LINES)
    return {"sha": rev[:8], "start": start, "highlight": hl, "lines": lines[start - 1:end]}


def _test_runs(facts: dict, name: str) -> list[dict]:
    runs = []
    for c in facts.get("checks", []):
        for t in c.get("tests", []):
            if t.get("name") == name:
                without = "fail_without_fix" in c["id"]
                runs.append({"check": c["id"], "outcome": t.get("outcome"), "project": t.get("project"),
                             "run": "source reverted, tests kept (without the fix)" if without else "change head",
                             "without_fix": without, "logs": _logs(c)})
    return runs


def _without_fix(runs: list[dict]) -> str | None:
    """failed: the test fails without the fix (it tests the change). passed: it passes anyway (held before)."""
    outs = {r["outcome"] for r in runs if r["without_fix"]}
    return "failed" if "failed" in outs else "passed" if "passed" in outs else None


def _evidence_index(ws: Workspace, facts: dict, d: dict, reqs: dict, tolerance: int) -> dict:
    git = _Git(ws.repo, facts)
    checks = {c["id"]: c for c in facts.get("checks", [])}
    req_text = {r["id"]: r["text"] for r in reqs.get("requirements", [])}
    idx: dict[str, dict] = {}

    def add(e: dict, by: str) -> None:
        ref = e["ref"] = ev_ref(e)
        if ref not in idx:
            rec = {k: e[k] for k in ("kind", "file", "line", "rev", "quote", "name", "outcome", "id", "req", "url", "check", "status") if k in e}
            rec.update(ref=ref, label=ev_label(e), verified=e["verified"], note=e["note"], cited_by=[])
            kind = e.get("kind")
            if kind == "code":
                rec["excerpt"] = _excerpt(git, e, tolerance)
            elif kind == "test":
                rec["runs"] = _test_runs(facts, str(e.get("name")))
                rec["without_fix"] = _without_fix(rec["runs"])
            elif kind == "check" and e.get("id") in checks:
                c = checks[e["id"]]
                rec["check_result"] = {"status": c["status"], "summary": c.get("summary"), "tool": c.get("tool"),
                                       "tool_version": c.get("tool_version"), "logs": _logs(c)}
            elif kind == "requirement":
                rec["clause_text"] = req_text.get(e.get("req"))
            idx[ref] = rec
        if by not in idx[ref]["cited_by"]:
            idx[ref]["cited_by"].append(by)

    for c in d["clauses"]:
        for n, v in c["verdicts"].items():
            for e in v["evidence"]:
                add(e, f"{n} on {c['id']}")
    for f in d["findings"]:
        for e in f["evidence"]:
            add(e, f"{f['reviewer']}:{f['id']}")
    return idx


# plain-language reasons ---------------------------------------------------------

def _verdict_groups(c: dict) -> str:
    by: dict[str, list[str]] = {}
    for n, v in c["verdicts"].items():
        by.setdefault(v["verdict"].replace("_", " "), []).append(_name(n))
    return "; ".join(f"{', '.join(ns)}: {v}" for v, ns in by.items())


def clause_label(c: dict) -> str:
    if c["status"] == "held_before":
        return "held before"
    if c["status"] == "refused" and any(v["verdict"] == "not_met" for v in c["verdicts"].values()):
        return "not met"
    return c["status"]


def clause_why(c: dict, n_reviewers: int) -> str:
    """One line, in words, for the trace row."""
    codes = {r["code"]: r for r in c["reasons"]}
    v = c["verdicts"]
    if c["status"] == "proven":
        cited = sum(x["verified"] for x in v.values())
        checks = ", ".join(x["id"] for x in c["checks"])
        return (f"{'All ' + str(len(v)) if len(v) > 1 else _names(v)} reviewer{'s' if len(v) > 1 else ''} say met "
                f"({_plural(cited, 'verified citation')})" + (f"; {checks} pass" if checks else ""))
    if c["status"] == "held_before":
        detail = next((r["detail"] for r in c["reasons"]), "")
        return "Met, but already true before this change" + (f": {detail}" if detail else ": its tests pass without the fix")
    parts = []
    if "check_failed" in codes:
        parts.append("; ".join(r["detail"] for r in c["reasons"] if r["code"] == "check_failed"))
    if "not_met" in codes:
        no = [n for n, x in v.items() if x["verdict"] == "not_met"]
        yes = [n for n, x in v.items() if x["verdict"] == "met"]
        parts.append(f"{_names(no)} say{'s' if len(no) == 1 else ''} not met" + (f" ({_names(yes)}: met)" if yes else ""))
    if "reviewers_disagree" in codes and "not_met" not in codes:
        parts.append(f"reviewers split ({_verdict_groups(c)})")
    elif "cannot_determine" in codes and "reviewers_disagree" not in codes:
        parts.append(f"{_names(n for n, x in v.items() if x['verdict'] == 'cannot_determine')} could not determine it")
    if "thin_evidence" in codes:
        parts.append(f"{_names(n for n, x in v.items() if x['verdict'] == 'met' and x['verified'] < 1)} said met without verified evidence")
    if "check_not_run" in codes:
        parts.append("; ".join(r["detail"] for r in c["reasons"] if r["code"] == "check_not_run"))
    missing = [r["detail"].split(" ")[0] for r in c["reasons"] if r["code"] == "missing_review"]
    if missing:
        parts.append(f"no verdict from {_names(missing)}" + (f" ({len(v)} of {n_reviewers} reviewers answered)" if v else ""))
    if "adjudicator_dispute" in codes:
        parts.append("the adjudicator disputes it")
    return (parts[0][:1].upper() + parts[0][1:] + "".join("; " + p for p in parts[1:])) if parts else "Refused"


def _settle(c: dict, chain_adj: dict | None) -> list[str]:
    out = list((chain_adj or {}).get("evidence_that_would_settle", []))
    for r in c["reasons"]:
        code, det = r["code"], r["detail"]
        name = det.split(":")[0].split(" ")[0]
        out.append({"missing_review": f"A verdict from {_name(name)} with verified evidence",
                    "check_not_run": f"Run the check ({det})",
                    "check_failed": f"A passing run, or proof the failure is unrelated ({det})",
                    "not_met": f"A fix, or evidence that refutes {_name(name)}'s objection",
                    "cannot_determine": f"The evidence {_name(name)} says it lacked (see its basis above)",
                    "thin_evidence": f"{_name(name)} citing evidence the engine can verify",
                    }.get(code, ""))
    return [x for x in dict.fromkeys(out) if x]


# refusals, deduplicated across reviewers -----------------------------------------

_STOP = {"that", "this", "with", "which", "whether", "from", "into", "under", "their", "there", "would", "could", "should", "does", "have", "when"}


def _tokens(s: str) -> set[str]:
    words = re.findall(r"[a-z0-9]+", s.lower().replace("behaviour", "behavior"))
    return {w.rstrip("s") for w in words if len(w) > 3 and w not in _STOP}


def _dedupe_refusals(refusals: list[dict]) -> list[dict]:
    groups: list[dict] = []
    for r in refusals:
        t = _tokens(r["topic"])
        g = next((g for g in groups if t and g["_t"] and len(t & g["_t"]) / min(len(t), len(g["_t"])) >= 0.6), None)
        if g is None:
            groups.append({"topic": r["topic"], "why": r["reason"], "raised_by": [r["reviewer"]],
                           "who_should_decide": [r["who_should_decide"]], "_t": t})
        else:
            g["raised_by"] = list(dict.fromkeys(g["raised_by"] + [r["reviewer"]]))
            g["who_should_decide"] = list(dict.fromkeys(g["who_should_decide"] + [r["who_should_decide"]]))
            g["_t"] |= t
    for i, g in enumerate(groups, 1):
        g.pop("_t")
        g["anchor"] = f"refusal-{i}"
    return groups


# the views ---------------------------------------------------------------------------

def _story(p: dict, facts: dict, reqs: dict) -> dict:
    by_file = facts.get("diff", {}).get("by_file", [])
    kinds: dict[str, list[str]] = {}
    for f in by_file:
        kinds.setdefault(f.get("kind", "source"), []).append(f["path"])
    src = kinds.get("source", [])
    parts = []
    if src:
        shown = ", ".join(Path(x).name for x in src[:3]) + (f" and {len(src) - 3} more" if len(src) > 3 else "")
        parts.append(f"{_plural(len(src), 'source file')} ({shown})")
    for k, one in (("test", "test file"), ("doc", "doc file"), ("build", "build file"), ("generated", "generated file")):
        if kinds.get(k):
            parts.append(_plural(len(kinds[k]), one))
    src_url = str(reqs.get("source") or "")
    issue = re.search(r"/(issues|pull)/(\d+)", src_url)
    issue_ref = f"#{issue.group(2)}" if issue else (src_url or "no linked issue")
    subject = _norm_ws(p["commit_message"] or "")
    subject = re.sub(r"^(implementation|implement|fix(es)?)\s+(for\s+)?(issue\s+)?#\d+\s*:?\s*", "", subject, flags=re.I) or subject
    n = len(reqs.get("requirements", []))
    return {
        "headline": f"{'Agent-written change' if p['agent_written'] else 'Change'} for {issue_ref}: {subject}",
        "what": (f"Changes {', '.join(parts) or 'no files'} (+{p['diff']['insertions']} -{p['diff']['deletions']}) on "
                 f"{p['branch']} by {p['author']}."),
        "why": (f"Judged against {_plural(n, 'requirement clause')} from {issue_ref}" + ("" if reqs.get("official") else " (placeholder requirement set, not Tieto's official one)") + "."),
        "touches": [{"area": a["name"], "owner": a["owner"], "sensitivity": a["sensitivity"], "files": len(a["files"])} for a in p["areas"]],
        "issue": src_url or None,
    }


def _finding_shared(f: dict, findings: list[dict]) -> list[str]:
    if f["status"] != "verified":
        return []
    mine = decide_mod._anchors(f)
    return sorted({g["reviewer"] for g in findings if g["reviewer"] != f["reviewer"] and g["status"] == "verified" and mine & decide_mod._anchors(g)})


def _chips(f: dict, n: int = 2) -> list[dict]:
    return [{"ref": e["ref"], "label": ev_label(e)} for e in f["evidence"] if e["verified"]][:n]


def _trust(p: dict, d: dict, facts: dict, idx: dict) -> list[dict]:
    rulings = {str(r.get("dispute")): r for r in (p.get("adjudication") or {}).get("rulings", []) if not r.get("stale")}
    fwf_failed = [t["name"] for c in facts.get("checks", []) if "fail_without_fix" in c["id"] for t in c.get("tests", []) if t["outcome"] == "failed"]
    out = []
    for c in d["clauses"]:
        reviewers = []
        tests: dict[str, dict] = {}
        for n, v in c["verdicts"].items():
            reviewers.append({"reviewer": n, "verdict": v["verdict"], "basis": v["basis"], "verified": v["verified"], "cited": v["cited"],
                              "refs": [e["ref"] for e in v["evidence"] if e["verified"]],
                              "unverified_refs": [e["ref"] for e in v["evidence"] if not e["verified"]]})
            for e in v["evidence"]:
                if e.get("kind") == "test" and e["ref"] in idx:
                    tests.setdefault(str(e.get("name")), {"name": e.get("name"), "ref": e["ref"], "without_fix": idx[e["ref"]].get("without_fix")})
        checks = [{"id": x["id"], "status": x["status"],
                   "summary": next((k.get("summary") for k in facts.get("checks", []) if k["id"] == x["id"]), None),
                   "logs": next((_logs(k) for k in facts.get("checks", []) if k["id"] == x["id"]), [])} for x in c["checks"]]
        fails = [t for t in tests.values() if t["without_fix"] == "failed"]
        if not fails and any("fail_without_fix" in x["id"] for x in c["checks"]):
            fails = [{"name": n, "ref": None, "without_fix": "failed"} for n in fwf_failed]
        missing = [r["detail"].split(" ")[0] for r in c["reasons"] if r["code"] == "missing_review"]
        adj = rulings.get(c["id"])
        out.append({"id": c["id"], "text": c["text"], "status": c["status"], "label": clause_label(c), "why": clause_why(c, len(p["reviewer_panel"]["reviewers"])),
                    "checks": checks, "reviewers": reviewers,
                    "agree": [r["reviewer"] for r in reviewers if r["verdict"] == "met"],
                    "disagree": [r["reviewer"] for r in reviewers if r["verdict"] != "met"], "missing": missing,
                    "tests_fail_without_fix": fails,
                    "tests_pass_without_fix": [t for t in tests.values() if t["without_fix"] == "passed"],
                    "reasons": c["reasons"], "adjudication": adj,
                    "settle": _settle(c, adj) if c["status"] != "proven" else []})
    return out


def _panel(p: dict, d: dict, reviews: dict) -> dict:
    clauses = d["clauses"]
    findings = d["findings"]
    rows = []
    for name, r in reviews.items():
        ev = [e for v in r.get("requirement_verdicts", []) for e in v["evidence"]] + [e for f in r.get("findings", []) for e in f["evidence"]]
        mine = [f for f in findings if f["reviewer"] == name]
        only = [{"id": f["id"], "severity": f["severity"], "title": f["title"], "status": f["status"]}
                for f in mine if not _finding_shared(f, findings)]
        verdicts = {c["id"]: (c["verdicts"].get(name) or {}).get("verdict") for c in clauses}
        rows.append({"reviewer": name, "model": r.get("model"), "vendor": r.get("vendor"), "prompt_version": r.get("prompt_version"),
                     "simulated": bool(r.get("simulated")), "verdicts": verdicts,
                     "citations_verified": sum(e["verified"] for e in ev), "citations_rejected": sum(not e["verified"] for e in ev),
                     "findings_verified": sum(f["status"] == "verified" for f in mine), "findings_rejected": sum(f["status"] == "rejected" for f in mine),
                     "only_this_reviewer": only, "refusals": len(r.get("refusals", []))})
    for n in p["reviewer_panel"]["reviewers"]:
        if n not in reviews:
            rows.append({"reviewer": n, "missing": True, "verdicts": {c["id"]: None for c in clauses}})
    callouts = []
    n_cl = len(clauses)
    all_met = [r["reviewer"] for r in rows if not r.get("missing") and n_cl and all(v == "met" for v in r["verdicts"].values())]
    for r in rows:
        if r.get("missing"):
            callouts.append(f"{_name(r['reviewer'])} is on the panel but has no review yet, so no clause can be proven until it answers.")
            continue
        serious = [f for f in r["only_this_reviewer"] if f["status"] == "verified" and f["severity"] in ("blocker", "major")]
        quiet = [n for n in all_met if n != r["reviewer"]]
        if serious and quiet:
            f = serious[0]
            diff = [c["id"] for c in clauses if c["status"] != "proven" and (r["verdicts"].get(c["id"]) not in (None, "met"))]
            tail = (f"{_name(r['reviewer'])} also did not say met on {', '.join(diff)}, so {'that clause is' if len(diff) == 1 else 'those clauses are'} refused"
                    if diff else "The finding alone routes the change to a human")
            callouts.append(f"{_names(quiet)} said met to all {n_cl} clauses; {_name(r['reviewer'])} raised a verified {f['severity']} finding "
                            f"they did not ({r['reviewer']}:{f['id']}: {f['title']}). {tail}. Unanimity is required: one verified objection is enough "
                            f"to send it to {p['owner']}.")
    for c in clauses:
        if any(x["code"] == "reviewers_disagree" for x in c["reasons"]):
            callouts.append(f"{c['id']}: {_verdict_groups(c)}. A split verdict is a refusal, not a vote.")
    return {"rows": rows, "callouts": list(dict.fromkeys(callouts)), "adjudicator": p["reviewer_panel"]["adjudicator"]}


def _card(p: dict, d: dict, trust_rows: list[dict], refusal_groups: list[dict]) -> dict:
    n_rev = len(p["reviewer_panel"]["reviewers"])
    # 1-3 reasons that set the tier, one per kind of driver, in words.
    def reasons_from(drivers: list[dict]) -> list[dict]:
        groups: dict[str, list[dict]] = {}
        for w in drivers:
            groups.setdefault(w["source"], []).append(w)
        reasons = []
        for source, ws_ in groups.items():
            if source == "mandate rule":
                reasons += [{"text": w["why"], "link": "#all-drivers"} for w in ws_]
            elif source == "verified finding":
                fs = sorted((f for f in p["findings"] if f"{f['reviewer']}:{f['id']}" in {w["id"] for w in ws_}),
                            key=lambda f: SEVERITIES.index(f["severity"]))
                f = fs[0]
                more = f" (and {_plural(len(fs) - 1, 'more finding')})" if len(fs) > 1 else ""
                reasons.append({"text": f"{_name(f['reviewer'])} found a verified {f['severity']} issue: {f['title']}{more}",
                                "link": f"#f-{f['reviewer']}-{f['id']}"})
            elif source == "refused clause":
                ids = [w["id"] for w in ws_]
                rows = [t for t in trust_rows if t["id"] in ids]
                whys = list(dict.fromkeys(t["why"] for t in rows))
                detail = whys[0] if len(whys) == 1 else f"{rows[0]['id']}: {rows[0]['why']}" + (f" (+{len(rows) - 1} more)" if len(rows) > 1 else "")
                reasons.append({"text": f"{len(ids)} of {len(p['requirements'])} requirement clauses not proven. {detail}",
                                "link": f"#chain-{ids[0]}"})
            elif source == "adjudicator":
                if {w["id"] for w in ws_} <= {w["id"] for w in groups.get("refused clause", [])}:
                    continue  # already said by the refused-clause reason
                reasons.append({"text": f"The adjudicator ({_name(p['adjudication']['reviewer'])}) found the evidence on {', '.join(w['id'] for w in ws_)} disputed",
                                "link": "#panel"})
            elif source == "reviewer refusal":
                reasons.append({"text": f"The AI declined to decide {_plural(len(refusal_groups), 'question')}, e.g. {refusal_groups[0]['topic']}"
                                if refusal_groups else "A reviewer declined to decide a topic", "link": "#refused"})
            elif source == "trust cap":
                reasons += [{"text": f"The AI may clear {w['id']} only up to {w['tier']}: {w['why'].split('(', 1)[-1].rstrip(')')}", "link": "#areas"} for w in ws_]
            elif source == "risk score":
                r = p["risk"]
                top = sorted((f for f in r["factors"] if f["points"]), key=lambda f: -f["points"])[:2]
                reasons.append({"text": f"Risk score {r['score']} reaches the {r['tier']} band (>= {r['thresholds'].get(r['tier'], 0)}), mostly "
                                        + " and ".join(f"{f['reason']} ({f['points']})" for f in top), "link": "#risk"})
        return reasons

    reasons = reasons_from(p["why"])
    if len(reasons) < 3:  # e.g. a block from a hard rule: also show what would still send it to a human
        rest = [w for w in p["drivers"] if w not in p["why"] and w["tier"] == "ask" and w["source"] in ("verified finding", "refused clause", "reviewer refusal")]
        reasons += [{**r, "text": "Also routes to a human. " + r["text"]} for r in reasons_from(rest)]
    shown = reasons[:3]

    sev = sorted(p["findings"], key=lambda f: (SEVERITIES.index(f["severity"]), f["reviewer"], f["id"]))
    found = [{"key": f"{f['reviewer']}:{f['id']}", "anchor": f"f-{f['reviewer']}-{f['id']}", "reviewer": f["reviewer"],
              "severity": f["severity"], "title": f["title"], "tier": f["tier"], "chips": _chips(f),
              "shared_with": _finding_shared(f, d["findings"])} for f in sev[:3]]

    not_checked = [{"id": x["id"], "reason": x["reason"]} for x in p["not_checked"] if x["source"] != "mandate known gap"]
    gaps = [x["id"] for x in p["not_checked"] if x["source"] == "mandate known gap"]

    residual = []
    for f in sev:
        if f["severity"] in ("blocker", "major"):
            residual.append({"text": f"Open {f['severity']} finding: {f['title']}", "link": f"#f-{f['reviewer']}-{f['id']}"})
    unproven = [t for t in trust_rows if t["status"] == "refused"]
    if unproven:
        residual.append({"text": f"Not proven by the AI: {', '.join(t['id'] for t in unproven)}. Signing means you judge them yourself.",
                         "link": f"#chain-{unproven[0]['id']}"})
    held = [t for t in trust_rows if t["status"] == "held_before"]
    if held:
        residual.append({"text": f"{', '.join(t['id'] for t in held)} already held before this change: met, but not achieved by it.",
                         "link": f"#chain-{held[0]['id']}"})
    if refusal_groups:
        residual.append({"text": f"{_plural(len(refusal_groups), 'question')} the AI declined to decide (listed above) are yours.", "link": "#refused"})
    for f in p["rejected_claims"]:
        if f["severity"] in ("blocker", "major"):
            residual.append({"text": f"Rejected for lack of evidence, not disproven: {f['title']} ({f['reviewer']}:{f['id']})",
                             "link": f"#f-{f['reviewer']}-{f['id']}"})
    if not_checked:
        residual.append({"text": "Not run: " + ", ".join(x["id"] for x in not_checked), "link": "#not-checked"})
    for a in p["areas"]:
        if a["cap"] != a["max_ai_tier"]:
            residual.append({"text": f"Area {a['name']} is on probation ({a['cap_reason']})", "link": "#areas"})
    for x in p["reviewer_panel"]["excluded"]:
        residual.append({"text": f"{_name(x['name'])} did not read this change: {x['reason']}", "link": "#panel"})
    if p["disputes"] and not p.get("adjudication"):
        residual.append({"text": f"{_plural(len(p['disputes']), 'disputed item')} not adjudicated", "link": "#panel"})
    if gaps:
        residual.append({"text": "Standing pipeline gaps: " + ", ".join(gaps), "link": "#not-checked"})

    s = p["signoff"]
    return {
        "tier": p["tier"], "owner": p["owner"], "fyi": p["notify"], "risk_score": p["risk"]["score"],
        "reasons": shown, "more_drivers": len(p["drivers"]),
        "trace": [{"id": t["id"], "status": t["status"], "label": t["label"], "why": t["why"], "anchor": f"chain-{t['id']}"} for t in trust_rows],
        "found": found, "found_total": len(p["findings"]), "rejected_total": len(p["rejected_claims"]),
        "refused": refusal_groups, "refused_clauses": [t["id"] for t in trust_rows if t["status"] == "refused"],
        "not_checked": not_checked, "known_gaps": gaps,
        "residual": residual,
        "sign": {"owner": s["owner"], "required": s["required"], "decisions": s["allowed_decisions"], "statement": s["statement"],
                 "command": s["command"]},
        "reviewers": n_rev,
    }
