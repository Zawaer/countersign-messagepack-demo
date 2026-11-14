"""Renderers for the evidence pack: the CLI sign-off card, pack.md (GitHub PR comment) and pack.html.

They only format what is in pack.json (pack.build puts the reader's view there: story, card, trust chains, reviewer
panel and an evidence index with code excerpts), so what the owner reads is exactly what the pack hash covers.
Layout, top to bottom: the one-screen sign-off card; where the trust comes from (per clause); the reviewer panel;
the evidence (findings, code excerpts, test runs, checks); and, folded, the full detail (all drivers, risk, checks).
"""

from __future__ import annotations

import hashlib
import html
import json
import re
from pathlib import Path

from .icons import CSS as ICON_CSS, icon


TAGLINE = "AI reviews code; a named human signs."  # same line as the site header (site/scene.py)

STATUS = {  # label -> (css class, glyph, what it means)
    "proven": ("proven", "\u2713", "every reviewer said met with verified evidence and the clause's checks pass"),
    "held before": ("held", "=", "met, but already true before this change (its tests pass without the fix)"),
    "refused": ("refused", "?", "the AI could not prove it: a human decides"),
    "not met": ("notmet", "\u2715", "a reviewer says the clause is not met"),
}
VERDICT_SHORT = {"met": "met", "not_met": "not met", "cannot_determine": "can't tell", None: "no review"}
SEV_ORDER = ["blocker", "major", "minor", "info"]


def _name(n: str) -> str:
    return {"claude": "Claude", "codex": "Codex", "nemotron": "Nemotron", "gemini": "Gemini"}.get(n, n[:1].upper() + n[1:])


def _short_id(cid: str) -> str:
    """REQ-2234-F1 -> F1 (the trace is per change, so the prefix is noise on a phone)."""
    parts = cid.split("-")
    return parts[-1] if len(parts) >= 3 else cid


def _rulings(p: dict) -> list[dict]:
    return [r for r in (p.get("adjudication") or {}).get("rulings", []) if not r.get("stale")]


ADJ_PHRASE = "the adjudicator disputes it"  # pack.json's generic wording; the render says what the ruling found


def _objection(p: dict, cid: str) -> str | None:
    """What the adjudicator's ruling on a clause says about the 'not met' side, in words:
    `Gemini: Claude's objection is supported` when it backs a claim by a reviewer who said not met."""
    r = next((x for x in _rulings(p) if str(x.get("dispute")) == cid), None)
    if not r:
        return None
    adj = _name(p["adjudication"]["reviewer"])
    tr = next((x for x in p.get("trust", []) if x["id"] == cid), None)
    no = [v["reviewer"] for v in (tr or {}).get("reviewers", []) if v["verdict"] != "met"]
    if not no:
        return f"{adj} ruled on it (advisory)"
    backed = [n for n in no if any(x.get("reviewer") == n for x in r.get("supported", []))]
    who = " and ".join(_name(n) for n in (backed or no))
    return (f"{adj}: {who}'s objection is supported" if backed else f"{adj} does not back {who}'s objection")


def view(p: dict) -> dict:
    """The pack as rendered: a copy where the generic `the adjudicator disputes it` names the ruling's outcome.
    Render only: pack.json (what the owner signs) is never changed."""
    if not _rulings(p) or ADJ_PHRASE not in json.dumps(p):
        return p

    def fix(text: str, cid: str | None) -> str:
        out, pos = "", 0
        for m in re.finditer(re.escape(ADJ_PHRASE), text):
            ids = re.findall(r"REQ-[A-Za-z0-9]+-[A-Za-z0-9]+", text[:m.start()])
            said = _objection(p, ids[-1] if ids else cid or "")
            out += text[pos:m.start()] + (said or ADJ_PHRASE)
            pos = m.end()
        return out + text[pos:]

    def walk(o, cid):
        if isinstance(o, dict):
            here = o.get("id") if str(o.get("id", "")).startswith("REQ-") else cid
            return {k: walk(v, here) for k, v in o.items()}
        if isinstance(o, list):
            return [walk(v, cid) for v in o]
        return fix(o, cid) if isinstance(o, str) and ADJ_PHRASE in o else o

    return walk(p, None)


# --- first-screen shortening (render only: the full text is always one tap away, in a fold) -------------------------

REASON_SEPS = (". ", " (and ", ", e.g. ", ", mostly ")  # never split "major issue: <title>": the title is the story
TEXT_SEPS = (": ", "; ", ". ", ", so ", " (")


def _split(text: str, limit: int, seps: tuple = TEXT_SEPS, least: int = 24) -> tuple[str, str]:
    """(headline, rest): cut a long sentence at its first natural break (outside parentheses) that leaves a headline of
    `least`..`limit` characters, trying the separators in order. Short text, text with no such break, or a rest too
    short to be worth a tap stays whole."""
    head, rest = _split_at(text, limit, seps, least)
    return (text, "") if rest and len(rest) < 36 else (head, rest)


def _split_at(text: str, limit: int, seps: tuple, least: int) -> tuple[str, str]:
    if len(text) <= limit:
        return text, ""
    depth, top = 0, []
    for ch in text:
        top.append(depth == 0)
        depth += (ch in "([") - (ch in ")]")
    for sep in seps:
        i = text.find(sep, least)
        while 0 <= i <= limit and (not top[i] or sep == ". " and text[max(0, i - 3):i] in ("e.g", "i.e")):
            i = text.find(sep, i + 1)
        if 0 <= i <= limit:
            return text[:i + 1] if sep == ". " else text[:i], text[i:].lstrip(".;:, ")
    if seps is REASON_SEPS or len(text) <= 2 * limit:
        return text, ""
    near = [i for i in (next((j for j in _finds(text, sep, least) if top[j]), -1) for sep in seps) if 0 <= i <= 2 * limit]
    if near:  # a wall of text: its first full clause, if that is short enough
        i = min(near)
        return text[:i + 1] if text[i:i + 2] == ". " else text[:i], text[i:].lstrip(".;:, ")
    cut = next((i for i in range(limit, least, -1) if text[i] == " " and top[i]), limit)  # a wall of text: cut at a word
    return text[:cut] + " \u2026", "\u2026" + text[cut:]


def _finds(text: str, sep: str, start: int):
    i = text.find(sep, start)
    while i >= 0:
        yield i
        i = text.find(sep, i + 1)


def _mutation_detail(t: dict | None) -> str | None:
    return next((r["detail"] for r in (t or {}).get("reasons", []) if r.get("code") == "tests_kill_no_mutant"), None)


def _mutation_short(detail: str) -> str:
    """`the tests supporting REQ-x (...) kill no mutant on its lines (...); no test kills any of the 2 mutant(s) there`
    -> `Its tests kill none of the 2 planted mutants on its lines`."""
    m = re.search(r"any of the (\d+) mutant", detail)
    n = int(m.group(1)) if m else 0
    return (f"Its tests kill none of the {n} planted mutant{'' if n == 1 else 's'} on its lines" if n
            else "Its tests kill no planted mutant on its lines")


def _mutation_check_line(p: dict) -> str | None:
    """tests.mutation in one line: `tests kill 2 of 8 planted mutants; survivors at TypeCollector.cs:239, ...`."""
    c = next((t for t in p["checked_by"]["tools"] if t["id"] == "tests.mutation"), None)
    m = re.match(r"(\d+) mutants? of the changed source lines: (\d+) killed", (c or {}).get("summary") or "")
    if not m:
        return None
    surv = re.search(r"surviving hunks: ([^;]+)", c["summary"])
    return f"tests kill {m.group(2)} of {m.group(1)} planted mutants" + (f"; survivors at {surv.group(1)}" if surv else "")


def _trace_why(p: dict, t: dict) -> tuple[str, str]:
    """The trace row's headline and the rest. A mutation refusal becomes one plain line; its detail is folded."""
    tr = next((x for x in p["trust"] if x["id"] == t["id"]), None)
    det = _mutation_detail(tr)
    if det and t["why"].lower().startswith(det.lower()[:40]):
        line = _mutation_check_line(p)
        return _mutation_short(det), t["why"] + (f". Whole change: {line}." if line else "")
    return _split(t["why"], 80)


def _ruling_line(p: dict, r: dict) -> str:
    """One plain line per adjudicated dispute: `Gemini on N1: Claude's objection is supported` when the ruling says so in
    words, else counted from its own supported/unsupported claims. The full ruling is folded under it."""
    adj = _name(p["adjudication"]["reviewer"])
    claims = [(x.get("reviewer"), True) for x in r.get("supported", [])] + [(x.get("reviewer"), False) for x in r.get("unsupported", [])]

    def tally(ns: set) -> tuple[int, int]:
        mine = [ok for n, ok in claims if n in ns]
        return sum(mine), len(mine)

    dispute = str(r.get("dispute", ""))
    if dispute.startswith("finding:"):
        who, _, fid = dispute.split(":", 1)[1].partition(":")
        k, n = tally({who})
        return f"{adj} on {_name(who)} {fid}: backs {k} of {n} of its claims"
    tr = next((x for x in p["trust"] if x["id"] == dispute), None)
    verdicts = {v["reviewer"]: v["verdict"] for v in (tr or {}).get("reviewers", [])}
    no = [n for n, v in verdicts.items() if v != "met"]
    yes = {n for n, v in verdicts.items() if v == "met"}
    parts = []
    if no:
        k, n = tally(set(no))
        parts.append(f"{k} of {n} claims for {' and '.join(_name(x) for x in no)}'s 'not met'")
    if yes:
        k, n = tally(yes)
        parts.append(f"{k} of {n} for 'met'")
    said = _objection(p, dispute) if no else None
    if said:  # the ruling in words; the per-side claim counts read as a split, so they stay in the folded ruling
        return f"{adj} on {_short_id(dispute)}: {said.split(': ', 1)[-1] if said.startswith(adj + ':') else said}"
    return f"{adj} on {_short_id(dispute)}: " + (("backs " + ", ".join(parts)) if parts else "see the full ruling")


def _short_command(sg: dict) -> str:
    """`countersign sign 2234 --as Toivo --decision … --note "…"`: the shape, without the alternatives."""
    return re.sub(r'"\.\.\."', '"…"', re.sub(r"<[^>]+>", "…", sg["command"]))


def _sim(p: dict) -> bool:
    return bool(p.get("simulated"))


def _html_inline(t: str) -> str:
    return html.escape(t, quote=False)


def _peripheral(c: dict) -> str:
    n = len(c.get("refused_peripheral") or [])
    return f"{n} peripheral refusal{'' if n == 1 else 's'}"


def _more_risks(c: dict) -> str:
    n = len(c.get("residual_more") or [])
    return f"{n} more risk{'' if n == 1 else 's'} that do not set the tier"


# --- the story card: the first screen of pack.html and pack.md (render only) --------------------------------------
# One verdict, the change in one line, one short reason and three marks (checks, reviewers, signature). Everything
# else sits behind one "Evidence" fold. The signature line comes from the signed ledger: a sign-off counts for this
# pack only if its pack_sha256 is this pack's hash (a sign-off of an earlier version says so).

WHY_WORDS = 12
_WHY_CUTS = (" about ", " because ", " when ", " for ", " in ", " on ", " with ")


def _words(s: str) -> int:
    return len(s.split())


def _why(p: dict) -> str:
    """The deciding reason in at most WHY_WORDS words, cut at a natural break of the pack's own text."""
    reasons = (p.get("card") or {}).get("reasons") or []
    if not reasons:
        return {"silent": "Everything mandated was proven", "notify": "Everything mandated was proven"}.get(p.get("tier"), "See the evidence")
    t = re.sub(r"\s*\[[^\]]*\]$", "", reasons[0]["text"]).strip()
    t = re.sub(r"^Also routes to a human\.\s*", "", t)
    m = re.match(r"\w+ found a verified (?:major|blocker|minor) issue: (.*)", t)
    if m:
        t = m.group(1)
    t = re.sub(r" \(and \d+ more findings?\)$", "", t)
    if _words(t) > WHY_WORDS and "; " in t:  # "X; so Y": the conclusion is the reason
        t = next((x for x in reversed(t.split("; ")) if _words(x) <= WHY_WORDS), t)
    for sep in (": ", ", e.g. ", " (", ", mostly ", ". ", ", "):
        if _words(t) > WHY_WORDS and sep in t:
            t = t.split(sep, 1)[0]
    for sep in _WHY_CUTS:
        if _words(t) > WHY_WORDS and sep in t:
            t = t.split(sep, 1)[0]
    if _words(t) > WHY_WORDS:
        t = " ".join(t.split()[:WHY_WORDS]) + "…"
    return t[:1].upper() + t[1:].rstrip(".")


def _ledger_paths() -> list[Path]:
    here = Path(__file__).resolve().parent.parent
    return list(dict.fromkeys([Path.cwd() / "ledger" / "ledger.jsonl", here / "ledger" / "ledger.jsonl"]))


def _signoff(p: dict, ledger: list[dict] | None = None) -> dict | None:
    """The newest ledger sign-off for this change: {signer, decision, ts, current} (current: it covers this exact pack).
    `ledger`: the entries to read (None: the workspace's ledger/ledger.jsonl)."""
    # common.canonical + sha256_hex, inlined: site/build.py imports this module without PyYAML
    want = hashlib.sha256(json.dumps(p, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()
    if ledger is None:
        ledger = []
        for path in _ledger_paths():
            try:
                ledger = [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]
            except (OSError, ValueError):
                continue
            if ledger:
                break
    best = None
    for e in ledger:
        pl = e.get("payload") or {}
        if e.get("type") == "signoff" and pl.get("change") == p.get("change"):
            cur = pl.get("pack_sha256") == want
            if cur or not (best and best["current"]):
                best = {"signer": e.get("signer"), "decision": pl.get("decision"), "ts": e.get("ts"), "seq": e.get("seq"), "current": cur}
    return best


_FAILED = {"tests.execution_fail_without_fix": "the new runtime tests pass without the fix",
           "tests.fail_without_fix": "the new tests pass without the fix",
           "public_api": "it adds public API", "solution_membership": "a new project is not in the solution",
           "injection_scan": "it hides instructions to the AI", "deps.delta": "it adds a vulnerable dependency",
           "build.egress": "the build reached a blocked host", "craci.network": "the build broke the network policy"}


def _check_failed(t: dict) -> str:
    """A failing check in a few plain words, from its id and summary: `3 of 8 planted mutants survive`."""
    summ = t.get("summary") or ""
    if t["id"] == "tests.mutation":
        m = re.match(r"(\d+) mutants? of the changed source lines: \d+ killed, (\d+) survived", summ)
        if m:
            return f"{m.group(2)} of {m.group(1)} planted mutants survive"
    if t["id"] == "analyzers":
        m = re.match(r"(\d+) new warnings?", summ)
        if m:
            return f"{m.group(1)} new analyzer warning{'' if m.group(1) == '1' else 's'}"
    return _FAILED.get(t["id"], f"{t['id']} fails")


def _marks(p: dict, so: dict | None) -> list[tuple[str, str, str]]:
    """Three (class, glyph, words): checks, reviewers, signature."""
    tools = [t for t in p["checked_by"]["tools"] if t.get("status") in ("pass", "fail")]
    bad = [t["id"] for t in tools if t["status"] == "fail"]
    core = [t for t in tools if t["id"] in ("build", "tests.full_suite")]
    if bad and core and all(t["status"] == "pass" for t in core):
        named = [_check_failed(t) for t in tools if t["status"] == "fail"]
        more = len(named) - 2
        out = [("warn", "!", "Builds, tests pass; but " + (" and ".join(named) if more <= 0
                else f"{', '.join(named[:2])} and {more} more check{'s' if more != 1 else ''} fail"))]
    else:
        out = [("bad", "✕", f"{len(bad)} of {len(tools)} checks fail") if bad else ("ok", "✓", f"All {len(tools)} checks pass")]
    major = [f for f in p.get("findings", []) if f.get("status") == "verified" and f.get("severity") in ("blocker", "major")]
    c = p.get("card") or {}
    open_q = len(c.get("refused") or []) + len(c.get("refused_clauses") or [])
    if major:
        out.append(("bad", "✕", f"Reviewers found {'a major issue' if len(major) == 1 else str(len(major)) + ' major issues'}"))
    elif open_q:
        out.append(("warn", "?", f"Reviewers left {open_q} question{'' if open_q == 1 else 's'} open"))
    else:
        out.append(("ok", "✓", "Reviewers: every requirement met"))
    owner = p.get("owner") or "the owner"
    dec = (so or {}).get("decision", "").replace("-", " ")
    if so and so["current"]:
        out.append(("ok", "✓", f"Signed by {so['signer']}: accept") if dec == "accept"
                   else ("bad", "✕", f"Signed by {so['signer']}: {dec}"))
    elif so:
        out.append(("warn", "!", f"{so['signer']} signed an earlier version: {dec}"))
    elif not (p.get("signoff") or {}).get("required", True):
        out.append(("ok", "✓", f"No signature needed: {owner} is told"))
    else:
        out.append(("warn", "…", f"Awaiting {owner}'s countersignature"))
    return out


def _change_line(p: dict) -> str:
    h = (p.get("story") or {}).get("headline", "")
    return re.sub(r"^(?:Agent-written )?[Cc]hange for (#\S+):\s*", r"\1 ", h) or f"Change {p['change']}"


# --- CLI ------------------------------------------------------------------------------

def card(p: dict) -> str:
    p = view(p)
    c, s = p["card"], p["story"]
    out = [f"Countersign evidence pack, change {p['change']} ({p['branch']} {p['base']}..{p['head']})" + (" [SIMULATED]" if _sim(p) else ""),
           s["headline"], "",
           f"Recommended tier: {p['tier'].upper()}    owner: {p['owner']}" + (f" (FYI {', '.join(p['notify'])})" if p["notify"] else ""),
           "Why:", *(f"  {i}. " + _cli_line(*_split(r["text"], 110, REASON_SEPS)) for i, r in enumerate(c["reasons"], 1))]
    if c["more_drivers"]:
        out.append(f"     (all {c['more_drivers']} tier drivers are in the pack)")
    out += ["", "Requirement trace:"]
    out += [f"  {t['id']:<14} {t['label'].upper():<12} " + _cli_line(*_trace_why(p, t)) for t in c["trace"]]
    out += [f"  {_ruling_line(p, r)} (advisory; full ruling in the pack)" for r in _rulings(p)]
    out += ["", "What the AI found:"] + ([f"  [{f['severity']}] {f['title']} ({f['key']})" for f in c["found"]] or ["  no verified findings"])
    if c["found_total"] > len(c["found"]):
        out.append(f"  (+{c['found_total'] - len(c['found'])} more)")
    out += ["", "What the AI refused to decide, and who should:"]
    out += [f"  - {g['topic']} -> {'; '.join(g['who_should_decide'])} (raised by {', '.join(_name(n) for n in g['raised_by'])})" for g in c["refused"]]
    if c["refused_clauses"]:
        out.append(f"  - whether {', '.join(c['refused_clauses'])} {'is' if len(c['refused_clauses']) == 1 else 'are'} met -> {p['owner']}")
    if c.get("refused_peripheral"):
        out.append(f"  ({_peripheral(c)}, out of scope: in the pack)")
    if not (c["refused"] or c["refused_clauses"]):
        out.append("  nothing")
    sc = p.get("supply_chain")
    if sc:
        out += ["", f"Supply chain (from the build): {sc['line']}"]
        out += [f"  NEW ADVISORY {v['package']} {v['version']} {v['severity']} {v['id']}" for v in (sc.get("deps") or {}).get("vulnerabilities_new", [])]
    out += ["", "Not checked:"] + [f"  {x['id']}: " + _cli_line(*_split(x["reason"], 60)) for x in c["not_checked"]]
    if c["known_gaps"]:
        out.append(f"  standing gaps: {', '.join(c['known_gaps'])}")
    out += ["", "Residual risk you accept by signing:"] + [f"  - {r['text']}" for r in c["residual"]]
    if c.get("residual_more"):
        out.append(f"  (+{len(c['residual_more'])} more in the pack)")
    sg = c["sign"]
    out += ["", f"{sg['owner']} signs: {sg['statement']}", "  " + _short_command(sg)]
    fs = sg.get("findings") or []
    if fs:
        out.append(f"  and rate the {len(fs)} verified finding{'' if len(fs) == 1 else 's'}, one flag each (unrated if left out): "
                   f"--finding {fs[0]['ref']}=<accepted|rejected|unsure>" + (f" ... {fs[-1]['ref']}" if len(fs) > 1 else ""))
        out.append("  (" + ", ".join(f"{r['ref']} {r['severity']}" for r in fs) + "; the full command is in pack.md)")
    return "\n".join(out)


def _cli_line(head: str, rest: str) -> str:
    return head + (" [...]" if rest else "")


# --- Markdown (GitHub PR comment) ---------------------------------------------------------

def _cell(x) -> str:
    return str("" if x is None else x).replace("|", "\\|").replace("\n", " ")


def _md_code(ex: dict, path: str) -> list[str]:
    width = len(str(ex["start"] + len(ex["lines"])))
    body = [f"{'>' if n == ex['highlight'] else ' '} {n:>{width}} | {line}"
            for n, line in enumerate(ex["lines"], ex["start"])]
    fence = "````" if any("```" in x for x in body) else "```"
    return [f"{fence}text", f"// {path} @ {ex['sha']}", *body, fence]


def _md_sign(sg: dict) -> list[str]:
    out = [f"**{sg['owner']} signs** ({'required' if sg['required'] else 'not required: AI-cleared, spot-checks apply'}; "
           f"{', '.join(sg['decisions'])})", "", f"```\n{_short_command(sg)}\n```", ""]
    n = len(sg.get("findings") or [])
    if n:
        out += [f"<details><summary>And rate the {n} verified finding{'' if n == 1 else 's'} (full command)</summary>", "",
                "One `--finding` flag each: `accepted` (real), `rejected` (a false positive) or `unsure`, optionally `:reason`. "
                "A finding without a flag is recorded as `unrated`.", ""]
        out += [f"- `{r['ref']}` ({r['severity']}): {_html_inline(r['title'])}" for r in sg["findings"]]
        out += ["", f"```\n{sg.get('command_with_findings', sg['command'])}\n```", "", "</details>", ""]
    out += ["<details><summary>What your signature says</summary>", "", f"> {sg['statement']}", "",
            "It covers the sha256 of this pack's canonical JSON, the decision, your verdict on each finding, the time and the signer, "
            "and is appended to the hash-chained ledger.", "", "</details>", ""]
    return out


def _md_evidence(p: dict, excerpts: bool = True) -> list[str]:
    out = ["<details><summary><b>Cited evidence</b> (code excerpts, test runs, checks)</summary>", ""]
    for ref, e in p["evidence_index"].items():
        mark = "verified" if e["verified"] else "NOT verified"
        out += [f"<a id=\"{ref}\"></a>", f"**{e['label']}** ({mark}; cited by {', '.join(e['cited_by'])}): {e['note']}", ""]
        if e["kind"] == "code" and e.get("excerpt") and excerpts:
            out += _md_code(e["excerpt"], e["file"]) + [""]
        elif e["kind"] == "code" and e.get("quote"):
            out += [f"`{_cell(e['quote'])}`", ""]
        elif e["kind"] == "test":
            out += [f"- {r['run']} (`{r['check']}`{', ' + r['project'] if r.get('project') else ''}): **{r['outcome']}**" for r in e.get("runs", [])]
            if e.get("without_fix"):
                out.append(f"- Without the fix it **{e['without_fix']}**: " + ("it tests the change" if e["without_fix"] == "failed" else "it does not show the change"))
            out.append("")
        elif e["kind"] == "check" and e.get("check_result"):
            cr = e["check_result"]
            out += [f"- `{e['id']}` **{cr['status']}**: {cr.get('summary') or ''} ({cr.get('tool') or ''} {cr.get('tool_version') or ''})".rstrip(),
                    *(f"- log: `{x}`" for x in cr["logs"]), ""]
        elif e["kind"] == "requirement":
            out += [f"> {e.get('clause_text') or ''}", ""]
    return out + ["</details>", ""]


def _md_full(p: dict) -> list[str]:
    rp = p["reviewer_panel"]
    ms = p["mandate"]["signature"]
    out = ["<details><summary><b>Full detail</b>: tier drivers, risk score, engine codes, areas</summary>", "",
           f"Branch `{p['branch']}` ({p['base']}..{p['head']}), {p['diff']['files']} files, +{p['diff']['insertions']} -{p['diff']['deletions']}. "
           f"Author {p['author']} (agent-written: {p['agent_written']}). Commit: {p['commit_message']}", "",
           f"Mandate `{p['mandate']['id']}` v{p['mandate']['version']} sha256 `{p['mandate']['sha256'][:16]}`, signature: "
           + (f"valid, {ms.get('signed_by', '')}" if ms["valid"] else f"NOT VALID ({ms['reason']})"), "",
           "<a id=\"all-drivers\"></a>", "#### All tier drivers (tier = strictest)", ""]
    out += [f"- {w['tier']}: {w['source']} `{w['id']}`: {w['why']}" for w in p["drivers"]]
    out += ["", "#### Who reviewed", "",
            f"Participating reviewers: {', '.join(rp['reviewers']) or 'none'}. Adjudicator: {rp['adjudicator'] or 'none'}. "
            f"Confidential: {'yes (' + rp['why'] + ')' if rp['confidential'] else 'no'}. Rule: {rp['rule']}."]
    out += [f"- Excluded **{x['name']}** ({x['vendor']}, {x['role']}): {x['reason']}" for x in rp["excluded"]]
    out += [f"- Not used: `{x['name']}`: {x['reason']}" for x in rp["ignored_files"]]
    out += ["", "| Reviewer | Model | Prompt | Verified findings | Rejected | Refusals |", "|---|---|---|---|---|---|"]
    out += [f"| {r['reviewer']} | {r['model']} ({r['vendor']}) | {r['prompt_version']} | {r['verified']} | {r['rejected']} | {r['refusals']} |"
            for r in p["checked_by"]["reviewers"]]
    out += ["", "#### Every check", "", "| Check | Status | Tool | Summary |", "|---|---|---|---|"]
    out += [f"| {t['id']} | {t['status']} | {_cell((t.get('tool') or '') + ' ' + (t.get('tool_version') or ''))} | {_cell(t.get('summary'))} |"
            for t in p["checked_by"]["tools"]]
    out += ["", f"Decision engine: {p['checked_by']['engine']}", "", "#### Requirement trace (engine codes)", "",
            "| Clause | Status | Verdicts | Checks | Reasons |", "|---|---|---|---|---|"]
    out += [f"| {c['id']} | {c['status']} | " + ", ".join(f"{n}: {v['verdict']} ({v['verified']}/{v['cited']})" for n, v in c["verdicts"].items())
            + f" | {', '.join(x['id'] + ': ' + x['status'] for x in c['checks']) or '-'} | {', '.join(dict.fromkeys(r['code'] for r in c['reasons'])) or '-'} |"
            for c in p["requirements"]]
    out += ["", "#### What the AI refused to decide (every reviewer refusal)", ""]
    out += [f"- **{r['reviewer']}** refused: {r['topic']}. Why: {r['reason']} Who should decide: {r['who_should_decide']}" for r in p["refused"]["reviewer_refusals"]] or ["- none"]
    out += ["", "<a id=\"areas\"></a>", "#### Areas", "", "| Area | Owner | Sensitivity | AI cap | Files |", "|---|---|---|---|---:|"]
    out += [f"| {a['name']} | {a['owner']} | {a['sensitivity']} | {a['cap']} ({a['cap_reason']}) | {len(a['files'])} |" for a in p["areas"]]
    out += ["", "<a id=\"not-checked\"></a>", "#### What was not checked, and why", ""] + [f"- `{x['id']}` ({x['source']}): {x['reason']}" for x in p["not_checked"]]
    out += ["", "#### Residual risk (every item)", ""] + [f"- {r}" for r in p["residual_risk"]]
    out += ["", "<a id=\"risk\"></a>", f"#### Risk score: {p['risk']['score']} -> {p['risk']['tier']}", "", "| Factor | Points | Reason |", "|---|---:|---|"]
    out += [f"| {f['factor']} | {f['points']} | {_cell(f['reason'])} |" for f in p["risk"]["factors"]]
    out += [f"| **total** | **{p['risk']['score']}** | bands: {_cell(p['risk']['thresholds'])} |", "",
            f"Inputs: facts `{p['inputs']['facts']['path']}`, requirements `{p['inputs']['requirements']['path']}`, reviews "
            + ", ".join(f"`{v['path']}`" for v in p["inputs"]["reviews"].values()), "", "</details>", ""]
    return out


def _md_supply(p: dict) -> list[str]:
    """One line, new advisories in plain sight, everything else in a fold."""
    sc = p.get("supply_chain")
    if not sc:
        return []
    out = ["<a id=\"supply-chain\"></a>**Supply chain (from the build):** " + _cell(sc["line"]), ""]
    deps = sc.get("deps") or {}
    for v in deps.get("vulnerabilities_new", []):
        out.append(f"- **New advisory** {v['package']} {v['version']} ({v['severity']}): [{v['id']}]({v['advisory']})")
    out += [f"- **{r['tier']}** `{r['id']}`: {_cell(r['evidence'])}" for r in sc["rules"]]
    if deps.get("vulnerabilities_new") or sc["rules"]:
        out.append("")
    body = []
    if deps:
        body += [f"`deps.delta` **{deps['status']}**: {_cell(deps['summary'])}", ""]
        if deps["packages"]:
            body += ["| Package | Base | Head | Direct | Via |", "|---|---|---|---|---|"]
            body += [f"| {_cell(x['package'])} | {_cell(x['base'] or '-')} | {_cell(x['head'])} | {'direct' if x['direct'] else 'transitive'} | {_cell(x['via'])} |"
                     for x in deps["packages"]]
            body.append("")
        body += [f"- New project: `{x}`" for x in deps["projects_added"]]
        body += [f"- New project reference: `{x['project']}` -> `{x['references']}`" for x in deps["project_references_added"]]
        body += [f"- Build inputs changed: {k}: {_cell(v.get('base'))} -> {_cell(v.get('head'))}" for k, v in deps["build_inputs_changed"].items()]
        if deps["vulnerabilities_also_on_base"]:
            body.append(f"- Already on base ({len(deps['vulnerabilities_also_on_base'])}): "
                        + ", ".join(f"{v['package']} {v['version']} {v['severity']} {v['id']}" for v in deps["vulnerabilities_also_on_base"]))
        if (deps.get("sbom") or {}).get("head"):
            body.append(f"- SBOMs (CycloneDX): `{deps['sbom']['base']}`, `{deps['sbom']['head']}`")
    eg = sc.get("egress")
    if eg:
        pol = eg["policy"]
        body.append(f"- `build.egress` **{eg['status']}**: default {pol.get('default')}, presets {pol.get('presets')}, "
                    f"{len(pol.get('tls_server_name_patterns') or [])} TLS host patterns"
                    + (f"; run {eg['run']}" if eg.get("run") else "") + (f"; blocked: {', '.join(eg['blocked_hosts'])}" if eg["blocked_hosts"] else "")
                    + (f"; policy sha256 `{eg['policy_sha256'][:12]}`" if eg.get("policy_sha256") else ""))
    net = sc.get("craci_network")
    if net:
        body.append(f"- `craci.network` **{net['status']}**: {_cell(net['summary'])}")
        body += [f"  - proxy violation: {_cell(v.get('host'))} ({_cell(v.get('reason'))})" for v in net["proxy_violations"]]
    if body:
        out += ["<details><summary>Supply-chain detail</summary>", "", *body, "", "</details>", ""]
    return out


# --- the compact Evidence fold in Markdown (pack.md and the PR comment): the same rows as pack.html ----------------
# GitHub renders no SVG and no Markdown inside <summary>, so a row is `<details><summary>EMOJI <b>name</b> verdict
# · file:line</summary>` with its few detail lines below in Markdown, and links to the source files for the full text.

MD_MARK = {"pass": "✅", "fail": "❌", "warn": "⚠️", "partial": "⚠️", "unknown": "❓",
           "pending": "⏳", "finding": "\U0001f41e", "person": "\U0001f464", "adjudicator": "⚖️", "repro": "\U0001f9ea"}
MD_SEV = {"blocker": "\U0001f534", "major": "\U0001f534", "minor": "\U0001f7e1", "info": "⚪"}


def _md_link(rel: str | None, label: str = "full text") -> str:
    return f"[{label}]({BLOB}{rel})" if rel else ""


def _md_short(text, rel: str | None = None, limit: int = 140) -> str:
    head, cut = _first(text, limit)
    return head + (" " + _md_link(rel) if cut and rel else "")


def _md_row(mark: str, summary: str, body: list[str], anchor: str = "") -> list[str]:
    """One row: `summary` is HTML (escaped by the caller); `body` Markdown lines, folded under it."""
    a = [f'<a id="{anchor}"></a>', ""] if anchor else []
    if not body:
        return a + [f"{mark} {summary}", ""]
    return a + [f"<details><summary>{mark} {summary}</summary>", "", *body, "", "</details>", ""]


def _md_loc(refs: list, ev: dict) -> tuple[str, str]:
    """(` · file:line` for the summary, a Markdown link to its excerpt for the body)."""
    es = [ev[r] for r in refs if r in ev and ev[r]["kind"] == "code"]
    e = next((x for x in es if x["verified"]), None) or next(iter(es), None)
    if not e:
        return "", ""
    lab = e["label"].removesuffix(" @head")
    return f" · {_html_inline(lab)}", f"- Cited: [`{lab}`](#{e['ref']})"


def _md_ruling_lines(p: dict, r: dict) -> list[str]:
    settle = r.get("evidence_that_would_settle") or []
    return [f"- **{_ruling_line(p, r)}** (advisory)" + (f": {_md_short(r['note'])}" if r.get("note") else "")
            + (f" Would settle it: {_md_short(settle[0], None, 120)}" if settle else "") + f" {_md_link(_adj_path(p), 'full ruling')}"]


def _md_clause(p: dict, t: dict, rulings: dict) -> list[str]:
    ev, ru = p["evidence_index"], rulings.get(t["id"])
    no = [r for r in t["reviewers"] if r["verdict"] != "met"]
    loc, cited = _md_loc([x for r in (no or t["reviewers"]) for x in r["refs"]], ev)
    body = [f"> {_md_short(t['text'], p['inputs']['requirements']['path'], 220)}", ""]
    if t["status"] == "held_before" or (not no and t["status"] != "proven"):
        body.append(f"- {_md_short(t['why'], _pack_path(p), 160)}")
    if t["status"] in ("proven", "held_before"):
        body.append("- " + ", ".join(f"**{_name(r['reviewer'])}** met ({r['verified']} of {r['cited']} cited verified)" for r in t["reviewers"]))
    else:
        body += [f"- **{_name(r['reviewer'])}** {VERDICT_SHORT.get(r['verdict'], r['verdict'])} ({r['verified']} of {r['cited']} cited verified): "
                 f"{_md_short(r['basis'], _rev_path(p, r['reviewer']))}" for r in t["reviewers"]]
        body += [f"- **{_name(x)}**: no review" for x in t["missing"]]
    body.append("- Checks: " + (", ".join(f"`{x['id']}` {x['status']}" for x in t["checks"]) or "none mandated"))
    fails = ", ".join(f"`{x['name'].rsplit('.', 1)[-1]}`" for x in t["tests_fail_without_fix"])
    passes = ", ".join(f"`{x['name'].rsplit('.', 1)[-1]}`" for x in t["tests_pass_without_fix"])
    body += ([f"- Fail without the fix: {fails}"] if fails else []) + ([f"- Pass without the fix: {passes}"] if passes else [])
    body += _md_ruling_lines(p, ru) if ru else ([f"- Would settle it: {_md_short(t['settle'][0], _pack_path(p), 120)}"] if t.get("settle") else [])
    body += [cited] if cited else []
    mark = MD_MARK[{"proven": "pass", "held before": "partial", "refused": "unknown", "not met": "fail"}.get(t["label"], "unknown")]
    return _md_row(mark, f"<b>{_short_id(t['id'])}</b> {_html_inline(_clause_verdict(p, t, ru))}{loc}", body, f"chain-{t['id']}")


def _md_finding(p: dict, f: dict, rulings: dict) -> list[str]:
    path = _rev_path(p, f["reviewer"])
    rep = (f.get("repro") or {}).get("status") == "reproduced"
    loc, cited = _md_loc([e.get("ref") for e in f["evidence"]], p["evidence_index"])
    body = [f"- {_md_short(f['claim'], path)}"]
    if f.get("repro"):
        body.append(f"- {MD_MARK['repro']} `{f['repro'].get('check')}`: {f['repro'].get('summary')}")
    if f.get("suggested_fix"):
        body.append(f"- **Fix:** {_md_short(f['suggested_fix'], path)}")
    body.append(f"- Rejected: {_md_short(f.get('rejection_reason'), path)}" if f["status"] == "rejected"
                else f"- Sets {f['tier']}: {f.get('tier_reason', '')}")
    for k, r in rulings.items():
        if k.startswith("finding:") and _finding_of(p, k) is f:
            body += _md_ruling_lines(p, r)
    body += [cited] if cited else []
    return _md_row(MD_MARK["finding"], f"<b>{_name(f['reviewer'])} {f['id']}</b> {f['severity']}: {_html_inline(f['title'])}"
                   + (f" {MD_MARK['repro']} reproduced" if rep else "") + loc, body, f"f-{f['reviewer']}-{f['id']}")


def _md_findings(p: dict, rulings: dict) -> list[str]:
    shown = [f for f in p["findings"] if _keep(f)]
    rest = [f for f in p["findings"] if not _keep(f)] + p["rejected_claims"]
    out = [x for f in shown for x in _md_finding(p, f, rulings)]
    if rest:
        sev = [s for s in SEV_ORDER if any(f["severity"] == s for f in rest)]
        out += _md_row(MD_MARK["finding"], f"{len(rest)} {'more ' if shown else ''}finding{'' if len(rest) == 1 else 's'} ({', '.join(sev)}"
                       + (f", {len(p['rejected_claims'])} rejected" if p["rejected_claims"] else "") + ")",
                       [f"- <a id=\"f-{f['reviewer']}-{f['id']}\"></a>{MD_SEV.get(f['severity'], '')} **{f['severity']}**"
                        + (" **rejected**" if f["status"] == "rejected" else "")
                        + f" {f['title']} ({_name(f['reviewer'])} {f['id']}): {_md_short(f['claim'], _rev_path(p, f['reviewer']), 120)}" for f in rest])
    return out or [f"{MD_MARK['pass']} No findings", ""]


def _md_checks(p: dict) -> list[str]:
    facts = p["inputs"]["facts"]["path"]
    tools = p["checked_by"]["tools"]
    ran = [t for t in tools if t["status"] in ("pass", "fail")]
    ok = [t for t in ran if t["status"] == "pass"]
    logs = (lambda t: [t["log"]] if isinstance(t.get("log"), str) else (t.get("log") or []))
    every = [f"- {MD_MARK.get(t['status'], MD_MARK['unknown'])} `{t['id']}`: {_md_short(t.get('summary'), facts, 110)}"
             + (f" ({_md_link(logs(t)[0], 'log')})" if logs(t) else "") for t in tools]
    out = _md_row(MD_MARK["pass" if len(ok) == len(ran) else "partial"], f"{len(ok)} of {len(ran)} checks pass", every + ["", _md_link(facts, "facts.json")], "every-check")
    for t in ran:
        if t["status"] == "fail":
            out += _md_row(MD_MARK["fail"], f"<b>{t['id']}</b>: {_html_inline(_check_failed(t))}",
                           [f"- {_md_short(t.get('summary'), facts, 220)}", f"- {t.get('tool') or ''} {t.get('tool_version') or ''}"
                            + (f" ({_md_link(logs(t)[0], 'log')})" if logs(t) else "")])
    sc = p.get("supply_chain")
    if sc:
        deps = sc.get("deps") or {}
        bad = sc["status"] == "fail" or deps.get("vulnerabilities_new") or sc["rules"]
        line = ("no new packages or advisories" if sc["status"] == "pass" and not bad and not deps.get("packages") and not deps.get("projects_added")
                else re.sub(r"^deps\.delta pass: ", "", sc["line"].split("; ")[0]).split(" (")[0])
        out += _md_row(MD_MARK["fail" if bad else "pass" if sc["status"] == "pass" else "unknown"], f"Supply chain: {_html_inline(line)}", _md_supply(p))
    nc, gaps = p["not_checked"], (p.get("card") or {}).get("known_gaps") or []
    if nc or gaps:
        out += _md_row(MD_MARK["unknown"], f"Not run: {len(nc)} check{'' if len(nc) == 1 else 's'}" + (f", {len(gaps)} standing gaps" if gaps else ""),
                       [f"- `{x['id']}` ({x['source']}): {_md_short(x['reason'], facts, 160)}" for x in nc]
                       + ([f"- Standing pipeline gaps: {', '.join(f'`{g}`' for g in gaps)}"] if gaps else []), "not-checked")
    return out


def _md_reviewers(p: dict) -> list[str]:
    out = []
    for r in p["panel"]["rows"]:
        if r.get("missing"):
            out += _md_row(MD_MARK["fail"], f"<b>{_name(r['reviewer'])}</b>: no review on file, every clause waits for it", [])
            continue
        vs = list(r["verdicts"].values())
        met, n = sum(v == "met" for v in vs), r["findings_verified"]
        only = ", ".join(f"[{f['id']}](#f-{r['reviewer']}-{f['id']})" for f in r["only_this_reviewer"])
        out += _md_row(MD_MARK["person"], f"<b>{_name(r['reviewer'])}</b> {_html_inline(r['model'].rsplit('/', 1)[-1])}: met {met} of {len(vs)} · "
                       f"{n} finding{'' if n == 1 else 's'}",
                       [f"- {r['model']}, {r['vendor']}, prompt {r['prompt_version']}{' (SIMULATED)' if r.get('simulated') else ''}. Citations: "
                        f"{r['citations_verified']} verified, {r['citations_rejected']} rejected. Findings: {r['findings_verified']} verified, "
                        f"{r['findings_rejected']} rejected. {r['refusals']} refusals.", *([f"- Only {_name(r['reviewer'])} raised: {only}"] if only else []),
                        f"- {_md_link(_rev_path(p, r['reviewer']), 'review file')}"])
    a = p.get("adjudication")
    if a:
        rs = _rulings(p)
        out += _md_row(MD_MARK["adjudicator"], f"<b>{_name(a['reviewer'])}</b> {_html_inline(a['model'])}: adjudicator, {len(rs)} ruling{'' if len(rs) == 1 else 's'}, advisory",
                       [f"- [{_ruling_line(p, x)}](#{_dispute_anchor(p, str(x.get('dispute')))})" for x in rs]
                       + [f"- Advisory: adds reasons, never clears. {_md_link(_adj_path(p), 'rulings file')}"])
    elif p.get("disputes"):
        out += _md_row(MD_MARK["unknown"], f"{len(p['disputes'])} disputed item(s) not adjudicated: {_html_inline(', '.join(x['id'] for x in p['disputes']))}", [])
    return out


def _md_refusals(p: dict) -> list[str]:
    c = p["card"]
    k = len(c["refused"]) + len(c["refused_clauses"])
    per = c.get("refused_peripheral") or []
    if not (k or per):
        return _md_row(MD_MARK["pass"], "No open questions: every clause proven, no topic refused", [], "refused")
    body = [f"- <a id=\"{g['anchor']}\"></a>**{_md_short(g['topic'], None, 120)}** *Who:* {'; '.join(g['who_should_decide'])} "
            f"(raised by {', '.join(_name(n) for n in g['raised_by'])}). {_md_short(g['why'], _rev_path(p, g['raised_by'][0]), 120)}" for g in c["refused"]]
    if c["refused_clauses"]:
        body.append(f"- Whether {', '.join(f'[{_short_id(x)}](#chain-{x})' for x in c['refused_clauses'])} "
                    f"{'is' if len(c['refused_clauses']) == 1 else 'are'} met. *Who:* {p['owner']}")
    if per:
        body += ["", f"<a id=\"refused-peripheral\"></a>{_peripheral(c)} (out of scope for this change):", ""]
        body += [f"- <a id=\"{g['anchor']}\"></a>{_md_short(g['topic'], _rev_path(p, g['raised_by'][0]), 120)} (who: {'; '.join(g['who_should_decide'])})" for g in per]
    return _md_row(MD_MARK["unknown"], f"Open questions: {k} for a human" + (f" (+{len(per)} out of scope)" if per else ""), body, "refused")


def _md_why(p: dict) -> list[str]:
    c, n = p["card"], len(p["card"]["reasons"])
    body = [f"{i}. {_split(x['text'], 110, REASON_SEPS)[0]} ([see]({x['link']}))" for i, x in enumerate(c["reasons"], 1)]
    if c["more_drivers"]:
        body += ["", f"All {c['more_drivers']} tier drivers and the risk factors are under Full detail."]
    return _md_row(MD_MARK["person"] if p["tier"] in ("ask", "block") else MD_MARK["pass"],
                   f"<b>Why {p['tier']}</b>: {n} reason{'' if n == 1 else 's'}, risk score {p['risk']['score']}", body, "risk")


def _md_residual(p: dict) -> list[str]:
    items = p["card"]["residual"] + (p["card"].get("residual_more") or [])
    return _md_row(MD_MARK["warn"], f"You accept {len(items)} residual risk{'' if len(items) == 1 else 's'} by signing",
                   [f"- {x['text']} ([see]({x['link']}))" for x in items]) if items else []


def _md_compact(p: dict) -> list[str]:
    """The Evidence fold's first level: about 1,500 characters with every row closed."""
    rulings = {str(r.get("dispute")): r for r in _rulings(p)}
    return (_md_why(p) + ["**Requirements**", ""] + [x for t in p["trust"] for x in _md_clause(p, t, rulings)]
            + ["**Findings**", ""] + _md_findings(p, rulings) + ["**Checks**", ""] + _md_checks(p)
            + ["**Reviewers**", ""] + _md_reviewers(p) + _md_refusals(p) + ["**Sign**", ""] + _md_residual(p) + _md_sign(p["card"]["sign"]))


MD_LIMIT = 60000  # GitHub comments stop at 65536 characters


def _md_story(p: dict, so: dict | None) -> list[str]:
    """The short card: verdict, the change, one reason, three marks."""
    marks = [f"- {g} {w}" for _c, g, w in _marks(p, so)]
    return [f"## Countersign: **{p['tier'].upper()}**, owner **{p['owner']}**" + (" (SIMULATED inputs)" if _sim(p) else ""), "",
            f"**{_change_line(p)}**", "", f"**Why:** {_why(p)}", "", *marks, ""]


def md_story(p: dict, ledger: list[dict] | None = None) -> list[str]:
    """The short card alone. `ledger`: the entries whose sign-off the card reports (default: the workspace ledger), so a
    caller with its own ledger (the PR check reads the repo's ledger branch) gets a card that agrees with its status."""
    return _md_story(view(p), _signoff(p, ledger))


def to_markdown(p: dict, ledger: list[dict] | None = None, story: bool = True) -> str:
    """The short card in plain GitHub Markdown, everything else in one <details>. Shrinks to stay under a PR comment's limit.
    `ledger` as in md_story; story=False leaves the card out (the PR comment puts it first itself)."""
    head = md_story(p, ledger) if story else []
    p = view(p)
    fold = ["<details><summary><b>Evidence</b>: requirements, findings, checks, reviewers, how to sign</summary>", ""]
    card = _md_compact(p)
    for parts in ((_md_full(p), _md_evidence(p)), (_md_full(p), _md_evidence(p, excerpts=False)), (_md_full(p),), ()):
        text = "\n".join(head + fold + card + [x for part in parts for x in part] + ["</details>", ""])
        if len(text) <= MD_LIMIT:
            return text
    return ("\n".join(head + fold + card)[:MD_LIMIT - 20]) + "\n\n</details>\n"


# --- HTML (self-contained, no JS, phone first, light and dark) ------------------------------

CSS = """
:root{color-scheme:light;--fg:#1f2328;--mut:#59636e;--bg:#fff;--sf:#f6f8fa;--sf2:#eff2f5;--line:#d1d9e0;--link:#0969da;--focus:#0969da;
--ok:#1a7f37;--okb:#dafbe1;--warn:#9a6700;--warnb:#fff8c5;--bad:#d1242f;--badb:#ffebe9;--held:#59636e;--heldb:#eff2f5;--mark:#fff8c5;
--t-silent:#1a7f37;--t-notify:#1a7f37;--t-ask:#9a6700;--t-block:#d1242f;--t-silentb:#dafbe1;--t-notifyb:#dafbe1;--t-askb:#fff8c5;--t-blockb:#ffebe9;
--sans:-apple-system,BlinkMacSystemFont,"Segoe UI","Noto Sans",Helvetica,Arial,sans-serif;--mono:ui-monospace,SFMono-Regular,"SF Mono",Menlo,Consolas,"Liberation Mono",monospace}
@media (prefers-color-scheme:dark){:root{color-scheme:dark;--fg:#f0f6fc;--mut:#9198a1;--bg:#0d1117;--sf:#151b23;--sf2:#212830;--line:#3d444d;--link:#4493f8;--focus:#4493f8;
--ok:#3fb950;--okb:#12261e;--warn:#d29922;--warnb:#272115;--bad:#f85149;--badb:#25171c;--held:#9198a1;--heldb:#212830;--mark:#3b2e0a;
--t-silent:#3fb950;--t-notify:#3fb950;--t-ask:#d29922;--t-block:#f85149;--t-silentb:#12261e;--t-notifyb:#12261e;--t-askb:#272115;--t-blockb:#25171c}}
*{box-sizing:border-box}html{-webkit-text-size-adjust:100%}
body{margin:0;overflow-wrap:anywhere;font:15px/1.5 var(--sans);color:var(--fg);background:var(--bg);font-variant-numeric:tabular-nums}
main{max-width:880px;margin:0 auto;padding:8px 16px 48px}
a{color:var(--link);text-underline-offset:2px}a:focus-visible,summary:focus-visible{outline:2px solid var(--focus);outline-offset:2px;border-radius:3px}
h1{font-size:20px;line-height:1.25;font-weight:600;margin:8px 0 4px}
h3{font-size:12px;letter-spacing:.04em;text-transform:uppercase;font-weight:600;color:var(--mut);margin:24px 0 2px}h4{font-size:16px;font-weight:600;margin:0 0 4px}
p{margin:4px 0 8px}ul,ol{margin:4px 0;padding-left:24px}li{margin:4px 0}.mut{color:var(--mut)}.sm{font-size:14px}
code,pre,.mono{font-family:var(--mono);font-size:.875em}code{overflow-wrap:anywhere;background:var(--sf);border:1px solid var(--line);border-radius:4px;padding:0 4px}
pre code{background:none;border:0;padding:0}
.banner{background:var(--badb);color:var(--bad);border:1px solid var(--bad);padding:8px 12px;border-radius:6px;font-weight:600}
.tier{display:inline-block;border:1px solid currentColor;border-radius:999px;padding:2px 12px;font:600 14px/20px var(--mono);letter-spacing:.02em;text-transform:uppercase}
.tier.sm{font-size:12px;line-height:18px;padding:0 8px}
.t-silent{color:var(--t-silent);background:var(--t-silentb)}.t-notify{color:var(--t-notify);background:var(--t-notifyb)}.t-ask{color:var(--t-ask);background:var(--t-askb)}.t-block{color:var(--t-block);background:var(--t-blockb)}
.chips{display:flex;flex-wrap:wrap;gap:4px;margin:4px 0}
.chip{font-family:var(--mono);font-size:12px;border:1px solid var(--line);background:var(--sf);border-radius:6px;padding:0 6px;text-decoration:none;overflow-wrap:anywhere}
.chip.bad{border-style:dashed;color:var(--mut)}
.sign{border:1px solid var(--line);border-left:3px solid var(--t-ask);background:var(--sf);border-radius:6px;padding:8px 12px;margin-top:8px}
.sign q{font-style:italic;quotes:none}.sign p{margin:0 0 4px}
pre{background:var(--sf);border:1px solid var(--line);padding:8px 12px;border-radius:6px;overflow-x:auto;margin:8px 0}
pre.code{padding:8px 0}pre.code span{display:block;padding:0 12px 0 0;white-space:pre}
pre.code span i{display:inline-block;min-width:4.2em;padding:0 .8em 0 .5em;text-align:right;color:var(--mut);font-style:normal;user-select:none}
pre.code span.hl{background:var(--mark);box-shadow:inset 3px 0 0 var(--t-ask)}pre.code span.hl i{color:var(--fg);font-weight:600}
.callout{border:1px solid var(--line);border-left:3px solid var(--t-ask);background:var(--sf);border-radius:6px;padding:8px 12px;margin:8px 0}
blockquote{margin:4px 0;padding:2px 12px;border-left:3px solid var(--line);color:var(--mut)}
.scroll{overflow-x:auto;border:1px solid var(--line);border-radius:6px;margin:8px 0}table{border-collapse:collapse;width:100%;font-size:14px}
th,td{text-align:left;padding:6px 10px;border-bottom:1px solid var(--line);vertical-align:top}tr:last-child td{border-bottom:0}
th{font-size:12px;font-weight:600;text-transform:uppercase;letter-spacing:.03em;color:var(--mut);background:var(--sf)}th,td{overflow-wrap:break-word}td.n{text-align:right}
.v-met{color:var(--ok);font-weight:600}.v-not_met{color:var(--bad);font-weight:600}.v-cannot_determine,.v-none{color:var(--warn);font-weight:600}
.sev-blocker,.sev-major{color:var(--bad);font-weight:600}.sev-minor{color:var(--warn);font-weight:600}.sev-info{color:var(--mut);font-weight:600}
details>summary{cursor:pointer}details.mini>summary{color:var(--link);font-size:14px}
details.fold{margin-top:24px;border-top:1px solid var(--line);padding-top:8px}details.fold>summary{font-weight:600;padding:8px 0}
.rows{border-top:1px solid var(--line)}
.row{border-bottom:1px solid var(--line)}
.row>summary,div.row{display:flex;gap:8px;align-items:flex-start;padding:7px 2px;list-style:none}
.row>summary::-webkit-details-marker{display:none}.row>summary:hover{background:var(--sf)}
.row .i{margin-top:.2em;font-size:1.1em}.row .rt{flex:1;min-width:0}.row .tag .i{margin:0;font-size:1em}
.row .loc{font:12px/1.9 var(--mono);white-space:nowrap;text-decoration:none}.row .loc:hover{text-decoration:underline}
.chev{color:var(--mut)}div.row .chev{width:1.1em;flex:none}details[open]>summary>.chev{transform:rotate(180deg)}
.rd{padding:0 8px 10px 30px;font-size:14px}.rd p{margin:2px 0 6px}.rd ol{margin:2px 0 6px}.rd .i{margin:0}
.rd.sub{padding:0 0 0 22px}.rd.sub .row:last-child{border-bottom:0}
.c-ok{color:var(--ok)}.c-bad{color:var(--bad)}.c-warn{color:var(--warn)}.c-mut{color:var(--mut)}
.c-t-silent{color:var(--t-silent)}.c-t-notify{color:var(--t-notify)}.c-t-ask{color:var(--t-ask)}.c-t-block{color:var(--t-block)}
.ev{display:none}.ev:target{display:block;border:1px solid var(--line);border-radius:6px;padding:12px 16px;margin:16px 0}
:target{scroll-margin-top:8px}.row:target{outline:2px solid var(--focus);outline-offset:2px;border-radius:4px}
.ok{color:var(--ok);font-weight:600}.no{color:var(--bad);font-weight:600}
.sr{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0);white-space:nowrap}
.story{min-height:calc(100vh - 160px);min-height:calc(100svh - 160px);display:flex;flex-direction:column;justify-content:center;align-items:center;text-align:center;gap:16px;padding:24px 0}
.story .brand{font:600 14px/1.4 var(--sans);margin:0}.story .brand .mut{font-weight:400}.story h1{font-size:clamp(22px,4.4vw,32px);line-height:1.2;max-width:28ch;margin:0;text-wrap:balance}
.pill{display:inline-flex;gap:8px;align-items:center;border:2px solid currentColor;border-radius:999px;padding:6px 20px;font:600 20px/1.3 var(--sans);margin:0}
.pill b{font-family:var(--mono);letter-spacing:.04em}
.why{font-size:clamp(18px,3.6vw,22px);margin:0;max-width:32ch}
ul.marks{list-style:none;padding:0;margin:8px 0 0;display:grid;gap:10px;font-size:clamp(18px,3.6vw,22px);text-align:left}
ul.marks li{display:flex;gap:12px;align-items:center;margin:0}ul.marks .g{font-size:1.25em}
.m-ok .g{color:var(--ok)}.m-bad .g{color:var(--bad)}.m-warn .g{color:var(--warn)}
details#evidence{margin-top:0}details#evidence>summary{font-size:20px;text-align:center;color:var(--link);list-style:none;padding:16px 0}
details#evidence>summary::-webkit-details-marker{display:none}details#evidence>summary .chev{color:var(--link);vertical-align:-.25em;font-size:1.2em}
details.more-all{margin-top:32px}details.more-all>summary{font-size:14px;color:var(--link)}
@media (min-width:720px){body{font-size:16px}main{padding:24px 32px 64px}h1{font-size:24px}}
@media print{details{display:block}details>*{display:block}.ev{display:block}}
"""


def _e(x) -> str:
    return html.escape("" if x is None else str(x))


def _tier(t: str, sm: bool = False) -> str:
    return f'<span class="tier{" sm" if sm else ""} t-{_e(t)}">{_e(t)}</span>'


ICON_OF = {"proven": "pass", "held before": "partial", "refused": "unknown", "not met": "fail"}  # icons.STATUS meanings


def _chip(ref: str, label: str, ok: bool = True) -> str:
    return f'<a class="chip{"" if ok else " bad"}" href="#{_e(ref)}">{_e(label)}{"" if ok else " (not verified)"}</a>'


def _table(headers: list[str], rows: list[list[str]], numeric: frozenset = frozenset(), caption: str = "") -> str:
    head = "".join(f'<th scope="col">{_e(h)}</th>' for h in headers)
    body = "".join("<tr>" + "".join(f'<td{" class=n" if i in numeric else ""}>{c}</td>' for i, c in enumerate(r)) + "</tr>" for r in rows)
    cap = f'<caption class="sr">{_e(caption)}</caption>' if caption else ""
    return f'<div class="scroll"><table>{cap}<thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>'


def _html_sign(sg: dict) -> str:
    """The sign-off in one command line; the per-finding flags and the signed statement one tap away."""
    n = len(sg.get("findings") or [])
    rate = ""
    if n:
        rows = "".join(f'<li><code>{_e(r["ref"])}</code> <span class="mut">({_e(r["severity"])})</span> {_e(r["title"])}</li>' for r in sg["findings"])
        rate = (f'<details class="mini" id="sign-findings"><summary>and rate the {n} verified finding{"" if n == 1 else "s"} (full command)</summary>'
                f'<p class="sm">One <code>--finding</code> flag each: <code>accepted</code> (real), <code>rejected</code> (a false positive) or '
                f'<code>unsure</code>, optionally <code>:reason</code>. A finding without a flag is recorded as <code>unrated</code>.</p>'
                f'<ul class="sm">{rows}</ul><pre>{_e(sg.get("command_with_findings", sg["command"]))}</pre></details>')
    return (f'<div class="sign"><p><b>{_e(sg["owner"])} signs</b> <span class="mut sm">({"required" if sg["required"] else "not required: spot-checks apply"}; '
            f'{_e(", ".join(sg["decisions"]))})</span></p>'
            f'<pre class="cmd" aria-label="sign command">{" ".join(f"<span>{_e(w)}</span>" for w in _short_command(sg).split(" "))}</pre>{rate}'
            f'<details class="mini"><summary>What your signature says</summary><p><q>{_e(sg["statement"])}</q></p>'
            f'<p class="mut sm">It covers the sha256 of this pack\'s canonical JSON, the decision, your verdict on each finding, the time and the signer, '
            f'and is appended to the hash-chained ledger.</p></details></div>')


def _ev_chips(refs: list[str], ev: dict) -> str:
    return "".join(_chip(r, ev[r]["label"], ev[r]["verified"]) for r in refs if r in ev)


def _html_ev(e: dict) -> str:
    mark = '<span class="ok">verified</span>' if e["verified"] else '<span class="no">not verified</span>'
    head = (f'<h4 class="mono">{_e(e["label"])}</h4><p class="sm">{mark} &middot; <span class="mut">{_e(e["note"])}</span></p>'
            f'<p class="sm mut">Cited by {_e(", ".join(e["cited_by"]))}</p>')
    body = ""
    if e["kind"] == "code":
        ex = e.get("excerpt")
        if ex:
            ind = min((len(x) - len(x.lstrip()) for x in ex["lines"] if x.strip()), default=0)  # display-only dedent for phones
            lines = "".join(f'<span{" class=hl" if n == ex["highlight"] else ""}><i>{n}</i>{_e(line[ind:])}</span>' for n, line in enumerate(ex["lines"], ex["start"]))
            body = (f'<p class="sm mono">{_e(e["file"])} @ {_e(e.get("rev", "head"))} {_e(ex["sha"])}</p>'
                    f'<pre class="code" aria-label="code excerpt, cited line highlighted">{lines}</pre>')
        body += f'<p class="sm">Quoted: <code>{_e(e.get("quote"))}</code></p>'
    elif e["kind"] == "test":
        runs = "".join(f'<li><b class="{"ok" if r["outcome"] == "passed" else "no"}">{_e(r["outcome"])}</b> on {_e(r["run"])} '
                       f'<span class="mut">(<code>{_e(r["check"])}</code>{", " + _e(r["project"]) if r.get("project") else ""})</span>'
                       + "".join(f'<br><span class="mono mut">{_e(x)}</span>' for x in r["logs"][:1]) + "</li>" for r in e.get("runs", []))
        body = f'<p class="sm">Test <code>{_e(e.get("name"))}</code>, cited as {_e(e.get("outcome"))}. Runs:</p><ul class="sm">{runs}</ul>' 
        if e.get("without_fix"):
            body += (f'<p class="sm">Without the fix it <b>{_e(e["without_fix"])}</b>: '
                     + ("so it tests the change.</p>" if e["without_fix"] == "failed" else "so it shows existing behaviour, not the change.</p>"))
    elif e["kind"] == "check" and e.get("check_result"):
        cr = e["check_result"]
        body = (f'<p class="sm"><code>{_e(e.get("id"))}</code> <b class="{"ok" if cr["status"] == "pass" else "no"}">{_e(cr["status"])}</b>: {_e(cr.get("summary"))}</p>'
                f'<p class="sm mut">{_e(cr.get("tool"))} {_e(cr.get("tool_version"))}</p>'
                + "".join(f'<p class="sm mono">log: {_e(x)}</p>' for x in cr["logs"]))
    elif e["kind"] == "requirement":
        body = f'<blockquote class="sm">{_e(e.get("clause_text"))}</blockquote>'
    elif e["kind"] == "issue":
        body = f'<p class="sm mono">{_e(e.get("url"))}</p>'
    return f'<article class="ev" id="{_e(e["ref"])}">{head}{body}<p class="sm"><a href="#evidence">Back to the evidence</a></p></article>'


def _html_supply(p: dict) -> str:
    """One summary line, new advisories and the supply-chain rules that fired in plain sight, the rest folded."""
    sc = p.get("supply_chain")
    if not sc:
        return ""
    cls = {"fail": "no", "pass": "ok"}.get(sc["status"], "mut")
    deps = sc.get("deps") or {}
    top = f'<p class="{cls}">{_e(sc["line"])}</p>'
    vul = "".join(f'<li><span class="sev sev-{"major" if v["severity"] in ("high", "critical") else "minor"}">{_e(v["severity"])}</span> '
                  f'<b>New advisory</b> {_e(v["package"])} {_e(v["version"])}: <a href="{_e(v["advisory"])}">{_e(v["id"])}</a></li>'
                  for v in deps.get("vulnerabilities_new", []))
    rules = "".join(f'<li>{_tier(r["tier"], True)} <code>{_e(r["id"])}</code> {_e(r["evidence"])}</li>' for r in sc["rules"])
    if vul or rules:
        top += f'<ul class="sm">{vul}{rules}</ul>'
    body = ""
    if deps:
        body += f'<p class="sm"><code>deps.delta</code> <b class="{"ok" if deps["status"] == "pass" else "no"}">{_e(deps["status"])}</b>: {_e(deps["summary"])}</p>'
        if deps["packages"]:
            body += _table(["Package", "Base", "Head", "Direct", "Via"],
                           [[_e(x["package"]), _e(x["base"] or "-"), _e(x["head"]), "direct" if x["direct"] else "transitive",
                             f'<span class="mono sm">{_e(x["via"])}</span>'] for x in deps["packages"]], caption="Packages added or moved")
        items = [f"New project <code>{_e(x)}</code>" for x in deps["projects_added"]]
        items += [f"New project reference <code>{_e(x['project'])}</code> &rarr; <code>{_e(x['references'])}</code>" for x in deps["project_references_added"]]
        items += [f"Build inputs changed: {_e(k)}: {_e(v.get('base'))} &rarr; {_e(v.get('head'))}" for k, v in deps["build_inputs_changed"].items()]
        if (deps.get("sbom") or {}).get("head"):
            items.append(f'SBOMs (CycloneDX): <span class="mono">{_e(deps["sbom"]["base"])}</span>, <span class="mono">{_e(deps["sbom"]["head"])}</span>')
        body += f'<ul class="sm">{"".join(f"<li>{x}</li>" for x in items)}</ul>' if items else ""
        if deps["vulnerabilities_also_on_base"]:
            body += (f'<details class="mini"><summary>Already on base ({len(deps["vulnerabilities_also_on_base"])} advisories)</summary><ul class="sm">'
                     + "".join(f'<li>{_e(v["package"])} {_e(v["version"])} {_e(v["severity"])} <a href="{_e(v["advisory"])}">{_e(v["id"])}</a></li>'
                               for v in deps["vulnerabilities_also_on_base"]) + "</ul></details>")
    eg = sc.get("egress")
    if eg:
        pol = eg["policy"]
        body += (f'<p class="sm"><code>build.egress</code> <b class="{"ok" if eg["status"] == "pass" else "no"}">{_e(eg["status"])}</b>: '
                 f'default {_e(pol.get("default"))}, presets {_e(pol.get("presets"))}, TLS hosts {_e(", ".join(pol.get("tls_server_name_patterns") or []))}'
                 + (f'; <a href="{_e(eg["run"])}">provenance run</a>' if eg.get("run") else "")
                 + (f'; <span class="no">blocked: {_e(", ".join(eg["blocked_hosts"]))}</span>' if eg["blocked_hosts"] else "")
                 + (f' <span class="mono mut">policy {_e(eg["policy_sha256"][:12])}</span>' if eg.get("policy_sha256") else "") + "</p>")
    net = sc.get("craci_network")
    if net:
        body += (f'<p class="sm"><code>craci.network</code> <b class="{"ok" if net["status"] == "pass" else "no" if net["status"] == "fail" else "mut"}">'
                 f'{_e(net["status"])}</b>: {_e(net["summary"])}</p>'
                 + "".join(f'<p class="sm no">proxy violation: {_e(v.get("host"))} ({_e(v.get("reason"))})</p>' for v in net["proxy_violations"]))
    return top + (f'<details class="mini"><summary>Supply-chain detail</summary>{body}</details>' if body else "")


# --- the Evidence fold: one compact row per clause, finding, check and reviewer; detail one tap deeper -----------
# Visible with every row closed: a status icon, a short name, a one-line verdict and the cited file:line. A row opens
# to a few short lines; long texts are cut to their first sentence with a link to the source file in the repo.

BLOB = "https://github.com/Zawaer/countersign/blob/main/"  # same as site/build.py's src()
TONE = {"proven": "ok", "held before": "warn", "refused": "warn", "not met": "bad"}
SEV_TONE = {"blocker": "bad", "major": "bad", "minor": "warn", "info": "mut"}


def _ic(name: str, tone: str = "", label: str | None = None) -> str:
    return icon(name, f"c-{tone}" if tone else "", label)


def _src(rel: str | None, label: str) -> str:
    return f'<a class="src" href="{BLOB}{_e(rel)}">{_e(label)}</a>' if rel else ""


def _first(text, limit: int = 140) -> tuple[str, bool]:
    """(the first sentence, or the text cut at a word near `limit`; whether anything was cut)."""
    t = " ".join(str(text or "").split())
    depth = 0
    for i, ch in enumerate(t):
        depth += (ch in "([") - (ch in ")]")
        if (ch == "." and depth == 0 and i >= 20 and (i + 1 == len(t) or t[i + 1] == " ")
                and t[max(0, i - 3):i] not in ("e.g", "i.e") and not t[i - 1].isdigit()):
            if i + 1 <= limit:
                return t[:i + 1], i + 1 < len(t)
            break
    if len(t) <= limit:
        return t, False
    cut = t.rfind(" ", 0, limit)
    return t[:cut if cut > 20 else limit].rstrip(",;: ") + "…", True


def _short(text, rel: str | None = None, limit: int = 140) -> str:
    """The first sentence, escaped, with a `full text` link to the source file when the rest was cut."""
    head, cut = _first(text, limit)
    return _e(head) + (" " + _src(rel, "full text") if cut and rel else "")


def _row(ic: str, body: str, loc: str = "", detail: str = "", rid: str = "", cls: str = "") -> str:
    """One line: icon, text, cited location. With a detail it is a fold (closed)."""
    rid = f' id="{_e(rid)}"' if rid else ""
    line = f'{ic}<span class="rt">{body}</span>{loc}'
    if not detail:
        return f'<div class="row{cls}"{rid}>{line}<span class="chev"></span></div>'
    return f'<details class="row{cls}"{rid}><summary>{line}{icon("expand_more", "chev")}</summary><div class="rd">{detail}</div></details>'


def _loc(refs: list, ev: dict) -> str:
    """The cited line as file:line (a verified code citation first), linking to its excerpt."""
    es = [ev[r] for r in refs if r in ev and ev[r]["kind"] == "code"]
    e = next((x for x in es if x["verified"]), None) or next(iter(es), None)
    return f'<a class="loc" href="#{_e(e["ref"])}">{_e(e["label"].removesuffix(" @head"))}</a>' if e else ""


def _pack_path(p: dict) -> str:
    return f"packs/{p['change']}/pack.json"


def _finding_of(p: dict, dispute: str) -> dict | None:
    """The finding a `finding:<reviewer>:<id>[-suffix]` dispute is about."""
    who, _, fid = dispute.split(":", 1)[1].partition(":")
    return next((f for f in p["findings"] if f["reviewer"] == who and (fid == f["id"] or fid.startswith(f["id"] + "-"))), None)


def _dispute_anchor(p: dict, dispute: str) -> str:
    if not dispute.startswith("finding:"):
        return f"chain-{dispute}"
    f = _finding_of(p, dispute)
    return f'f-{f["reviewer"]}-{f["id"]}' if f else "findings"


def _rev_path(p: dict, n: str) -> str | None:
    return ((p.get("inputs") or {}).get("reviews") or {}).get(n, {}).get("path")


def _adj_path(p: dict) -> str | None:
    return ((p.get("inputs") or {}).get("adjudication") or {}).get("path")


def _ruling_detail(p: dict, r: dict) -> str:
    """A ruling in three short lines: what it says, whose claims it backs, what would settle it."""
    def who(xs: list) -> str:
        n: dict = {}
        for x in xs:
            n[_name(x.get("reviewer", "?"))] = n.get(_name(x.get("reviewer", "?")), 0) + 1
        return ", ".join(f"{k} ({v})" for k, v in n.items()) or "none"
    settle = r.get("evidence_that_would_settle") or []
    return (f'<p>{_ic("gavel", "mut")} <b>{_e(_ruling_line(p, r))}</b> <span class="mut">(advisory)</span></p>'
            + (f'<p>{_short(r["note"])}</p>' if r.get("note") else "")
            + f'<p class="mut">Claims backed: {_e(who(r.get("supported", [])))}; not backed: {_e(who(r.get("unsupported", [])))}. '
            + (f'Would settle it: {_short(settle[0], None, 120)}' if settle else "") + f' {_src(_adj_path(p), "full ruling")}</p>')


def _clause_verdict(p: dict, t: dict, ruling: dict | None) -> str:
    """`Not met: Claude; met: Codex, Nemotron; Gemini sided with Claude`, or the status in a few words."""
    n = len(t["reviewers"])
    if t["status"] == "proven":
        return f"Proven: all {n} reviewers say met, checks pass"
    if t["status"] == "held_before":
        return "Held before: its tests pass without the fix too"
    by: dict = {}
    for r in t["reviewers"]:
        by.setdefault(r["verdict"], []).append(_name(r["reviewer"]) + (" (unverified)" if r["verdict"] == "met" and not r["verified"] else ""))
    by.update({None: [_name(x) for x in t["missing"]]} if t["missing"] else {})
    if set(by) == {"met"}:  # refused although all say met: thin evidence, mutation, ...
        head = _trace_why(p, t)[0]
        named = head.split(" ", 1)[0] in {_name(r["reviewer"]) for r in t["reviewers"]}
        return "Refused: " + (head if named else head[:1].lower() + head[1:])
    s = "; ".join(f"{VERDICT_SHORT.get(v, v)}: {', '.join(by[v])}" for v in ("not_met", "cannot_determine", "met", None) if v in by)
    s = s[:1].upper() + s[1:]
    if ruling:
        adj = _name(p["adjudication"]["reviewer"])
        no = [r["reviewer"] for r in t["reviewers"] if r["verdict"] != "met"]
        backed = [x for x in no if any(y.get("reviewer") == x for y in ruling.get("supported", []))]
        s += (f"; {adj} sided with {' and '.join(_name(x) for x in backed)}" if backed
              else f"; {adj} did not back {' and '.join(_name(x) for x in no)}" if no else f"; {adj} ruled (advisory)")
    return s


def _html_clause(p: dict, t: dict, rulings: dict) -> str:
    ev, ru = p["evidence_index"], rulings.get(t["id"])
    no = [r for r in t["reviewers"] if r["verdict"] != "met"]
    loc = _loc([x for r in (no or t["reviewers"]) for x in r["refs"]], ev)
    d = f'<blockquote>{_short(t["text"], p["inputs"]["requirements"]["path"], 220)}</blockquote>'
    if t["status"] == "held_before" or not no:  # a dissent is already said by the row and the reviewer lines below
        d += f'<p>{_short(t["why"], _pack_path(p), 160)}</p>' if t["status"] != "proven" else ""
    if t["status"] in ("proven", "held_before"):
        d += "<p>" + ", ".join(f'<b>{_e(_name(r["reviewer"]))}</b> met ({r["verified"]} of {r["cited"]} cited verified)' for r in t["reviewers"]) + "</p>"
    else:
        d += "".join(f'<p><b>{_e(_name(r["reviewer"]))}</b> <span class="v-{_e(r["verdict"])}">{_e(VERDICT_SHORT.get(r["verdict"], r["verdict"]))}</span> '
                     f'<span class="mut">({r["verified"]} of {r["cited"]} cited verified)</span>: {_short(r["basis"], _rev_path(p, r["reviewer"]))}</p>'
                     for r in t["reviewers"])
        d += "".join(f'<p><b>{_e(_name(x))}</b> <span class="v-none">no review</span></p>' for x in t["missing"])
    fails = ", ".join(_chip(x["ref"], x["name"].rsplit(".", 1)[-1]) if x["ref"] else _e(x["name"].rsplit(".", 1)[-1]) for x in t["tests_fail_without_fix"])
    passes = ", ".join(_chip(x["ref"], x["name"].rsplit(".", 1)[-1]) for x in t["tests_pass_without_fix"])
    checks = ", ".join(f'{_e(x["id"])} <span class="{"ok" if x["status"] == "pass" else "no"}">{_e(x["status"])}</span>' for x in t["checks"])
    d += (f'<p>Checks: {checks or "none mandated"}</p>' + (f'<p>Fail without the fix: {fails}</p>' if fails else "")
          + (f'<p>Pass without the fix: {passes}</p>' if passes else ""))
    if ru:
        d += _ruling_detail(p, ru)
    elif t.get("settle"):
        d += f'<p class="mut">Would settle it: {_short(t["settle"][0], _pack_path(p), 120)}</p>'
    return _row(_ic(ICON_OF.get(t["label"], "unknown"), TONE.get(t["label"], "warn"), t["label"]),
                f'<b>{_e(_short_id(t["id"]))}</b> {_e(_clause_verdict(p, t, ru))}', loc, d, rid=f'chain-{t["id"]}')


def _html_finding(p: dict, f: dict, rulings: dict) -> str:
    ev, path = p["evidence_index"], _rev_path(p, f["reviewer"])
    rep = (f.get("repro") or {}).get("status") == "reproduced"
    rej = f["status"] == "rejected"
    body = (f'<b>{_e(_name(f["reviewer"]))} {_e(f["id"])}</b> <span class="sev-{_e(f["severity"])}">{_e(f["severity"])}</span>'
            + (' <span class="no">rejected</span>' if rej else "") + f': {_e(f["title"])}'
            + (f' <span class="tag">{_ic("experiment")} reproduced</span>' if rep else ""))
    d = f'<p>{_short(f["claim"], path)}</p>'
    if f.get("repro"):
        d += f'<p>{_ic("experiment", "mut")} <code>{_e(f["repro"].get("check"))}</code>: {_e(f["repro"].get("summary"))}</p>'
    if f.get("suggested_fix"):
        d += f'<p><b>Fix:</b> {_short(f["suggested_fix"], path)}</p>'
    d += (f'<p class="no">Rejected: {_short(f.get("rejection_reason"), path)}</p>' if rej
          else f'<p class="mut">Sets {_e(f["tier"])}: {_e(f.get("tier_reason", ""))}</p>')
    also = [x for x in f.get("confirmed_by") or []]
    if also:
        d += f'<p class="mut">Also raised by {_e(", ".join(_name(x) for x in also))}</p>'
    chips = "".join(_chip(e["ref"], ev.get(e["ref"], {}).get("label", e.get("kind", "?")), e["verified"]) for e in f["evidence"] if e.get("ref"))
    d += f'<div class="chips">{chips}</div>' if chips else ""
    for k, r in rulings.items():
        if k.startswith("finding:") and _finding_of(p, k) is f:
            d += _ruling_detail(p, r)
    return _row(_ic("bug_report", "mut" if rej else SEV_TONE.get(f["severity"], "mut"), f["severity"]), body,
                _loc([e.get("ref") for e in f["evidence"]], ev), d, rid=f'f-{f["reviewer"]}-{f["id"]}')


def _keep(f: dict) -> bool:
    """Findings shown on the first level: blocker and major ones, and any the pipeline reproduced."""
    return f["severity"] in ("blocker", "major") or (f.get("repro") or {}).get("status") == "reproduced"


def _log(t: dict) -> str:
    logs = [t["log"]] if isinstance(t.get("log"), str) else (t.get("log") or [])
    return f'<a class="loc" href="{BLOB}{_e(logs[0])}">log{"s" if len(logs) > 1 or logs[0].endswith("/") else ""}</a>' if logs else ""


def _html_checks(p: dict) -> str:
    facts = p["inputs"]["facts"]["path"]
    tools = p["checked_by"]["tools"]
    ran = [t for t in tools if t["status"] in ("pass", "fail")]
    ok = [t for t in ran if t["status"] == "pass"]
    every = "".join(f'<p>{_ic("pass" if t["status"] == "pass" else "fail" if t["status"] == "fail" else "unknown", {"pass": "ok", "fail": "bad"}.get(t["status"], "mut"))} '
                    f'<code>{_e(t["id"])}</code> {_short(t.get("summary"), facts, 110)} <span class="mut">{_e(t.get("tool") or "")} {_e(t.get("tool_version") or "")}</span> {_log(t)}</p>'
                    for t in tools)
    out = _row(_ic("pass" if len(ok) == len(ran) else "partial", "ok" if len(ok) == len(ran) else "warn"),
               f"{len(ok)} of {len(ran)} checks pass", "", every + f'<p>{_src(facts, "facts.json")}</p>', rid="every-check")
    for t in ran:
        if t["status"] == "fail":
            out += _row(_ic("fail", "bad", "fails"), f'<b>{_e(t["id"])}</b>: {_e(_check_failed(t))}', _log(t),
                        f'<p>{_short(t.get("summary"), facts, 220)}</p><p class="mut">{_e(t.get("tool") or "")} {_e(t.get("tool_version") or "")}</p>')
    sc = p.get("supply_chain")
    if sc:
        deps = sc.get("deps") or {}
        bad = sc["status"] == "fail" or deps.get("vulnerabilities_new") or sc["rules"]
        line = ("no new packages or advisories" if sc["status"] == "pass" and not bad and not deps.get("packages") and not deps.get("projects_added")
                else re.sub(r"^deps\.delta pass: ", "", sc["line"].split("; ")[0]).split(" (")[0])
        out += _row(_ic("fail" if bad else "pass" if sc["status"] == "pass" else "unknown", "bad" if bad else "ok" if sc["status"] == "pass" else "mut"),
                    f"Supply chain: {_e(line)}", "", _html_supply(p), rid="supply-chain")
    nc, gaps = p["not_checked"], (p.get("card") or {}).get("known_gaps") or []
    if nc or gaps:
        d = "".join(f'<p><code>{_e(x["id"])}</code> <span class="mut">({_e(x["source"])})</span>: {_short(x["reason"], facts, 160)}</p>' for x in nc)
        d += f'<p class="mut">Standing pipeline gaps: {_e(", ".join(gaps))}</p>' if gaps else ""
        out += _row(_ic("unknown", "mut"), f"Not run: {len(nc)} check{'' if len(nc) == 1 else 's'}" + (f", {len(gaps)} standing gaps" if gaps else ""),
                    "", d, rid="not-checked")
    return out


def _html_reviewers(p: dict, rulings: dict) -> str:
    out = ""
    for r in p["panel"]["rows"]:
        if r.get("missing"):
            out += _row(_ic("fail", "bad"), f'<b>{_e(_name(r["reviewer"]))}</b>: no review on file, every clause waits for it')
            continue
        vs = list(r["verdicts"].values())
        met = sum(v == "met" for v in vs)
        only = ", ".join(f'<a href="#f-{_e(r["reviewer"])}-{_e(f["id"])}">{_e(f["id"])}</a>' for f in r["only_this_reviewer"])
        d = (f'<p>{_e(r["model"])}, {_e(r["vendor"])}, prompt {_e(r["prompt_version"])}{" (SIMULATED)" if r.get("simulated") else ""}. '
             f'Citations: {r["citations_verified"]} verified, {r["citations_rejected"]} rejected. Findings: {r["findings_verified"]} verified, '
             f'{r["findings_rejected"]} rejected. {r["refusals"]} refusals.</p>'
             + (f'<p>Only {_e(_name(r["reviewer"]))} raised: {only}</p>' if only else "") + f'<p>{_src(_rev_path(p, r["reviewer"]), "review file")}</p>')
        n = r["findings_verified"]
        out += _row(_ic("person", "ok" if met == len(vs) else "warn"),
                    f'<b>{_e(_name(r["reviewer"]))}</b> <span class="mut">{_e(r["model"].rsplit("/", 1)[-1])}</span> met {met} of {len(vs)} '
                    f'&middot; {n} finding{"" if n == 1 else "s"}', "", d)
    a = p.get("adjudication")
    if a:
        rs = _rulings(p)
        links = "".join(f'<p><a href="#{_e(_dispute_anchor(p, str(x.get("dispute"))))}">'
                        f'{_e(_ruling_line(p, x))}</a></p>' for x in rs)
        out += _row(_ic("gavel", "mut"), f'<b>{_e(_name(a["reviewer"]))}</b> <span class="mut">{_e(a["model"])}</span> adjudicator: '
                    f'{len(rs)} ruling{"" if len(rs) == 1 else "s"}, advisory',
                    "", links + f'<p class="mut">Advisory: adds reasons, never clears. {_src(_adj_path(p), "rulings file")}</p>')
    elif p.get("disputes"):
        out += _row(_ic("unknown", "mut"), f'{len(p["disputes"])} disputed item(s) not adjudicated')
    return out


def _html_refusals(p: dict) -> str:
    c = p["card"]
    k = len(c["refused"]) + len(c["refused_clauses"])
    per = c.get("refused_peripheral") or []
    if not (k or per):
        return _row(_ic("pass", "ok"), "No open questions: every clause proven, no topic refused", rid="refused")
    d = "".join(f'<p id="{_e(g["anchor"])}"><b>{_short(g["topic"], None, 120)}</b> <span class="mut">Who: {_e("; ".join(g["who_should_decide"]))}; '
                f'raised by {_e(", ".join(_name(n) for n in g["raised_by"]))}.</span> {_short(g["why"], _rev_path(p, g["raised_by"][0]), 120)}</p>' for g in c["refused"])
    if c["refused_clauses"]:
        d += (f'<p><b>Whether {", ".join(f"<a href=#chain-{_e(x)}>{_e(_short_id(x))}</a>" for x in c["refused_clauses"])} '
              f'{"is" if len(c["refused_clauses"]) == 1 else "are"} met</b> <span class="mut">Who: {_e(p["owner"])}</span></p>')
    if per:
        d += ('<p class="mut" id="refused-peripheral">Out of scope for this change:</p>'
              + "".join(f'<p class="mut" id="{_e(g["anchor"])}">{_short(g["topic"], _rev_path(p, g["raised_by"][0]), 120)} '
                        f'(who: {_e("; ".join(g["who_should_decide"]))})</p>' for g in per))
    return _row(_ic("unknown", "warn" if k else "mut"), f"Open questions: {k} for a human" + (f" (+{len(per)} out of scope)" if per else ""), "", d, rid="refused")


def _html_why(p: dict) -> str:
    c, r = p["card"], p["risk"]
    lis = "".join(f'<li>{_e(_split(x["text"], 110, REASON_SEPS)[0])} <a href="{_e(x["link"])}">see</a></li>' for x in c["reasons"])
    d = (f'<ol>{lis}</ol>' + (f'<p class="mut">All {c["more_drivers"]} tier drivers and the risk factors are in <a href="#all-drivers">full detail</a>.</p>'
                              if c["more_drivers"] else ""))
    n = len(c["reasons"])
    return _row(icon(p["tier"], f"c-t-{p['tier']}"), f'<b>Why {_e(p["tier"])}</b>: {n} reason{"" if n == 1 else "s"}, risk score {_e(r["score"])}', "", d, rid="risk")


def _html_residual(p: dict) -> str:
    c = p["card"]
    items = c["residual"] + (c.get("residual_more") or [])
    if not items:
        return ""
    d = "".join(f'<p>{_e(x["text"])} <a href="{_e(x["link"])}">see</a></p>' for x in items)
    return _row(_ic("warn", "warn"), f'You accept {len(items)} residual risk{"" if len(items) == 1 else "s"} by signing', "", d)


def _html_full(p: dict) -> dict:
    from .common import now_iso  # imported here so view() stays importable without PyYAML (site/build.py)
    ms = p["mandate"]["signature"]
    rp = p["reviewer_panel"]
    driver_rows = [[_tier(w["tier"], True), _e(w["source"]), f"<code>{_e(w['id'])}</code>", _e(w["why"])] for w in p["drivers"]]
    risk_rows = [[_e(f["factor"]), _e(f["points"]), _e(f["reason"])] for f in p["risk"]["factors"]]
    risk_rows.append(["<b>total</b>", f"<b>{_e(p['risk']['score'])}</b>", f"{_tier(p['risk']['tier'], True)} (bands {_e(p['risk']['thresholds'])})"])
    rev_rows = [[_e(r["reviewer"]), _e(f"{r['model']} ({r['vendor']})"), _e(r["prompt_version"]), _e(r["reviewed_at"]),
                 str(r["verified"]), str(r["rejected"]), str(r["refusals"])] for r in p["checked_by"]["reviewers"]]
    area_rows = [[_e(a["name"]), _e(a["owner"]), _e(a["sensitivity"]), _tier(a["cap"], True), _e(a["cap_reason"]), str(len(a["files"]))] for a in p["areas"]]
    req_rows = [[f"<code>{_e(c['id'])}</code>", _e(c["status"]),
                 "<br>".join(f"{_e(n)}: {_e(v['verdict'])} ({v['verified']}/{v['cited']})" for n, v in c["verdicts"].items()) or "none",
                 "<br>".join(f"{_e(x['id'])}: {_e(x['status'])}" for x in c["checks"]) or "-",
                 "<br>".join(f"<code>{_e(r['code'])}</code> {_e(r['detail'])}" for r in c["reasons"]) or "-"] for c in p["requirements"]]
    return {
        "drivers": f'<h3 id="all-drivers">All tier drivers (tier = strictest)</h3>{_table(["Tier", "Source", "Id", "Why"], driver_rows)}',
        "risk": f'<h3 id="risk-score">Risk score {_e(p["risk"]["score"])}</h3>{_table(["Factor", "Points", "Reason"], risk_rows, frozenset({1}))}',
        "reviewers": f"""<h3>Reviewers</h3>
<p class="sm">Participating: <b>{_e(", ".join(rp["reviewers"]) or "none")}</b>; adjudicator: {_e(rp["adjudicator"] or "none")}; confidential: {_e("yes (" + rp["why"] + ")" if rp["confidential"] else "no")}.</p>
{"".join(f"<p class='sm mut'>Not used: {_e(x['name'])}: {_e(x['reason'])}</p>" for x in rp["ignored_files"])}
{_table(["Reviewer", "Model", "Prompt", "Reviewed", "Verified", "Rejected", "Refusals"], rev_rows, frozenset({4, 5, 6}))}""",
        "codes": f'<h3>Requirement trace, engine codes</h3>{_table(["Clause", "Status", "Verdicts", "Checks", "Reasons"], req_rows)}',
        "areas": f'<h3 id="areas">Areas touched</h3>{_table(["Area", "Owner", "Sensitivity", "AI cap", "Cap source", "Files"], area_rows, frozenset({5}))}',
        "residual": f'<h3>Residual risk, every item</h3><ul class="sm">{"".join(f"<li>{_e(r)}</li>" for r in p["residual_risk"])}</ul>',
        "provenance": f"""<h3>Provenance</h3>
<p class="sm">Branch <code>{_e(p["branch"])}</code> {_e(p["base"])}..{_e(p["head"])}, {_e(p["diff"]["files"])} files, +{_e(p["diff"]["insertions"])} &minus;{_e(p["diff"]["deletions"])}, author {_e(p["author"])} (agent-written: {_e(p["agent_written"])}). Commit: &ldquo;{_e(p["commit_message"])}&rdquo;.</p>
<p class="sm">Mandate {_e(p["mandate"]["id"])} v{_e(p["mandate"]["version"])} <code>{_e(p["mandate"]["sha256"][:16])}</code>:
{"signed by " + _e(ms.get("signed_by")) if ms["valid"] else "<b class=no>signature not valid: " + _e(ms["reason"]) + "</b>"}. {_e(p["checked_by"]["engine"])}.</p>
<p class="sm mut">Inputs: facts {_e(p["inputs"]["facts"]["path"])} ({_e(p["inputs"]["facts"]["sha256"][:12])}), requirements {_e(p["inputs"]["requirements"]["path"])},
reviews {_e(", ".join(f"{k} ({v['sha256'][:12]})" for k, v in p["inputs"]["reviews"].items()))}. Rendered {_e(now_iso())}.</p>""",
    }


MARK_ICON = {"\u2713": "pass", "\u2715": "fail", "!": "warn", "?": "unknown", "\u2026": "pending"}  # _marks glyph -> icons.STATUS


def _html_story(p: dict, so: dict | None) -> str:
    """The first screen: verdict pill, the change in one line, one reason, three marks. Status is icon + words."""
    marks = "".join(f'<li class="m-{c}">{icon(MARK_ICON.get(g, "unknown"), "g")}{_e(w)}</li>' for c, g, w in _marks(p, so))
    who = f" &rarr; {_e(p['owner'])} decides" if p["tier"] in ("ask", "block") else f" &middot; {_e(p['owner'])} is told"
    pill = f'{icon(p["tier"])}<b>{_e(p["tier"].upper())}</b>{who}'
    if so and so.get("current"):  # already decided: say what the ledger records, not what is still to come
        pill = f'{_e(so["signer"])} decided: {_e((so.get("decision") or "").replace("-", " "))}'
    return (f'<section class="story" id="card" aria-labelledby="card-h">'
            f'<p class="brand">Countersign <span class="mut">&middot; {_e(TAGLINE)}</span></p>'
            f'<p class="pill t-{_e(p["tier"])}">{pill}</p>'
            f'<h1 id="card-h">{_e(_change_line(p))}</h1>'
            f'<p class="why"><b>Why:</b> {_e(_why(p))}</p>'
            f'<ul class="marks" aria-label="Checks, reviewers, signature">{marks}</ul></section>')


FAVICON = ('<link rel="icon" href="../../favicon.svg" type="image/svg+xml"><link rel="icon" href="../../favicon-32.png" type="image/png" sizes="32x32">'
           '<link rel="apple-touch-icon" href="../../apple-touch-icon.png">')  # the site's icons (pages live at site/packs/<change>/)


def to_html(p: dict, ledger: list[dict] | None = None) -> str:
    so = _signoff(p, ledger)
    p = view(p)
    ev = p["evidence_index"]
    rulings = {str(r.get("dispute")): r for r in _rulings(p)}
    full = _html_full(p)
    st, pv, rp = p["story"], p["panel"], p["reviewer_panel"]
    shown = [f for f in p["findings"] if _keep(f)]
    rest = [f for f in p["findings"] if not _keep(f)] + p["rejected_claims"]
    found = "".join(_html_finding(p, f, rulings) for f in shown)
    if rest:
        sev = [s for s in SEV_ORDER if any(f["severity"] == s for f in rest)]
        found += (f'<details class="row more"><summary>{_ic("bug_report", "mut")}<span class="rt">{len(rest)} {"more " if shown else ""}'
                  f'finding{"" if len(rest) == 1 else "s"} <span class="mut">({", ".join(sev)}'
                  f'{", " + str(len(p["rejected_claims"])) + " rejected" if p["rejected_claims"] else ""})</span></span>{icon("expand_more", "chev")}</summary>'
                  f'<div class="rd sub">{"".join(_html_finding(p, f, rulings) for f in rest)}</div></details>')
    if not p["findings"] and not p["rejected_claims"]:
        found = _row(_ic("pass", "ok"), "No findings")
    mut = f'<p class="callout">Seeded mutant of {_e(p["mutation"].get("of"))}: {_e(p["mutation"].get("description"))}</p>' if p.get("mutation") else ""
    panel = ("".join(f'<p class="sm">{_e(x)}</p>' for x in pv["callouts"])
             + "".join(f'<p class="sm mut">Excluded {_e(_name(x["name"]))} ({_e(x["vendor"])}): {_e(x["reason"])}</p>' for x in rp["excluded"])
             + f'<p class="sm mut">Rule: {_e(rp["rule"])}. Unanimity, not a vote: each added reviewer can only make the AI more cautious.</p>')
    body = f"""
<main>
{'<p class="banner">Simulated inputs: fixture data, not a real run</p>' if _sim(p) else ""}
{mut}
{_html_story(p, so)}
<details class="fold" id="evidence"><summary>Evidence {icon("expand_more", "chev")}</summary>
<div class="rows">{_html_why(p)}</div>
<h3 id="requirements">Requirements</h3>
<div class="rows">{"".join(_html_clause(p, t, rulings) for t in p["trust"])}</div>
<h3 id="findings">Findings</h3>
<div class="rows">{found}</div>
<h3 id="checks">Checks</h3>
<div class="rows">{_html_checks(p)}</div>
<h3 id="panel">Reviewers</h3>
<div class="rows">{_html_reviewers(p, rulings)}{_html_refusals(p)}</div>
<h3 id="sign">Sign</h3>
<div class="rows">{_html_residual(p)}</div>
{_html_sign(p["card"]["sign"])}
<details class="fold more-all" id="full"><summary>Full detail <span class="mut">(tier drivers, risk score, engine codes, areas, provenance)</span></summary>
<p class="sm">{_e(st["headline"])}. {_e(st["what"])} <span class="mut">{_e(st["why"])}</span></p>
{full["drivers"]}
{full["risk"]}
{full["codes"]}
{full["areas"]}
{full["reviewers"]}
{panel}
{full["residual"]}
{full["provenance"]}
<h3>Cited code, tests and checks ({len(ev)})</h3>
<div class="chips">{"".join(_chip(e["ref"], e["label"], e["verified"]) for e in ev.values())}</div>
</details>
<div class="cited">{"".join(_html_ev(e) for e in ev.values())}</div>
</details>
</main>"""
    return (f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<meta name="color-scheme" content="light dark">{FAVICON}'
            f"<title>Countersign {_e(p['change'])}: {_e(p['tier'])}, owner {_e(p['owner'])}</title><style>{CSS}{ICON_CSS}</style></head><body>{body}</body></html>\n")
