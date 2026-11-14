"""Renderers for the evidence pack: the CLI sign-off card, pack.md (GitHub PR comment) and pack.html.

They only format what is in pack.json (pack.build puts the reader's view there: story, card, trust chains, reviewer
panel and an evidence index with code excerpts), so what the owner reads is exactly what the pack hash covers.
Layout, top to bottom: the one-screen sign-off card; where the trust comes from (per clause); the reviewer panel;
the evidence (findings, code excerpts, test runs, checks); and, folded, the full detail (all drivers, risk, checks).
"""

from __future__ import annotations

import html
import re
from pathlib import Path

from .common import now_iso

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


def _ruling_text(r: dict) -> str:
    sup = "; ".join(f"{_name(x.get('reviewer', '?'))}: {x.get('claim', '')} ({x.get('why', '')})" for x in r.get("supported", []))
    uns = "; ".join(f"{_name(x.get('reviewer', '?'))}: {x.get('claim', '')} ({x.get('why', '')})" for x in r.get("unsupported", []))
    settle = "; ".join(r.get("evidence_that_would_settle", []))
    return (f"Supported by the cited evidence: {sup or 'nothing'}. Not supported: {uns or 'nothing'}. "
            f"What would settle it: {settle or 'not stated'}.")


def _rulings(p: dict) -> list[dict]:
    return [r for r in (p.get("adjudication") or {}).get("rulings", []) if not r.get("stale")]


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
    """One plain line per adjudicated dispute, counted from the ruling's own supported/unsupported claims:
    `Gemini on N1: backs 2 of 3 claims for Claude's 'not met', 2 of 4 for 'met'`. The full ruling is folded under it."""
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


# --- CLI ------------------------------------------------------------------------------

def card(p: dict) -> str:
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


def _md_ev_link(ref: str, label: str) -> str:
    return f"[`{label}`](#{ref})"


def _md_fold(head: str, rest: str) -> str:
    """Markdown headline with the rest folded (one line, so it also works inside list items and table cells)."""
    return f"{head} <details><summary>more</summary>{_html_inline(rest)}</details>" if rest else head


def _md_ruling(p: dict, r: dict) -> list[str]:
    """One line per dispute (the details summary); the adjudicator's note and full ruling folded under it."""
    def items(xs: list) -> list[str]:
        flat = (lambda t: str(t or "").replace("\n", " "))
        return [f"- **{_name(x.get('reviewer', '?'))}**: {flat(x.get('claim'))} ({flat(x.get('why'))})" for x in xs] or ["- nothing"]
    return ([f"<details><summary>{_html_inline(_ruling_line(p, r))} (advisory)</summary>", ""]
            + ([str(r["note"]).replace("\n", " "), ""] if r.get("note") else [])
            + ["**Backed by the cited evidence**", "", *items(r.get("supported", [])), "", "**Not backed**", "", *items(r.get("unsupported", [])), "",
               "**What would settle it**", "", *(f"- {x}" for x in r.get("evidence_that_would_settle", [])), "", "</details>", ""])


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


def _md_card(p: dict) -> list[str]:
    c, s = p["card"], p["story"]
    rulings = {str(r.get("dispute")): r for r in _rulings(p)}
    out = [f"## Countersign: change {p['change']} is **{p['tier'].upper()}**, owner **{p['owner']}**" + (" (SIMULATED inputs)" if _sim(p) else ""), "",
           f"**{s['headline']}**", "", f"{s['what']} {s['why']}", ""]
    if p.get("mutation"):
        out += [f"> Seeded mutant of {p['mutation'].get('of')}: {p['mutation'].get('description')}", ""]
    out += [f"**Why {p['tier']}**", ""]
    for i, r in enumerate(c["reasons"], 1):
        head, rest = _split(r["text"], 110, REASON_SEPS)
        out.append(f"{i}. " + _md_fold(f"{head} ([evidence]({r['link']}))", rest))
    if c["more_drivers"]:
        out.append(f"\n<sub>All {c['more_drivers']} tier drivers are under Full detail.</sub>")
    out += ["", "**Requirement trace**", "", "| Status | Clause | Why |", "|---|---|---|"]
    for t in c["trace"]:
        head, rest = _trace_why(p, t)
        out.append(f"| **{t['label'].upper()}** | [{_short_id(t['id'])}](#{t['anchor']}) | " + _cell(_md_fold(head, rest)) + " |")
    out.append("")
    for t in c["trace"]:
        if t["id"] in rulings:
            out += _md_ruling(p, rulings[t["id"]])
    out += ["**What the AI found**", ""]
    for f in c["found"]:
        chips = " ".join(_md_ev_link(x["ref"], x["label"]) for x in f["chips"])
        out.append(f"- **{f['severity']}** [{f['title']}](#{f['anchor']}) ({_name(f['reviewer'])} {f['key'].split(':', 1)[1]}"
                   + (f", also {', '.join(_name(n) for n in f['shared_with'])}" if f["shared_with"] else "") + f") {chips}")
    if not c["found"]:
        out.append("- No verified findings.")
    if c["found_total"] > len(c["found"]):
        out.append(f"- +{c['found_total'] - len(c['found'])} more under Evidence.")
    out.append("")
    for f in c["found"]:
        if "finding:" + f["key"] in rulings:
            out += _md_ruling(p, rulings["finding:" + f["key"]])
    out += ["<a id=\"refused\"></a>**What the AI refused to decide, and who should**", ""]
    for g in c["refused"]:
        out.append(f"- <a id=\"{g['anchor']}\"></a>**{g['topic']}** *Who:* {'; '.join(g['who_should_decide'])} "
                   f"(raised by {', '.join(_name(n) for n in g['raised_by'])}) <details><summary>why</summary>{_html_inline(g['why'])}</details>")
    if c["refused_clauses"]:
        out.append(f"- Whether {', '.join(f'[{_short_id(x)}](#chain-{x})' for x in c['refused_clauses'])} "
                   f"{'is' if len(c['refused_clauses']) == 1 else 'are'} met: see the trace. *Who:* {p['owner']}")
    if not (c["refused"] or c["refused_clauses"]):
        out.append("- Nothing: every clause was proven and no reviewer refused a topic.")
    if c.get("refused_peripheral"):
        out += ["", f"<details id=\"refused-peripheral\"><summary>{_peripheral(c)} (out of scope for this change)</summary>"
                + " · ".join(f"<a id=\"{g['anchor']}\"></a>{_html_inline(g['topic'])} ({_name(g['raised_by'][0])})" for g in c["refused_peripheral"])
                + "</details>"]
    out += ["", "**Not checked, and why**", ""]
    for x in c["not_checked"]:
        head, rest = _split(x["reason"], 60)
        out.append(f"- `{x['id']}`: " + _md_fold(head, rest))
    if c["known_gaps"]:
        out.append(f"- Standing pipeline gaps: {', '.join(f'`{g}`' for g in c['known_gaps'])}")
    out += ["", "**Residual risk you accept by signing**", ""] + [f"- {r['text']}" for r in c["residual"]]
    if c.get("residual_more"):
        out += ["", f"<details><summary>{_more_risks(c)}</summary>" + " · ".join(_html_inline(r["text"]) for r in c["residual_more"]) + "</details>"]
    return out + [""] + _md_sign(c["sign"])


def _md_trust(p: dict) -> list[str]:
    ev = p["evidence_index"]
    out = ["<details><summary><b>Where the trust comes from</b> (per requirement clause)</summary>", ""]
    for t in p["trust"]:
        out += [f"<a id=\"{'chain-' + t['id']}\"></a>", f"#### {t['id']}: **{t['label'].upper()}**", "", f"> {t['text']}", ""]
        if t["status"] in ("proven", "held_before"):
            out.append("- **Checks passed:** " + (", ".join(f"`{x['id']}` {x['status']}" for x in t["checks"]) or "none mandated"))
            if t["tests_fail_without_fix"]:
                out.append("- **Fails without the fix:** " + ", ".join(
                    _md_ev_link(x["ref"], x["name"].rsplit(".", 1)[-1]) if x["ref"] else f"`{x['name'].rsplit('.', 1)[-1]}`" for x in t["tests_fail_without_fix"]))
            else:
                out.append("- **Fails without the fix:** no cited test does")
            if t["tests_pass_without_fix"]:
                out.append("- **Passes without the fix too:** " + ", ".join(_md_ev_link(x["ref"], x["name"].rsplit(".", 1)[-1]) for x in t["tests_pass_without_fix"]))
            for r in t["reviewers"]:
                out.append(f"- **{_name(r['reviewer'])}** says {r['verdict'].replace('_', ' ')} ({r['verified']}/{r['cited']} citations verified): "
                           + " ".join(_md_ev_link(x, ev[x]["label"]) for x in r["refs"] if x in ev))
        else:
            for r in t["reviewers"]:
                out.append(f"- **{_name(r['reviewer'])}: {r['verdict'].replace('_', ' ')}** ({r['verified']}/{r['cited']} verified). {r['basis']}")
            for n in t["missing"]:
                out.append(f"- **{_name(n)}**: no verdict")
            out.append("- **Checks:** " + (", ".join(f"`{x['id']}` {x['status']}" for x in t["checks"]) or "none mandated"))
            if t["adjudication"]:
                out.append(f"- **Adjudicator ({_name(p['adjudication']['reviewer'])}, advisory):** {_ruling_text(t['adjudication'])}")
            out.append("- **What would settle it:** " + "; ".join(t["settle"]))
        out.append("")
    return out + ["</details>", ""]


def _md_panel(p: dict) -> list[str]:
    pv = p["panel"]
    rows = pv["rows"]
    out = ["<details><summary><b>Reviewer panel</b> (who said what)</summary>", "<a id=\"panel\"></a>", ""]
    out += [f"> {x}" for x in pv["callouts"]] + ([""] if pv["callouts"] else [])
    out += ["| Clause | " + " | ".join(_name(r["reviewer"]) for r in rows) + " | Result |", "|---|" + "---|" * len(rows) + "---|"]
    for t in p["trust"]:
        out.append(f"| {t['id']} | " + " | ".join(VERDICT_SHORT.get(r["verdicts"].get(t["id"]), "?") for r in rows) + f" | **{t['label']}** |")
    out.append("")
    for r in rows:
        if r.get("missing"):
            out.append(f"- **{_name(r['reviewer'])}**: no review on file")
            continue
        only = ", ".join(f"[{f['id']}](#f-{r['reviewer']}-{f['id']}) {f['severity']} {f['title']}" + (" (rejected)" if f["status"] == "rejected" else "")
                         for f in r["only_this_reviewer"])
        out.append(f"- **{_name(r['reviewer'])}** ({r['model']}, {r['vendor']}{', simulated' if r.get('simulated') else ''}): "
                   f"citations {r['citations_verified']} verified / {r['citations_rejected']} rejected; findings {r['findings_verified']} verified / "
                   f"{r['findings_rejected']} rejected; {r['refusals']} refusals." + (f" Only {_name(r['reviewer'])} raised: {only}" if only else ""))
    if p.get("adjudication"):
        a = p["adjudication"]
        out += ["", f"Adjudicator **{_name(a['reviewer'])}** ({a['model']}, {a['prompt_version']}), advisory only: it can add reasons, never clear."]
        out += [f"- **{r.get('dispute')}**: {_ruling_text(r)}" for r in _rulings(p)] or ["- No rulings on the current disputes (stale file)."]
    elif p.get("disputes"):
        out += ["", f"{len(p['disputes'])} disputed item(s), not adjudicated: {', '.join(x['id'] for x in p['disputes'])}"]
    return out + ["", "</details>", ""]


def _md_evidence(p: dict, excerpts: bool = True) -> list[str]:
    out = ["<details><summary><b>Evidence</b> (findings, cited code, tests and checks)</summary>", ""]
    for f in p["findings"] + p["rejected_claims"]:
        tag = "REJECTED: " if f["status"] == "rejected" else ""
        out += [f"<a id=\"f-{f['reviewer']}-{f['id']}\"></a>",
                f"#### {tag}{_name(f['reviewer'])} {f['id']} [{f['severity']}, {f['category']}]: {f['title']}", "", f["claim"], ""]
        out.append("Evidence: " + " ".join(_md_ev_link(e["ref"], e["label"] if "label" in e else p["evidence_index"].get(e.get("ref"), {}).get("label", e.get("kind")))
                                         + ("" if e["verified"] else " (not verified)") for e in f["evidence"]))
        if f["status"] == "rejected":
            out.append(f"\nRejected: {f['rejection_reason']}")
        else:
            out.append(f"\nTier effect: {f['tier']}" + (f" ({f['tier_reason']})" if f.get("tier_reason") else ""))
        if f.get("suggested_fix"):
            out.append(f"\nSuggested fix: {f['suggested_fix']}")
        out.append("")
    out += ["#### Cited evidence", ""]
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
    out = ["<details><summary><b>Full detail</b>: all tier drivers, risk score, every check, areas, not checked, residual risk</summary>", "",
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


MD_LIMIT = 60000  # GitHub comments stop at 65536 characters


def to_markdown(p: dict) -> str:
    """The card in plain GitHub Markdown, everything else in <details>. Shrinks to stay under a PR comment's limit."""
    head = _md_card(p) + _md_supply(p)
    for parts in ((_md_trust(p), _md_panel(p), _md_evidence(p), _md_full(p)),
                  (_md_trust(p), _md_panel(p), _md_evidence(p, excerpts=False), _md_full(p)),
                  (_md_trust(p), _md_panel(p), _md_full(p)),
                  (_md_panel(p),)):
        text = "\n".join(head + [x for part in parts for x in part])
        if len(text) <= MD_LIMIT:
            return text
    return "\n".join(head)[:MD_LIMIT]


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
h1{font-size:20px;line-height:1.25;font-weight:600;margin:8px 0 4px}h2{font-size:20px;line-height:1.25;font-weight:600;margin:32px 0 8px;padding-bottom:8px;border-bottom:1px solid var(--line)}
h3{font-size:12px;letter-spacing:.04em;text-transform:uppercase;font-weight:600;color:var(--mut);margin:16px 0 4px}h4{font-size:16px;font-weight:600;margin:0 0 4px}
p{margin:4px 0 8px}ul,ol{margin:4px 0;padding-left:24px}li{margin:4px 0}.mut{color:var(--mut)}.sm{font-size:14px}
code,pre,.mono{font-family:var(--mono);font-size:.875em}code{overflow-wrap:anywhere;background:var(--sf);border:1px solid var(--line);border-radius:4px;padding:0 4px}
pre code{background:none;border:0;padding:0}
.eyebrow{font:12px/1.5 var(--mono);text-transform:uppercase;letter-spacing:.04em;color:var(--mut);margin:0}.story{font-size:14px;margin:4px 0 8px}
nav.jump{font-size:14px;margin:8px 0 0;display:flex;flex-wrap:wrap;gap:4px 16px}
.banner{background:var(--badb);color:var(--bad);border:1px solid var(--bad);padding:8px 12px;border-radius:6px;font-weight:600}
.card{background:var(--bg);border:1px solid var(--line);border-radius:6px;padding:12px 16px 16px;margin:4px 0 16px}
.verdict{display:flex;flex-wrap:wrap;align-items:center;gap:8px 12px}
.tier{display:inline-block;border:1px solid currentColor;border-radius:999px;padding:2px 12px;font:600 14px/20px var(--mono);letter-spacing:.02em;text-transform:uppercase}
.tier.sm{font-size:12px;line-height:18px;padding:0 8px}
.t-silent{color:var(--t-silent);background:var(--t-silentb)}.t-notify{color:var(--t-notify);background:var(--t-notifyb)}.t-ask{color:var(--t-ask);background:var(--t-askb)}.t-block{color:var(--t-block);background:var(--t-blockb)}
ol.reasons{padding-left:24px}ol.reasons li{margin:4px 0}
ul.rows{list-style:none;padding:0;margin:0}ul.rows>li{display:grid;grid-template-columns:auto minmax(0,1fr);gap:4px 8px;align-items:start;padding:8px 0;border-top:1px solid var(--line)}
ul.rows>li:first-child{border-top:0}
.st,.sev{display:inline-flex;align-items:center;gap:4px;white-space:nowrap;font:600 12px/18px var(--mono);text-transform:uppercase;border:1px solid currentColor;border-radius:999px;padding:0 8px;margin-top:2px}
.st-proven{color:var(--ok);background:var(--okb)}.st-refused{color:var(--warn);background:var(--warnb)}.st-notmet{color:var(--bad);background:var(--badb)}.st-held{color:var(--held);background:var(--heldb)}
.sev-blocker,.sev-major{color:var(--bad);background:var(--badb)}.sev-minor{color:var(--warn);background:var(--warnb)}.sev-info{color:var(--held);background:var(--heldb)}
.chips{display:flex;flex-wrap:wrap;gap:4px;margin-top:4px}
.chip{font-family:var(--mono);font-size:12px;border:1px solid var(--line);background:var(--sf);border-radius:6px;padding:0 6px;text-decoration:none;overflow-wrap:anywhere}
.chip.bad{border-style:dashed;color:var(--mut)}
.sign{border:1px solid var(--line);border-left:3px solid var(--t-ask);background:var(--sf);border-radius:6px;padding:8px 12px;margin-top:16px}
.sign q{font-style:italic;quotes:none}
pre{background:var(--sf);border:1px solid var(--line);padding:8px 12px;border-radius:6px;overflow-x:auto;margin:8px 0}
pre.code{padding:8px 0}pre.code span{display:block;padding:0 12px 0 0;white-space:pre}
pre.code span i{display:inline-block;min-width:4.2em;padding:0 .8em 0 .5em;text-align:right;color:var(--mut);font-style:normal;user-select:none}
pre.code span.hl{background:var(--mark);box-shadow:inset 3px 0 0 var(--t-ask)}pre.code span.hl i{color:var(--fg);font-weight:600}
article,.box{border:1px solid var(--line);border-radius:6px;padding:12px 16px;margin:8px 0;background:var(--bg)}
article.c-refused,article.c-notmet{border-left:3px solid var(--warn)}article.c-notmet{border-left-color:var(--bad)}article.c-proven{border-left:3px solid var(--ok)}article.c-held{border-left:3px solid var(--held)}
.callout{border:1px solid var(--line);border-left:3px solid var(--t-ask);background:var(--sf);border-radius:6px;padding:8px 12px;margin:8px 0}
blockquote{margin:4px 0;padding:4px 12px;border-left:3px solid var(--line);color:var(--mut)}
ol.chain{padding-left:24px}ol.chain>li{margin:8px 0}
.scroll{overflow-x:auto;border:1px solid var(--line);border-radius:6px;margin:8px 0}table{border-collapse:collapse;width:100%;font-size:14px}
th,td{text-align:left;padding:6px 10px;border-bottom:1px solid var(--line);vertical-align:top}tr:last-child td{border-bottom:0}
th{font-size:12px;font-weight:600;text-transform:uppercase;letter-spacing:.03em;color:var(--mut);background:var(--sf)}th,td{overflow-wrap:break-word}td.n{text-align:right}
.v-met{color:var(--ok);font-weight:600}.v-not_met{color:var(--bad);font-weight:600}.v-cannot_determine,.v-none{color:var(--warn);font-weight:600}
details.fold{margin-top:32px;border-top:1px solid var(--line);padding-top:8px}details.fold>summary{font-weight:600;cursor:pointer;padding:8px 0}
details.mini>summary{cursor:pointer;color:var(--link);font-size:14px}
details.clip>summary{list-style:none;cursor:pointer}details.clip>summary::-webkit-details-marker{display:none}
details.clip>summary::after{content:" more";color:var(--link);font-size:13px;white-space:nowrap}details.clip[open]>summary::after{content:" less"}
details.clip>div{margin:4px 0 2px}details.clip>div p{margin:2px 0 6px}details.adj{margin-top:2px}details.adj>summary{font-size:14px}
pre.cmd span{white-space:nowrap}pre.cmd{white-space:pre-wrap;overflow-wrap:normal;margin:6px 0 4px}.sign details.mini{margin-top:4px}
:target{scroll-margin-top:8px;outline:2px solid var(--focus);outline-offset:4px;border-radius:6px}
.ok{color:var(--ok);font-weight:600}.no{color:var(--bad);font-weight:600}
.sr{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0);white-space:nowrap}
@media (min-width:720px){body{font-size:16px}main{padding:24px 32px 64px}h1{font-size:24px}.story{font-size:15px}.card{padding:16px 24px 24px}}
@media (max-width:480px){.eyebrow .range{display:none}}
@media print{details{display:block}details>*{display:block}.jump{display:none}}
"""


def _e(x) -> str:
    return html.escape("" if x is None else str(x))


def _tier(t: str, sm: bool = False) -> str:
    return f'<span class="tier{" sm" if sm else ""} t-{_e(t)}">{_e(t)}</span>'


def _status(label: str) -> str:
    cls, glyph, title = STATUS.get(label, ("refused", "?", label))
    return f'<span class="st st-{cls}" title="{_e(title)}"><span aria-hidden="true">{glyph}</span>{_e(label)}</span>'


def _sev(s: str) -> str:
    return f'<span class="sev sev-{_e(s)}">{_e(s)}</span>'


def _chip(ref: str, label: str, ok: bool = True) -> str:
    return f'<a class="chip{"" if ok else " bad"}" href="#{_e(ref)}">{_e(label)}{"" if ok else " (not verified)"}</a>'


def _table(headers: list[str], rows: list[list[str]], numeric: frozenset = frozenset(), caption: str = "") -> str:
    head = "".join(f'<th scope="col">{_e(h)}</th>' for h in headers)
    body = "".join("<tr>" + "".join(f'<td{" class=n" if i in numeric else ""}>{c}</td>' for i, c in enumerate(r)) + "</tr>" for r in rows)
    cap = f'<caption class="sr">{_e(caption)}</caption>' if caption else ""
    return f'<div class="scroll"><table>{cap}<thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>'


def _clip(head: str, rest: str, cls: str = "clip") -> str:
    """A headline that opens to the rest in one tap (both already HTML-escaped). No rest, no fold."""
    if not rest:
        return head
    return f'<details class="{cls}"><summary>{head}</summary><div class="sm mut">{rest}</div></details>'


def _html_ruling(p: dict, r: dict, chain: bool = True) -> str:
    """One line per dispute; the adjudicator's note and full ruling folded under it."""
    def items(xs: list, title: str) -> str:
        lis = "".join(f'<li><b>{_e(_name(x.get("reviewer", "?")))}</b>: {_e(x.get("claim"))} <span class="mut">({_e(x.get("why"))})</span></li>' for x in xs)
        return f"<p><b>{title}</b></p><ul>{lis or '<li>nothing</li>'}</ul>"

    body = ((f'<p>{_e(r["note"])}</p>' if r.get("note") else "") + items(r.get("supported", []), "Backed by the cited evidence")
            + items(r.get("unsupported", []), "Not backed") + "<p><b>What would settle it</b></p><ul>"
            + "".join(f"<li>{_e(x)}</li>" for x in r.get("evidence_that_would_settle", [])) + "</ul>")
    if chain and not str(r.get("dispute", "")).startswith("finding:"):
        body += f'<p><a href="#chain-{_e(r.get("dispute"))}">The full chain for {_e(_short_id(str(r.get("dispute"))))}</a></p>'
    return _clip(f'{_e(_ruling_line(p, r))} <span class="mut">(advisory)</span>', body, "clip adj")


def _html_card(p: dict) -> str:
    c, st = p["card"], p["story"]
    rulings = {str(r.get("dispute")): r for r in _rulings(p)}
    reasons = ""
    for r in c["reasons"]:
        head, rest = _split(r["text"], 110, REASON_SEPS)
        link = f' <a class="sm" href="{_e(r["link"])}">evidence</a>'
        reasons += f"<li>{_clip(_e(head) + link, _e(rest))}</li>"
    more = (f'<p class="sm mut">All {c["more_drivers"]} tier drivers are in <a href="#all-drivers">full detail</a>.</p>' if c["more_drivers"] else "")
    trace = ""
    for t in c["trace"]:
        head, rest = _trace_why(p, t)
        idl = f'<a href="#{_e(t["anchor"])}"><b title="{_e(t["id"])}">{_e(_short_id(t["id"]))}</b></a> '
        adj = _html_ruling(p, rulings[t["id"]]) if t["id"] in rulings else ""
        trace += f'<li>{_status(t["label"])}<div>{_clip(idl + _e(head), _e(rest))}{adj}</div></li>'
    found = "".join(
        f'<li>{_sev(f["severity"])}<div><a href="#{_e(f["anchor"])}">{_e(f["title"])}</a> '
        f'<span class="mut sm">{_e(_name(f["reviewer"]))} {_e(f["key"].split(":", 1)[1])}'
        + (f', also {_e(", ".join(_name(n) for n in f["shared_with"]))}' if f["shared_with"] else ", only this reviewer") + "</span>"
        f'<div class="chips">{"".join(_chip(x["ref"], x["label"]) for x in f["chips"])}</div>'
        + (_html_ruling(p, rulings["finding:" + f["key"]]) if "finding:" + f["key"] in rulings else "") + "</div></li>" for f in c["found"])
    if not c["found"]:
        found = '<li><span class="st st-proven">none</span><div>No verified findings.</div></li>'
    if c["found_total"] > len(c["found"]):
        found += f'<li><span></span><div class="sm"><a href="#findings">+{c["found_total"] - len(c["found"])} more findings</a></div></li>'
    refused = ""
    for g in c["refused"]:
        head, rest = _split(g["topic"], 80)
        why = (f"{_e(rest)}<br>" if rest else "") + f'<b>Why the AI would not decide:</b> {_e(g["why"])}'
        refused += (f'<li id="{_e(g["anchor"])}"><span class="st st-refused"><span aria-hidden="true">?</span>open</span><div>'
                    f'{_clip("<b>" + _e(head) + "</b>", why)}'
                    f'<div class="sm">Who: <b>{_e("; ".join(g["who_should_decide"]))}</b> '
                    f'<span class="mut">(raised by {_e(", ".join(_name(n) for n in g["raised_by"]))})</span></div></div></li>')
    if c["refused_clauses"]:
        links = ", ".join(f'<a href="#chain-{_e(x)}">{_e(_short_id(x))}</a>' for x in c["refused_clauses"])
        refused += (f'<li><span class="st st-refused"><span aria-hidden="true">?</span>open</span><div><b>Whether {links} '
                    f'{"is" if len(c["refused_clauses"]) == 1 else "are"} met</b><div class="sm">Not proven by the AI (see the trace). '
                    f'Who: <b>{_e(p["owner"])}</b></div></div></li>')
    if not refused:
        refused = '<li><span class="st st-proven">none</span><div>Every clause was proven and no reviewer refused a topic.</div></li>'
    if c.get("refused_peripheral"):
        refused += (f'<li><span></span><div class="sm"><details class="mini" id="refused-peripheral"><summary>{_e(_peripheral(c))} (out of scope for this change)</summary><ul>'
                    + "".join(f'<li id="{_e(g["anchor"])}">{_e(g["topic"])} <span class="mut">(who: {_e("; ".join(g["who_should_decide"]))}; '
                              f'raised by {_e(", ".join(_name(n) for n in g["raised_by"]))})</span></li>' for g in c["refused_peripheral"])
                    + "</ul></details></div></li>")
    nc = ""
    for x in c["not_checked"]:
        head, rest = _split(x["reason"], 60)
        nc += "<li>" + _clip(f"<code>{_e(x['id'])}</code>: {_e(head)}", _e(rest)) + "</li>"
    if c["known_gaps"]:
        nc += f'<li class="mut">Standing pipeline gaps: {_e(", ".join(c["known_gaps"]))} (<a href="#not-checked">why</a>)</li>'
    residual = "".join(f'<li>{_e(r["text"])} <a class="sm" href="{_e(r["link"])}">see</a></li>' for r in c["residual"])
    if c.get("residual_more"):
        residual += (f'<li class="mut"><details class="mini"><summary>{_e(_more_risks(c))}</summary><ul>'
                     + "".join(f'<li>{_e(r["text"])} <a class="sm" href="{_e(r["link"])}">see</a></li>' for r in c["residual_more"])
                     + "</ul></details></li>")
    sg = c["sign"]
    return f"""
<section class="card" aria-labelledby="card-h" id="card">
<p class="eyebrow"><span id="card-h">Countersign sign-off card</span> &middot; change {_e(p["change"])}<span class="range"> &middot; <span class="mono">{_e(p["base"])}..{_e(p["head"])}</span></span></p>
<div class="verdict">{_tier(p["tier"])}<span><b>{_e(p["owner"])}</b> {"must countersign" if sg["required"] else "is notified (AI-cleared)"}
{('<span class="mut sm"> &middot; FYI ' + _e(", ".join(p["notify"])) + "</span>") if p["notify"] else ""}</span></div>
<h1>{_e(st["headline"])}</h1>
<p class="story">{_e(st["what"])} <span class="mut">{_e(st["why"])}</span></p>
<h3>Why {_e(p["tier"])}</h3><ol class="reasons">{reasons}</ol>{more}
<h3>Requirement trace</h3><ul class="rows">{trace}</ul>
<h3>What the AI found</h3><ul class="rows">{found}</ul>
<h3 id="refused">What the AI refused to decide, and who should</h3><ul class="rows">{refused}</ul>
<h3>Not checked, and why</h3><ul class="sm">{nc or "<li>Everything mandated ran.</li>"}</ul>
<h3>Residual risk you accept by signing</h3><ul class="sm">{residual}</ul>
{_html_sign(sg)}
</section>"""


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


def _html_trust(p: dict) -> str:
    ev = p["evidence_index"]
    out = []
    for t in p["trust"]:
        cls = STATUS.get(t["label"], ("refused",))[0]
        head = f'<h4>{_status(t["label"])} {_e(t["id"])}</h4><blockquote>{_e(t["text"])}</blockquote>'
        checks = "".join(f'<li><code>{_e(x["id"])}</code> <span class="{"ok" if x["status"] == "pass" else "no"}">{_e(x["status"])}</span>'
                         f'{": " + _e(x["summary"]) if x.get("summary") else ""}'
                         + "".join(f' <span class="mono mut sm">{_e(lg)}</span>' for lg in x["logs"][:1]) + "</li>" for x in t["checks"]) or "<li>none mandated</li>"
        if t["status"] in ("proven", "held_before"):
            fails = ("".join(_chip(x["ref"], x["name"].rsplit(".", 1)[-1]) if x["ref"] else f'<span class="chip">{_e(x["name"].rsplit(".", 1)[-1])}</span>'
                             for x in t["tests_fail_without_fix"]) or '<span class="mut">no cited test fails without the fix</span>')
            passes = "".join(_chip(x["ref"], x["name"].rsplit(".", 1)[-1]) for x in t["tests_pass_without_fix"])
            revs = "".join(f'<li><b>{_e(_name(r["reviewer"]))}</b> said <span class="v-{_e(r["verdict"])}">{_e(r["verdict"].replace("_", " "))}</span> '
                           f'<span class="mut sm">({r["verified"]} of {r["cited"]} citations verified)</span>'
                           f'<div class="chips">{_ev_chips(r["refs"], ev)}</div></li>' for r in t["reviewers"])
            body = (f'<ol class="chain"><li><b>Checks that passed</b><ul class="sm">{checks}</ul></li>'
                    f'<li><b>Tests that fail without the fix</b><div class="chips">{fails}</div>'
                    + (f'<div class="sm mut">Pass without the fix too (they show existing behaviour):</div><div class="chips">{passes}</div>' if passes else "")
                    + f'</li><li><b>Reviewers who agreed, with verified citations</b><ul>{revs}</ul></li></ol>')
            if t["status"] == "held_before":
                body += f'<p class="sm"><b>Held before:</b> {_e(t["why"])}</p>'
        else:
            revs = "".join(f'<li><b>{_e(_name(r["reviewer"]))}</b>: <span class="v-{_e(r["verdict"])}">{_e(r["verdict"].replace("_", " "))}</span> '
                           f'<span class="mut sm">({r["verified"]}/{r["cited"]} verified)</span><div class="sm">{_e(r["basis"])}</div>'
                           f'<div class="chips">{_ev_chips(r["refs"] + r["unverified_refs"], ev)}</div></li>' for r in t["reviewers"])
            revs += "".join(f'<li><b>{_e(_name(n))}</b>: <span class="v-none">no verdict</span></li>' for n in t["missing"])
            adj = (f'<div class="sm"><b>Adjudicator</b> <span class="mut">(advisory, cannot clear)</span>: {_html_ruling(p, t["adjudication"], chain=False)}</div>'
                   if t["adjudication"] else "")
            body = (f'<p><b>Refused:</b> {_e(t["why"])}</p><ol class="chain"><li><b>Who said what</b><ul>{revs}</ul></li>'
                    f'<li><b>Checks</b><ul class="sm">{checks}</ul></li></ol>{adj}'
                    f'<p><b>What would settle it</b></p><ul class="sm">{"".join(f"<li>{_e(x)}</li>" for x in t["settle"])}</ul>')
        out.append(f'<article id="chain-{_e(t["id"])}" class="c-{cls}">{head}{body}</article>')
    return "".join(out)


def _html_panel(p: dict) -> str:
    pv = p["panel"]
    rows = pv["rows"]
    callouts = "".join(f'<p class="callout">{_e(x)}</p>' for x in pv["callouts"])
    matrix = _table(["Clause", *(_name(r["reviewer"]) for r in rows), "Result"],
                    [[f'<a href="#chain-{_e(t["id"])}">{_e(_short_id(t["id"]))}</a>',
                      *(f'<span class="v-{_e(r["verdicts"].get(t["id"]) or "none")}">{_e(VERDICT_SHORT.get(r["verdicts"].get(t["id"]), "?"))}</span>' for r in rows),
                      _status(t["label"])] for t in p["trust"]], caption="Verdict per clause and reviewer")
    cards = []
    for r in rows:
        if r.get("missing"):
            cards.append(f'<div class="box"><h4>{_e(_name(r["reviewer"]))}</h4><p class="no">No review on file: every clause waits for it.</p></div>')
            continue
        only = "".join(f'<li>{_sev(f["severity"])} <a href="#f-{_e(r["reviewer"])}-{_e(f["id"])}">{_e(f["id"])}: {_e(f["title"])}</a>'
                       + (' <span class="no sm">rejected</span>' if f["status"] == "rejected" else "") + "</li>" for f in r["only_this_reviewer"])
        cards.append(f'<div class="box"><h4>{_e(_name(r["reviewer"]))} <span class="mut sm">{_e(r["model"])} &middot; {_e(r["vendor"])} &middot; {_e(r["prompt_version"])}'
                     f'{" &middot; SIMULATED" if r.get("simulated") else ""}</span></h4>'
                     f'<p class="sm">Citations: <span class="ok">{r["citations_verified"]} verified</span>, <span class="{"no" if r["citations_rejected"] else "mut"}">'
                     f'{r["citations_rejected"]} rejected</span> &middot; findings: {r["findings_verified"]} verified, {r["findings_rejected"]} rejected &middot; '
                     f'{r["refusals"]} refusals</p>'
                     + (f'<p class="sm"><b>Only {_e(_name(r["reviewer"]))} raised:</b></p><ul class="sm">{only}</ul>' if only else '<p class="sm mut">Raised nothing the others did not.</p>')
                     + "</div>")
    adj = ""
    if p.get("adjudication"):
        a = p["adjudication"]
        adj = (f'<div class="box"><h4>{_e(_name(a["reviewer"]))} <span class="mut sm">adjudicator &middot; {_e(a["model"])} &middot; advisory: adds reasons, never clears</span></h4>'
               + ("".join(f'<div class="sm">{_html_ruling(p, r)}</div>' for r in _rulings(p)) or '<p class="sm mut">No rulings on current disputes (stale).</p>')
               + "</div>")
    elif p.get("disputes"):
        adj = (f'<p class="sm mut">{len(p["disputes"])} disputed item(s) not adjudicated'
               + (f" ({_e(_name(pv['adjudicator']))} has not run)" if pv["adjudicator"] else "") + f': {_e(", ".join(x["id"] for x in p["disputes"]))}</p>')
    excl = "".join(f'<p class="sm mut">Excluded {_e(_name(x["name"]))} ({_e(x["vendor"])}): {_e(x["reason"])}</p>' for x in p["reviewer_panel"]["excluded"])
    rule = '<p class="sm mut">Rule: a clause is proven only if every participating reviewer says met with verified evidence and its checks pass. Unanimity, not a vote: each added reviewer can only make the AI more cautious.</p>'
    return callouts + matrix + rule + "".join(cards) + adj + excl


def _html_finding(f: dict, ev: dict) -> str:
    rej = f["status"] == "rejected"
    chips = "".join(_chip(e["ref"], ev.get(e["ref"], {}).get("label", e.get("kind", "?")), e["verified"]) for e in f["evidence"])
    effect = (f'<p class="sm no">Rejected: {_e(f["rejection_reason"])}</p>' if rej
              else f'<p class="sm">Tier effect: {_tier(f["tier"], True)} {_e(f.get("tier_reason", ""))}</p>')
    fix = f'<p class="sm"><b>Suggested fix:</b> {_e(f["suggested_fix"])}</p>' if f.get("suggested_fix") else ""
    return (f'<article id="f-{_e(f["reviewer"])}-{_e(f["id"])}" class="{"c-notmet" if rej else ""}"><h4>{_sev(f["severity"])} {"<span class=no>REJECTED</span> " if rej else ""}'
            f'{_e(f["title"])}</h4><p class="sm mut">{_e(_name(f["reviewer"]))} {_e(f["id"])} &middot; {_e(f["category"])}</p><p>{_e(f["claim"])}</p>'
            f'<div class="chips">{chips}</div>{fix}{effect}</article>')


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
    return f'<article id="{_e(e["ref"])}">{head}{body}</article>'


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


def _html_full(p: dict) -> str:
    ms = p["mandate"]["signature"]
    rp = p["reviewer_panel"]
    driver_rows = [[_tier(w["tier"], True), _e(w["source"]), f"<code>{_e(w['id'])}</code>", _e(w["why"])] for w in p["drivers"]]
    risk_rows = [[_e(f["factor"]), _e(f["points"]), _e(f["reason"])] for f in p["risk"]["factors"]]
    risk_rows.append(["<b>total</b>", f"<b>{_e(p['risk']['score'])}</b>", f"{_tier(p['risk']['tier'], True)} (bands {_e(p['risk']['thresholds'])})"])
    tool_rows = [[f"<code>{_e(t['id'])}</code>", f'<span class="{"ok" if t["status"] == "pass" else "no"}">{_e(t["status"])}</span>',
                  _e(f"{t.get('tool') or ''} {t.get('tool_version') or ''}"), _e(t.get("summary")),
                  "<br>".join(f'<span class="mono">{_e(x)}</span>' for x in ([t["log"]] if isinstance(t.get("log"), str) else (t.get("log") or [])))]
                 for t in p["checked_by"]["tools"]]
    rev_rows = [[_e(r["reviewer"]), _e(f"{r['model']} ({r['vendor']})"), _e(r["prompt_version"]), _e(r["reviewed_at"]),
                 str(r["verified"]), str(r["rejected"]), str(r["refusals"])] for r in p["checked_by"]["reviewers"]]
    area_rows = [[_e(a["name"]), _e(a["owner"]), _e(a["sensitivity"]), _tier(a["cap"], True), _e(a["cap_reason"]), str(len(a["files"]))] for a in p["areas"]]
    req_rows = [[f"<code>{_e(c['id'])}</code>", _e(c["status"]),
                 "<br>".join(f"{_e(n)}: {_e(v['verdict'])} ({v['verified']}/{v['cited']})" for n, v in c["verdicts"].items()) or "none",
                 "<br>".join(f"{_e(x['id'])}: {_e(x['status'])}" for x in c["checks"]) or "-",
                 "<br>".join(f"<code>{_e(r['code'])}</code> {_e(r['detail'])}" for r in c["reasons"]) or "-"] for c in p["requirements"]]
    refusals = "".join(f"<li><b>{_e(r['reviewer'])}</b>: {_e(r['topic'])}. <span class=mut>Why: {_e(r['reason'])} Who: {_e(r['who_should_decide'])}</span></li>"
                       for r in p["refused"]["reviewer_refusals"]) or "<li>none</li>"
    return f"""
<details class="fold" id="full"><summary>Full detail: all tier drivers, risk score, every check, areas, not checked, inputs</summary>
<h3 id="all-drivers">All tier drivers (tier = strictest)</h3>{_table(["Tier", "Source", "Id", "Why"], driver_rows)}
<h3 id="risk">Risk score {_e(p["risk"]["score"])}</h3>{_table(["Factor", "Points", "Reason"], risk_rows, frozenset({1}))}
<h3 id="checks">Every check</h3>{_table(["Check", "Status", "Tool", "Summary", "Log"], tool_rows)}
<h3>Reviewers</h3>
<p class="sm">Participating: <b>{_e(", ".join(rp["reviewers"]) or "none")}</b>; adjudicator: {_e(rp["adjudicator"] or "none")}; confidential: {_e("yes (" + rp["why"] + ")" if rp["confidential"] else "no")}.</p>
{"".join(f"<p class='sm mut'>Not used: {_e(x['name'])}: {_e(x['reason'])}</p>" for x in rp["ignored_files"])}
{_table(["Reviewer", "Model", "Prompt", "Reviewed", "Verified", "Rejected", "Refusals"], rev_rows, frozenset({4, 5, 6}))}
<h3>Every reviewer refusal</h3><ul class="sm">{refusals}</ul>
<h3>Requirement trace, engine codes</h3>{_table(["Clause", "Status", "Verdicts", "Checks", "Reasons"], req_rows)}
<h3 id="areas">Areas touched</h3>{_table(["Area", "Owner", "Sensitivity", "AI cap", "Cap source", "Files"], area_rows, frozenset({5}))}
<h3 id="not-checked">What was not checked, and why</h3>
<ul class="sm">{"".join(f"<li><code>{_e(x['id'])}</code> <span class=mut>({_e(x['source'])})</span>: {_e(x['reason'])}</li>" for x in p["not_checked"])}</ul>
<h3>Residual risk, every item</h3><ul class="sm">{"".join(f"<li>{_e(r)}</li>" for r in p["residual_risk"])}</ul>
<h3>Provenance</h3>
<p class="sm">Branch <code>{_e(p["branch"])}</code> {_e(p["base"])}..{_e(p["head"])}, {_e(p["diff"]["files"])} files, +{_e(p["diff"]["insertions"])} &minus;{_e(p["diff"]["deletions"])}, author {_e(p["author"])} (agent-written: {_e(p["agent_written"])}). Commit: &ldquo;{_e(p["commit_message"])}&rdquo;.</p>
<p class="sm">Mandate {_e(p["mandate"]["id"])} v{_e(p["mandate"]["version"])} <code>{_e(p["mandate"]["sha256"][:16])}</code>:
{"signed by " + _e(ms.get("signed_by")) if ms["valid"] else "<b class=no>signature not valid: " + _e(ms["reason"]) + "</b>"}. {_e(p["checked_by"]["engine"])}.</p>
<p class="sm mut">Inputs: facts {_e(p["inputs"]["facts"]["path"])} ({_e(p["inputs"]["facts"]["sha256"][:12])}), requirements {_e(p["inputs"]["requirements"]["path"])},
reviews {_e(", ".join(f"{k} ({v['sha256'][:12]})" for k, v in p["inputs"]["reviews"].items()))}. Rendered {_e(now_iso())}.</p>
</details>"""


def to_html(p: dict) -> str:
    s = p["story"]
    ev = p["evidence_index"]
    findings = "".join(_html_finding(f, ev) for f in p["findings"]) or '<p class="sm mut">No verified findings.</p>'
    rejected = "".join(_html_finding(f, ev) for f in p["rejected_claims"])
    mut = f'<p class="callout">Seeded mutant of {_e(p["mutation"].get("of"))}: {_e(p["mutation"].get("description"))}</p>' if p.get("mutation") else ""
    body = f"""
<main>
{'<p class="banner">Simulated inputs: fixture data, not a real run</p>' if _sim(p) else ""}
{mut}
{_html_card(p)}
<nav class="jump" aria-label="Sections"><a href="#supply-chain">Supply chain</a><a href="#trust">Where the trust comes from</a><a href="#panel">Reviewer panel</a><a href="#evidence">Evidence</a><a href="#full">Full detail</a></nav>
<h2 id="supply-chain">Supply chain (from the build)</h2>
{_html_supply(p)}
<h2 id="trust">Where the trust comes from</h2>
<p class="sm mut">For each requirement clause: the checks that passed, the tests that fail without the fix, and the reviewers who agreed with verified citations; for refused clauses, who disagreed and what would settle it.</p>
{_html_trust(p)}
<h2 id="panel">Reviewer panel</h2>
{_html_panel(p)}
<h2 id="evidence">Evidence</h2>
<h3 id="findings">Findings ({len(p["findings"])} verified{", " + str(len(p["rejected_claims"])) + " rejected" if p["rejected_claims"] else ""})</h3>
{findings}{rejected}
<h3>Cited code, tests and checks ({len(ev)})</h3>
<p class="sm mut">Code is shown from git at the cited revision; the cited line is highlighted. Tests show every run they appear in, including the run with the fix reverted.</p>
{"".join(_html_ev(e) for e in ev.values())}
{_html_full(p)}
</main>"""
    return (f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<meta name="color-scheme" content="light dark">'
            f"<title>Countersign {_e(p['change'])}: {_e(p['tier'])}, owner {_e(p['owner'])}</title><style>{CSS}</style></head><body>{body}</body></html>\n")
