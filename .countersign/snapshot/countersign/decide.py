"""Stage 4: decide. Every outcome carries the rule that produced it and the evidence it used.

- Per requirement clause: `proven` or `refused` with machine reasons.
- Risk score: additive factors, each with points and a one-line reason; weights come from the mandate.
- Tier: the strictest of every driver (risk band, mandate rules, area trust caps, refusals, verified findings).
"""

from __future__ import annotations

import math
import re

from .common import TIERS, strictest
from .injection import only_unscannable
from .mandate import SENSITIVITY, Mandate, matches

# When several drivers set the same tier, the most specific one is listed first.
SOURCE_ORDER = ["mandate rule", "failing check", "verified finding", "refused clause", "adjudicator", "reviewer refusal", "held before",
                "trust cap", "risk score"]
REFUSAL_REASONS = ["check_failed", "check_not_run", "missing_review", "not_met", "reviewers_disagree", "cannot_determine", "thin_evidence",
                   "adjudicator_dispute", "reviewers_untrusted", "tests_kill_no_mutant"]
# Principle 0: a mandated check in one of these states can't be argued away by verdicts, adjudication or trust.
NOT_PASSING = ("fail", "error")
INJECTION_CHECK = "injection_scan"
REPRO_PREFIX = "repro."


def check_status(facts: dict, check_id: str) -> str:
    """pass | fail | skipped | error | absent. Only `pass` counts as passing."""
    return next((c["status"] for c in facts.get("checks", []) if c["id"] == check_id), "absent")


def check(facts: dict, check_id: str) -> dict | None:
    return next((c for c in facts.get("checks", []) if c["id"] == check_id), None)


def is_repro(check_id: str) -> bool:
    """repro.<reviewer>.<finding-id>: the pipeline's attempt to reproduce a finding. Its status says whether the
    finding reproduced, not whether the change is good, so it never counts as a failed check of the change."""
    return str(check_id).startswith(REPRO_PREFIX)


def injection_lines(facts: dict) -> list[str]:
    """The lines injection_scan matched (text addressed to automated reviewers), as `where: text`."""
    c = check(facts, INJECTION_CHECK) or {}
    out = []
    for m in c.get("matches") or c.get("hits") or []:
        if isinstance(m, dict):
            where = m.get("file") or m.get("where") or m.get("source") or "?"
            line = f":{m['line']}" if m.get("line") is not None else ""
            out.append(f"{where}{line}: {str(m.get('text') or m.get('match') or m.get('line_text') or '').strip()}")
        else:
            out.append(str(m))
    return out or ([c["summary"]] if c.get("summary") else [])


def injection_found(facts: dict) -> bool:
    """injection_scan found text addressed to reviewers (not only content it could not read: see injection_unscannable)."""
    c = check(facts, INJECTION_CHECK)
    return c is not None and c.get("status") == "fail" and not only_unscannable(c)


def injection_unscannable(facts: dict) -> bool:
    """injection_scan failed only because it could not read something (binary files): a human looks (ask), but nothing
    planted was found, so reviewers stay trusted and R-INJECT does not block (red team I9)."""
    c = check(facts, INJECTION_CHECK)
    return c is not None and only_unscannable(c)


def generated_hand_edited(facts: dict) -> list[str]:
    """Files named like generated output (`*.g.cs`, or a T4 template's `.cs`, which stage 1 marks `looks_generated`)
    that stage 1 classified as not generated because their input did not change in the diff: a hand edit to the
    output (red team G2: the depth guard removed from every generated formatter)."""
    return [f["path"] for f in files(facts) if f.get("kind") != "generated" and (f.get("looks_generated") or f["path"].endswith(".g.cs"))]


def public_api_changed(facts: dict) -> bool | None:
    c = next((c for c in facts.get("checks", []) if c["id"] == "public_api"), None)
    if c is None or c["status"] in ("skipped", "error"):
        return None
    return bool(c.get("changed")) or c["status"] == "fail"


# --- supply chain (deps.delta, build.egress, craci.network: stage 1 treats the build as a witness) ----------

DEPS_CHECK = "deps.delta"
EGRESS_CHECKS = ("build.egress", "craci.network")


def allowed_dependencies(m: Mandate) -> list[str]:
    return [str(x) for x in (m.data.get("supply_chain") or {}).get("allowed_new_dependencies") or []]


def dep_allowed(entry: str, allowed: list[str]) -> bool:
    """`Name@1.2.3` is allowed if the mandate lists its name (any version) or name@version, case-insensitively."""
    allow = {a.strip().lower() for a in allowed}
    name = entry.rsplit("@", 1)[0]
    return entry.lower() in allow or name.lower() in allow


def deps_unallowed(facts: dict, allowed: list[str]) -> tuple[list[str], dict | None]:
    """(packages added or moved that the mandate does not allow, the package-feed change or None)."""
    c = check(facts, DEPS_CHECK) or {}
    entries = [str(e) for e in c.get("new_or_changed") or []]
    return [e for e in entries if not dep_allowed(e, allowed)], (c.get("build_inputs_changed") or {}).get("package_sources")


def deps_new_vulnerabilities(facts: dict) -> list[str]:
    """Advisories on head that base did not have, as `Package version severity GHSA-...`."""
    c = check(facts, DEPS_CHECK) or {}
    return [f"{v.get('package')} {v.get('version')} {v.get('severity')} {str(v.get('advisory', '')).rstrip('/').rsplit('/', 1)[-1]}"
            for v in c.get("vulnerabilities_new") or []]


def egress_violations(facts: dict) -> list[str]:
    """build.egress or craci.network at `fail`: the build tried to reach a host outside its network policy."""
    return [f"{cid}: {c.get('summary') or 'fail'}" for cid in EGRESS_CHECKS if (c := check(facts, cid)) and c.get("status") == "fail"]


# Build-time code that is not a NuGet package in project.assets.json: dotnet tools (run in CI), MSBuild SDKs and
# the SDK pin. deps.delta records them under build_inputs_changed (sbom.tree_inputs); the file list is the fallback
# when deps.delta did not run or did not record them (red team S2, S3).
BUILD_CODE_INPUTS = ("dotnet_tools", "msbuild_sdks", "sdk")
BUILD_CODE_FILES = ("dotnet-tools.json", "global.json")


def deps_check_problem(facts: dict) -> str | None:
    """deps.delta at fail or error: a package, feed, advisory or restore failure the graph could not account for
    (red team S7: a project that restores on base but not on head hides its packages)."""
    c = check(facts, DEPS_CHECK)
    if c is None or c.get("status") not in NOT_PASSING:
        return None
    return f"deps.delta {c['status']}: " + ("; ".join(map(str, c.get("fail_reasons") or [])) or c.get("summary") or "no reason recorded")


def build_code_changes(facts: dict) -> list[str]:
    """New or changed dotnet tools, MSBuild SDKs or SDK pin, from deps.delta's build_inputs_changed; when deps.delta
    did not record build inputs, any dotnet-tools.json / global.json in the diff. (Not covered: `Sdk="..."` attributes
    in project files, which sbom.tree_inputs does not record yet.)"""
    c = check(facts, DEPS_CHECK) or {}
    changed = c.get("build_inputs_changed") or {}
    out = []
    for k in BUILD_CODE_INPUTS:
        if k not in changed:
            continue
        b, h = (changed[k] or {}).get("base"), (changed[k] or {}).get("head")
        if isinstance(b, dict) or isinstance(h, dict):
            b, h = b or {}, h or {}
            diff = [f"{n} {b.get(n)} -> {h.get(n)}" for n in sorted(set(b) | set(h)) if b.get(n) != h.get(n)]
            out.append(f"{k}: " + ", ".join(diff))
        else:
            out.append(f"{k}: {b} -> {h}")
    if "build_inputs_changed" not in c:  # deps.delta did not run (or predates build inputs): read the file list
        out += [f"{f['path']} changed (not checked by deps.delta)" for f in files(facts) if f["path"].rsplit("/", 1)[-1].lower() in BUILD_CODE_FILES]
    return out


def _deps_changed_rule(ctx: dict) -> tuple[bool, str]:
    parts = list(filter(None, [deps_check_problem(ctx["facts"])])) + build_code_changes(ctx["facts"])
    return bool(parts), "; ".join(parts)


def _deps_unallowed_rule(ctx: dict) -> tuple[bool, str]:
    pkgs, sources = deps_unallowed(ctx["facts"], ctx.get("allowed_deps", []))
    parts = []
    if pkgs:
        parts.append(f"{', '.join(pkgs)} not in supply_chain.allowed_new_dependencies")
    if sources:
        parts.append(f"package feeds changed (base {sources.get('base')} -> head {sources.get('head')})")
    return bool(parts), "; ".join(parts)


def files(facts: dict) -> list[dict]:
    return facts.get("diff", {}).get("by_file", [])


# --- areas ------------------------------------------------------------------

def touched_areas(facts: dict, m: Mandate) -> list[dict]:
    by_area: dict[str, list[str]] = {}
    for f in files(facts):
        by_area.setdefault(m.area_for(f["path"]).name, []).append(f["path"])
    out = []
    for a in m.areas:  # mandate order
        if a.name in by_area:
            out.append({"name": a.name, "owner": a.owner, "sensitivity": a.sensitivity, "max_ai_tier": a.max_ai_tier,
                        "checks": a.checks, "files": by_area[a.name]})
    return out


def primary_area(areas: list[dict]) -> dict | None:
    return max(areas, key=lambda a: SENSITIVITY.index(a["sensitivity"]), default=None)


# --- requirement clauses ------------------------------------------------------

def required_reviewers(m: Mandate, panel: dict) -> list[str]:
    """Every participating reviewer must say met. `reviewers_required` may be `all_participating` (the default) or an
    explicit list, which is then narrowed to the reviewers the panel allows (confidentiality can only remove names)."""
    req = m["decision"].get("reviewers_required", "all_participating")
    return list(panel["reviewers"]) if req == "all_participating" else [n for n in req if n in panel["reviewers"]]


def decide_clauses(reqs: dict, reviews: dict, facts: dict, m: Mandate, required: list[str], untrusted: str | None = None) -> list[dict]:
    """Per clause: proven, held_before or refused (a would-be-proven clause whose tests kill no mutant: kill_gap). `untrusted` (set when injection_scan failed) is why no reviewer
    verdict counts on this change: every clause is then refused with `reviewers_untrusted`."""
    d = m["decision"]
    out = []
    for r in reqs.get("requirements", []):
        needed = list(dict.fromkeys(m["requirement_checks"].get(r.get("type", ""), []) + r.get("checks", [])))
        checks = [{"id": c, "status": check_status(facts, c)} for c in needed]
        reasons = []
        for c in checks:
            if c["status"] == "fail":
                reasons.append({"code": "check_failed", "detail": f"{c['id']} failed", "check": c["id"], "status": c["status"]})
            elif c["status"] != "pass":
                reasons.append({"code": "check_not_run", "detail": f"{c['id']} is {c['status']}", "check": c["id"], "status": c["status"]})
        verdicts = {}
        for name in required:
            given = [v for v in reviews.get(name, {}).get("requirement_verdicts", []) if v.get("req") == r["id"]]
            if len(given) > 1:  # first-wins would let a model put `met` first and `not_met` later: none of them counts
                reasons.append({"code": "missing_review", "detail": f"{name} gave {len(given)} verdicts for this clause; none counted",
                                "reviewer": name, "verdict": None, "duplicate": len(given)})
                continue
            v = given[0] if given else None
            if v is None:
                reasons.append({"code": "missing_review", "detail": f"{name} gave no verdict", "reviewer": name, "verdict": None})
                continue
            docs_checks(v, r, m)
            verdict = v.get("verdict") if v.get("verdict") in ("met", "not_met", "cannot_determine") else "cannot_determine"
            verdicts[name] = {"verdict": verdict, "basis": str(v.get("confidence_basis", "")),
                              "verified": v.get("substantive_count", 0), "verified_any": v.get("verified_count", 0),
                              "cited": len(v["evidence"]), "evidence": v["evidence"]}
        said = {n: v["verdict"] for n, v in verdicts.items()}
        for n, v in said.items():
            if v == "not_met":
                reasons.append({"code": "not_met", "detail": f"{n}: {verdicts[n]['basis']}", "reviewer": n, "verdict": v})
        if len(set(said.values())) > 1:
            reasons.append({"code": "reviewers_disagree", "detail": ", ".join(f"{n} says {v}" for n, v in said.items())})
        for n, v in said.items():
            if v == "cannot_determine":
                reasons.append({"code": "cannot_determine", "detail": f"{n}: {verdicts[n]['basis']}", "reviewer": n, "verdict": v})
            if v == "met" and verdicts[n]["verified"] < d["min_verified_evidence"]:
                reasons.append({"code": "thin_evidence", "detail": f"{n} says met with {verdicts[n]['verified']} verified evidence items about the change "
                                f"(of {verdicts[n]['cited']} cited; requirement quotes and unclaimed outcomes don't count)",
                                "reviewer": n, "verdict": v})
        if untrusted:
            reasons.append({"code": "reviewers_untrusted", "detail": untrusted})
        status = "refused" if reasons else "proven"
        held = held_before(r, verdicts, facts) if status == "proven" else None
        if held:
            status = "held_before"
            reasons.append({"code": "held_before", "detail": held["detail"], "tests": held["tests"]})
        # Proven also needs its tests to kill a mutant of the change (red team TT1). A clause already held_before is
        # not proven either: its tests pass without the fix, which says more than "they kill no mutant".
        gap = kill_gap(r, verdicts, facts) if status == "proven" else None
        if gap:
            status = "refused"
            reasons.append(gap)
        out.append({"id": r["id"], "type": r.get("type", ""), "text": r["text"], "checks": checks, "verdicts": verdicts,
                    "status": status, "reasons": reasons, **({"untrusted": True} if untrusted else {})})
    return out


def docs_checks(v: dict, req: dict, m: Mandate) -> None:
    """A docs clause has no code path or test to cite: a passing check the mandate requires for docs clauses
    (requirement_checks.docs, e.g. docs.anchors) counts on its own there. verify.py set such checks aside as
    "context only" (a check never counts alone); this puts them back for docs clauses only, so the R3 rule for code
    clauses is unchanged."""
    if req.get("type") != "docs":
        return
    mandated = set(m["requirement_checks"].get("docs", []))
    back = [e for e in v.get("evidence", []) if e.get("kind") == "check" and e.get("verified") and not e.get("substantive")
            and e.get("id") in mandated and e.get("context") and (e.get("status") or e.get("outcome"))]
    for e in back:
        e["substantive"] = True
        e["note"] = e["note"].split("; context only")[0] + "; counts: a check the mandate requires for docs clauses"
        del e["context"]
    if back:
        v["substantive_count"] = sum(bool(e.get("substantive")) for e in v["evidence"])


def held_before(req: dict, verdicts: dict, facts: dict) -> dict | None:
    """Met, but not achieved by this change: a relevant test that was also run with the source reverted (a
    `*fail_without_fix*` check) passed there.

    - If the clause lists its own `tests:` (owner-authored), they decide: held_before when every one of them that was
      run without the fix passed there. Reviewer citations can't add or remove a test from that judgement.
    - Otherwise the relevant tests are the new tests (`new: true` in that run) that EVERY reviewer cited with
      substantive evidence on this clause; held_before fires if any of them passes without the fix. One cited test
      that fails without the fix doesn't cancel another that passes (red team R7: citing an unrelated new test that
      fails on base used to hide that the clause's own test passes there).
    Existing tests passing on base are regression guards, not evidence that the clause held before ("no regressions"
    clauses should hold before), so they are not counted. No relevant test in a fail-without-fix run -> no judgement
    (None): absence of evidence is not `held_before`."""
    listed = list(req.get("tests") or [])
    if listed:
        names = set(listed)
    else:
        cited = [{e["name"] for e in v["evidence"] if e.get("kind") == "test" and e.get("substantive", e.get("verified"))}
                 for v in verdicts.values()]
        names = set.intersection(*cited) if cited else set()
    without: dict[str, set] = {}
    for c in facts.get("checks", []):
        if "fail_without_fix" in c["id"]:
            for t in c.get("tests", []):
                if t["name"] in names and (listed or t.get("new") is True):
                    without.setdefault(t["name"], set()).add(t["outcome"])
    if listed:
        held = sorted(without) if without and all(outs == {"passed"} for outs in without.values()) else []
    else:
        held = sorted(n for n, outs in without.items() if outs == {"passed"})
    if not held:
        return None
    if listed:
        detail = f"all {len(held)} of the clause's tests that were run without the fix pass there too: "
    else:
        detail = f"{len(held)} of the {len(without)} new test(s) every reviewer cited that were run without the fix pass there too: "
    return {"tests": held, "detail": detail + ", ".join(t.rsplit(".", 1)[-1] for t in held)}


MUTATION_CHECK = "tests.mutation"


def kill_gap(req: dict, verdicts: dict, facts: dict) -> dict | None:
    """Red team TT1 (test theater): a test can fail without the fix for a reason unrelated to the clause (it reflects
    on a method the fix renamed), so fail-without-fix alone does not show the test checks what the clause asks.
    Stage 1's `tests.mutation` mutates the change's own source lines and records which new test killed which mutant.

    A clause whose support includes tests needs at least one of them to have killed a mutant, on the hunks the clause
    depends on: those holding a changed line its reviewers cite as verified code evidence, or any hunk of the change
    when they cite none that was mutated. Its tests are the clause's `tests:` if listed (owner-authored), else the new
    tests its reviewers cite with substantive evidence; a functional clause citing no new test is judged on all of
    the change's new tests (a behaviour change has to be shown by some test). Otherwise: `tests_kill_no_mutant`.
    No judgement (None) when the check did not run (absent, skipped, error) or a non-functional clause cites no test."""
    mc = check(facts, MUTATION_CHECK)
    if mc is None or mc.get("status") not in ("pass", "fail") or not mc.get("mutants"):
        return None
    judged = [t["name"] for t in mc.get("kills_by_test", [])]
    listed = list(req.get("tests") or [])
    if listed:
        support, basis = listed, "the clause's tests"
    else:
        cited = {e["name"] for v in verdicts.values() for e in v["evidence"] if e.get("kind") == "test" and e.get("substantive", e.get("verified"))}
        support, basis = [t for t in judged if t in cited], "the new tests its reviewers cite"
        if not support:
            if req.get("type") != "functional" or not judged:
                return None
            support, basis = judged, "the change's new tests (the reviewers cite none)"
    hunks = {h["id"]: h for h in mc.get("hunks", [])}
    lines = {(e.get("file"), e.get("line")) for v in verdicts.values() for e in v["evidence"]
             if e.get("kind") == "code" and e.get("verified") and e.get("rev", "head") == "head"}
    near = sorted(h["id"] for h in hunks.values() if h.get("status") != "not_mutated"
                  and any(f == h["file"] and isinstance(n, int) and h["lines"][0] <= n <= h["lines"][1] for f, n in lines))
    killed = {t["name"]: set(t.get("killed", [])) for t in mc.get("kills_by_test", [])}
    mutants = {m["id"]: m for m in mc["mutants"]}
    scope = set(near) or set(hunks)
    kills = sorted({m for t in support for m in killed.get(t, set()) if mutants.get(m, {}).get("hunk") in scope})
    if kills:
        return None
    loc = lambda h: f"{h['file'].rsplit('/', 1)[-1]}:{h['lines'][0]}" + (f"-{h['lines'][1]}" if h["lines"][1] != h["lines"][0] else "")  # noqa: E731
    where = f"its lines ({', '.join(loc(hunks[i]) for i in near)})" if near else "any changed line"
    short = lambda ts: ", ".join(t.rsplit(".", 1)[-1] for t in ts)  # noqa: E731
    ran = [t for t in support if t in killed]
    if not ran:
        detail = f"the tests supporting {req['id']} ({short(support)}) were not run against the mutants in {MUTATION_CHECK}"
    else:
        others = sorted({t for t, ms in killed.items() if t not in support and any(mutants.get(m, {}).get("hunk") in scope for m in ms)})
        n_scope = sum(m.get("hunk") in scope for m in mc["mutants"])
        detail = (f"the tests supporting {req['id']} ({basis}: {short(support)}) kill no mutant on {where} in {MUTATION_CHECK}; "
                  + (f"the mutants there are killed by other tests ({short(others)})" if others else
                     f"no test kills any of the {n_scope} mutant(s) there"))
    return {"code": "tests_kill_no_mutant", "detail": detail, "check": MUTATION_CHECK, "tests": sorted(support), "hunks": near}


# --- reviewer refusals ---------------------------------------------------------------

def classify_refusal(r: dict, reqs: dict, areas: list[dict], clauses: list[dict], m: Mandate) -> tuple[str, str]:
    """A refusal routes `decision.reviewer_refusal_tier` (ask) if it names a requirement clause (`req`), is marked
    `blocking: true` by the reviewer, or its topic names a check the change's areas or clauses mandate, or a term
    from the mandate's `refusal_ask_terms` (security, public API, runtime, ...). Otherwise it is out of scope: shown,
    in residual risk, and it routes `decision.out_of_scope_refusal_tier` (notify), so the owner is still told."""
    d = m["decision"]
    ask, other = d["reviewer_refusal_tier"], d.get("out_of_scope_refusal_tier", d["reviewer_refusal_tier"])
    ids = {x["id"] for x in reqs.get("requirements", [])}
    if r.get("req") in ids:
        return ask, f"names requirement clause {r['req']}"
    if r.get("blocking"):
        return ask, "marked blocking by the reviewer"
    topic = str(r.get("topic", "")).lower()
    issue = str(reqs.get("change", "")).split("-")[0]
    if issue.isdigit() and re.search(rf"#{issue}\b|issue {issue}\b", topic) or re.search(r"\b(resolves?|fix(es)?) (the |this )?(reported )?issue\b", topic):
        return ask, "asks whether the change resolves its own issue (the requirement's root)"
    mandated ={c for a in areas for c in a["checks"]} | {x["id"] for c in clauses for x in c["checks"]}
    hit = [c for c in sorted(mandated) if re.search(rf"(?<![\w.]){re.escape(c.lower())}(?![\w.])", topic)]
    if hit:
        return ask, f"topic names mandated check {hit[0]}"
    term = next((t for t in d.get("refusal_ask_terms", []) if t.lower() in topic), None)
    if term:
        return ask, f"topic touches '{term}' (mandate refusal_ask_terms)"
    return other, "out of scope: names no clause, not marked blocking, touches no mandated check or sensitive term"


# --- disputes and the adjudicator ---------------------------------------------------

def disputes(clauses: list[dict], findings: list[dict]) -> list[dict]:
    """What the adjudicator may look at: clauses where participating reviewers gave different verdicts, and
    blocker/major findings that no other reviewer corroborated (no shared anchor). Ids are stable across runs."""
    out = []
    for c in clauses:
        said = {n: v["verdict"] for n, v in c["verdicts"].items()}
        if len(set(said.values())) > 1:
            out.append({"id": c["id"], "kind": "clause", "about": c["id"], "text": c["text"],
                        "sides": [{"reviewer": n, "verdict": v["verdict"], "basis": v["basis"], "evidence": v["evidence"]}
                                  for n, v in c["verdicts"].items()]})
    for f in findings:
        if f["severity"] not in ("blocker", "major"):
            continue
        others = [g for g in findings if g["reviewer"] != f["reviewer"]]
        if any(_anchors(f) & _anchors(g) for g in others if g["status"] == "verified") and f["status"] == "verified":
            continue  # corroborated by another reviewer: not in dispute
        out.append({"id": f"finding:{f['reviewer']}:{f['id']}", "kind": "finding", "about": f"{f['reviewer']}:{f['id']}",
                    "text": f"{f['title']}: {f['claim']}",
                    "sides": [{"reviewer": f["reviewer"], "verdict": f"{f['severity']} finding ({f['status']})", "basis": f["claim"],
                               "evidence": f["evidence"]}],
                    "not_raised_by": sorted({g["reviewer"] for g in others} or [])})
    return out


def apply_adjudication(clauses: list[dict], adjudication: dict | None, current: list[dict]) -> list[dict]:
    """HARD RULE: the adjudicator can only add reasons and route to a human; it can never clear anything.

    - A clause's status is never moved towards `proven`: a refused clause stays refused whatever the adjudicator says
      (even if it writes "met", "proven" or "supported" for every claim).
    - An adjudicated dispute about a clause adds the reason `adjudicator_dispute` (so a clause that is somehow proven
      while the adjudicator disputes it becomes refused, never the reverse).
    - Every adjudicated dispute becomes a tier driver at `ask` (source `adjudicator`): a human looks at it.
    Returns the tier drivers it adds. Rulings on items that are no longer in dispute are kept in the pack as `stale`."""
    if not adjudication:
        return []
    before = {c["id"]: c["status"] for c in clauses}
    live = {d["id"] for d in current}
    drivers = []
    for r in adjudication.get("rulings", []):
        did = str(r.get("dispute", ""))
        r["stale"] = did not in live
        if r["stale"]:
            continue
        summary = _short_ruling(r)
        c = next((c for c in clauses if c["id"] == did), None)
        if c is not None:
            c.setdefault("adjudication", r)
            c["reasons"].append({"code": "adjudicator_dispute", "detail": f"{adjudication.get('reviewer', 'adjudicator')}: {summary}"})
            c["status"] = "refused"
        drivers.append({"source": "adjudicator", "id": did, "tier": "ask", "why": summary})
    for c in clauses:  # the rule, checked: nothing the adjudicator said may turn a refused clause into proven
        assert not (before[c["id"]] == "refused" and c["status"] == "proven"), f"adjudicator cleared {c['id']}"
    return drivers


def _short_ruling(r: dict) -> str:
    sup = [x.get("reviewer", "?") for x in r.get("supported", [])]
    uns = [x.get("reviewer", "?") for x in r.get("unsupported", [])]
    settle = "; ".join(r.get("evidence_that_would_settle", [])[:2])
    return (f"supported by cited evidence: {', '.join(sup) or 'none'}; not supported: {', '.join(uns) or 'none'}"
            + (f"; would settle it: {settle}" if settle else ""))


# --- findings -----------------------------------------------------------------

def _anchors(f: dict) -> set:
    """What a verified finding points at: (file, line bucket) for code, the id for checks/tests."""
    out = set()
    for e in f["evidence"]:
        if e["verified"]:
            if e["kind"] == "code":
                out |= {(e["file"], e["line"] // 10), (e["file"], (e["line"] + 5) // 10)}
            elif e["kind"] in ("check", "test"):
                out.add((e["kind"], e.get("id") or e.get("name")))
    return out


def _same_evidence(a: dict, b: dict) -> bool:
    """Two verified items that point at the same thing: the same code quote in the same file, or the same test."""
    if not (a.get("verified") and b.get("verified")) or a.get("kind") != b.get("kind"):
        return False
    if a["kind"] == "code":
        return a.get("file") == b.get("file") and " ".join(str(a.get("quote", "")).split()) == " ".join(str(b.get("quote", "")).split())
    if a["kind"] == "test":
        return a.get("name") == b.get("name")
    return False


def carry_forward(reviews: dict, earlier: dict | None, facts: dict | None = None) -> tuple[list[dict], list[dict]]:
    """Failure mode R6: a later pass may not silently drop a finding. For each reviewer's earlier passes
    (reviews/<n>/<reviewer>.v<k>.json, verified), every verified blocker/major finding stays open as
    `carried_forward` unless the reviewer's current pass re-raises it: a current finding cites a piece of the same
    verified evidence (same code quote in the same file, or the same test).

    A refutation (an entry in `refutations[]`, or a finding with `refutes:`, that names the earlier finding id and
    cites verified evidence at the same location) only annotates: a reviewer's word can open a finding, not close one
    (red team R6: re-quoting the line the finding quoted used to clear it). The finding stays open, at its tier (ask
    for blocker/major), until the pipeline's repro for it (`repro.<reviewer>.<id>`) ran and did not reproduce it, or
    the owner closes it at sign-off. Returns (carried findings, refuted findings): carried ones are verified findings
    with id `<pass>.<id>`; each refuted entry says whether the refutation closed it (`closed`)."""
    carried, refuted = [], []
    for name, passes in (earlier or {}).items():
        cur = reviews.get(name)
        if cur is None:
            continue
        cur_f = cur.get("findings", [])
        refs = list(cur.get("refutations", [])) + [{**f, "finding": f["refutes"]} for f in cur_f if f.get("refutes")]
        seen: list[dict] = []
        for pass_name, old in passes:  # newest first
            for f in old.get("findings", []):
                if f.get("status") != "verified" or f["severity"] not in ("blocker", "major"):
                    continue
                if any(_same_evidence(a, b) for g in cur_f for a in f["evidence"] for b in g.get("evidence", [])):
                    continue  # re-raised
                if any(_same_evidence(a, b) for g in seen for a in f["evidence"] for b in g["evidence"]):
                    continue  # already carried from a newer earlier pass
                ref = next((x for x in refs if str(x.get("finding", "")).split(".")[-1] == f["id"]
                            and _anchors(f) & _anchors({"evidence": x.get("evidence", [])})), None)
                why = f"{name}'s current pass neither re-raised it nor refuted it with verified evidence, so it stays open"
                if ref is not None:
                    repro = check(facts or {}, f"{REPRO_PREFIX}{name}.{f['id']}") or {}
                    closed = repro.get("status") == "fail"
                    refuted.append({"reviewer": name, "id": f"{pass_name}.{f['id']}", "title": f["title"],
                                    "refuted_by": ref.get("id") or "refutation", "reason": ref.get("reason") or ref.get("claim", ""),
                                    "evidence": [e for e in ref.get("evidence", []) if e.get("verified")], "closed": closed,
                                    "closed_by": f"{repro['id']} did not reproduce it" if closed else None})
                    if closed:
                        continue
                    why = (f"{name} refuted it ({ref.get('reason') or ref.get('claim', '')}), but a refutation only annotates: it stays "
                           f"open until the pipeline's repro ({REPRO_PREFIX}{name}.{f['id']}) fails to reproduce it or the owner closes it at sign-off")
                c = {**f, "id": f"{pass_name}.{f['id']}", "reviewer": name, "carried_forward": {
                    "from": f"{name}.{pass_name}.json", "pass": pass_name, "original_id": f["id"], "why": why,
                    **({"refuted_by": ref.get("id") or "refutation"} if ref is not None else {})}}
                if ref is not None:
                    c["tier_reason"] = "refuted by the reviewer without a pipeline repro: a human closes it"
                carried.append(c)
                seen.append(f)
    return carried, refuted


def attach_repro(f: dict, facts: dict) -> None:
    """Executable repros (stage 1 adds `repro.<reviewer>.<finding-id>` checks): pass = the pipeline reproduced the
    defect as claimed, fail = it didn't. A finding gets the repro named after it, or any repro check it cites."""
    ids = [f"{REPRO_PREFIX}{f.get('reviewer')}.{f.get('carried_forward', {}).get('original_id', f['id'])}"]
    ids += [e.get("id") for e in f.get("evidence", []) if e.get("kind") == "check" and is_repro(e.get("id", ""))]
    for cid in dict.fromkeys(ids):
        c = check(facts, cid)
        if c is None:
            continue
        status = {"pass": "reproduced", "fail": "not_reproduced"}.get(c["status"], "repro_not_run")
        runs = {r.get("label") or r.get("rev"): r.get("outcome") for r in c.get("runs", []) if isinstance(r, dict)}
        # the defect shows on base the same way it shows on head: real, but not introduced by this change
        before = status == "reproduced" and runs.get("base") is not None and runs.get("base") == runs.get("head")
        f["repro"] = {"check": cid, "status": status, "check_status": c["status"], "summary": c.get("summary", ""),
                      "present_before": before, "runs": runs,
                      "label": {"reproduced": "reproduced" + ("; also present before this change" if before else ""),
                                "not_reproduced": "not reproduced", "repro_not_run": f"repro {c['status']}"}[status]}
        if status == "reproduced":
            break


def grade_findings(reviews: dict, facts: dict, m: Mandate, carried: list[dict] | None = None) -> list[dict]:
    d = m["decision"]
    all_f = [f for r in reviews.values() for f in r.get("findings", [])] + list(carried or [])
    for f in all_f:
        attach_repro(f, facts)
        repro = f.get("repro", {}).get("status")
        if repro == "reproduced" and f["status"] != "verified":
            f["status"], f["verified_by"] = "verified", "repro"  # the pipeline reproduced it: strongest evidence there is
        f["tier"] = d["finding_tiers"][f["severity"]] if f["status"] == "verified" else "silent"
        if f["status"] == "verified" and f.get("carried_forward", {}).get("refuted_by"):
            f["tier"] = strictest(f["tier"], "ask")  # R6: a refuted finding stays with a human until a repro or the owner closes it
        f["confirmed_by"] = []
        if repro == "not_reproduced" and f["status"] == "verified":
            # Labelled, not demoted: the label adds no routing of its own, and a repro the pipeline could not make work
            # does not argue away the reviewer's other verified evidence (the finding keeps its severity tier).
            f["tier_reason"] = f"not reproduced by the pipeline ({f['repro']['check']} failed); routed on its other verified evidence"
        if repro == "reproduced" and f["status"] == "verified":
            f["tier_reason"] = f"reproduced by the pipeline ({f['repro']['check']})"
            if f["severity"] == "blocker":
                f["tier"] = d["blocker_confirmed_tier"]
            continue
        if f["status"] != "verified" or f["severity"] != "blocker":
            continue
        others = [g for g in all_f if g["reviewer"] != f["reviewer"] and g["status"] == "verified" and g["severity"] == "blocker"]
        f["confirmed_by"] = sorted({g["reviewer"] for g in others if _anchors(f) & _anchors(g)})
        failing = [e for e in f["evidence"] if e["verified"] and (
            (e["kind"] == "check" and not is_repro(e["id"]) and check_status(facts, e["id"]) == "fail")
            or (e["kind"] == "test" and e.get("outcome") == "failed"))]
        if f["confirmed_by"] or failing:
            f["tier"] = d["blocker_confirmed_tier"]
            f["tier_reason"] = ("confirmed by " + ", ".join(f["confirmed_by"])) if f["confirmed_by"] else "backed by a failing check"
    return all_f


# --- hard rules (predicate name in the mandate -> function) ---------------------

def _mandated(ctx):
    return [(c, a["name"], check_status(ctx["facts"], c)) for a in ctx["areas"] for c in a["checks"]]


RULES = {
    "files_changed_gt": lambda ctx, n: (ctx["facts"]["diff"]["files"] > n, f"{ctx['facts']['diff']['files']} files changed"),
    "generated_files_gt": lambda ctx, n: (len(ctx["generated"]) > n, f"{len(ctx['generated'])} generated files"),
    "public_api_changed": lambda ctx, _: (public_api_changed(ctx["facts"]) is True,
                                          next((c.get("summary", "") for c in ctx["facts"].get("checks", []) if c["id"] == "public_api"), "")),
    "source_without_tests": lambda ctx, _: (bool(ctx["source"]) and not ctx["tests"],
                                            f"{len(ctx['source'])} source files, {len(ctx['tests'])} test files changed"),
    "mandated_check_failed": lambda ctx, _: (any(s == "fail" for *_, s in _mandated(ctx)),
                                             "; ".join(f"{c} ({a}): fail" for c, a, s in _mandated(ctx) if s == "fail")),
    "mandated_check_missing": lambda ctx, _: (any(s not in ("pass", "fail") for *_, s in _mandated(ctx)),
                                              "; ".join(f"{c} ({a}): {s}" for c, a, s in dict.fromkeys(_mandated(ctx)) if s not in ("pass", "fail"))),
    "mandate_unsigned": lambda ctx, _: (not ctx["mandate_sig"]["valid"], ctx["mandate_sig"]["reason"]),
    "injection_found": lambda ctx, _: (injection_found(ctx["facts"]), "; ".join(injection_lines(ctx["facts"]))),
    "injection_unscannable": lambda ctx, _: (injection_unscannable(ctx["facts"]), "; ".join(injection_lines(ctx["facts"]))),
    "generated_hand_edited": lambda ctx, _: (bool(generated_hand_edited(ctx["facts"])),
                                             ", ".join(generated_hand_edited(ctx["facts"])) + " (generated-looking, its input unchanged)"),
    # supply chain: only stricter routing, never a pass (deps.delta stays out of the areas' mandated checks)
    "deps_unallowed": lambda ctx, _: _deps_unallowed_rule(ctx),
    "deps_new_vulnerability": lambda ctx, _: (bool(deps_new_vulnerabilities(ctx["facts"])), "; ".join(deps_new_vulnerabilities(ctx["facts"]))),
    "egress_violation": lambda ctx, _: (bool(egress_violations(ctx["facts"])), "; ".join(egress_violations(ctx["facts"]))),
    # deps.delta at fail/error, or new/changed dotnet tools, MSBuild SDKs or SDK pin (red team S2, S3, S7)
    "deps_check_failed": lambda ctx, _: _deps_changed_rule(ctx),
}


def fire_rules(ctx: dict, m: Mandate) -> list[dict]:
    fired = []
    for rule in m["rules"]:
        hit, evidence = RULES[rule["when"]](ctx, rule.get("value"))
        if hit:
            fired.append({**rule, "evidence": evidence})
    return fired


# --- risk score ---------------------------------------------------------------

def size_points(x: float, w: dict) -> float:
    """Points for the size of a change, smooth in x (no cliff to stay one file under): `per` points per unit while
    the change is small, bending logarithmically past `knee` points, at most `cap`. v6 (red team G4): a linear rate
    with a low cap gave 49 files the same points as 20, so only the >50 split rule saw size at all."""
    return round(min(w["knee"] * math.log1p(w["per"] * x / w["knee"]), w["cap"]), 1)


def size_rule(w: dict, unit: str) -> str:
    return f"~{w['per']} per {unit} while small, log-scaled past {w['knee']}, cap {w['cap']}"


def risk_score(ctx: dict, clauses: list[dict], m: Mandate) -> dict:
    w, facts = m["risk"], ctx["facts"]
    prim = primary_area(ctx["areas"])
    n_files = facts["diff"]["files"]
    lines = sum(f.get("ins", 0) + f.get("del", 0) for f in files(facts) if f.get("kind") != "generated")
    sec = [f["path"] for f in files(facts) if matches(f["path"], m["security_sensitive_paths"])]
    api = public_api_changed(facts)
    fwf = check_status(facts, "tests.fail_without_fix")
    disagree = [c["id"] for c in clauses if any(r["code"] == "reviewers_disagree" for r in c["reasons"])]
    failed = [c["id"] for c in facts.get("checks", []) if c["status"] == "fail" and c["id"] != "public_api" and not is_repro(c["id"])]

    def capped(points, cap):
        return round(min(points, cap), 1)

    files_pts = size_points(n_files, w["files"])
    lines_pts = round(min(size_points(lines / 100, w["lines"]), max(0.0, w["size_cap"] - files_pts)), 1)

    factors = [
        ("area_sensitivity", w["sensitivity_points"][prim["sensitivity"]] if prim else 0,
         f"most sensitive area touched: {prim['name']} ({prim['sensitivity']})" if prim else "no files mapped"),
        ("files_changed", files_pts, f"{n_files} files ({size_rule(w['files'], 'file')})"),
        ("lines_changed", lines_pts, f"{lines} non-generated lines ({size_rule(w['lines'], '100 lines')}; "
                                     f"files and lines together at most {w['size_cap']})"),
        ("generated_files", capped(len(ctx["generated"]) * w["per_generated_file"], w["generated_cap"]),
         f"{len(ctx['generated'])} generated files x {w['per_generated_file']} (cap {w['generated_cap']})"),
        ("public_api_change", w["public_api_change"] if api is not False else 0,
         {True: "public API changed", False: "public_api check: no change", None: "public API not checked (counted as changed)"}[api]),
        ("source_without_tests", w["source_without_tests"] if ctx["source"] and not ctx["tests"] else 0,
         "source changed, no test changed" if ctx["source"] and not ctx["tests"] else "tests changed alongside source" if ctx["source"] else "no source changed"),
        ("security_sensitive_paths", w["security_sensitive_path"] if sec else 0, ", ".join(sec) or "none touched"),
        # Only a source change has a fix to show. A skipped check is still not a pass: on a docs/tests-only change the
        # factor is 0 because there is nothing to revert, and the clause/area rules still treat `skipped` as not run.
        ("fail_without_fix_not_shown", w["fail_without_fix_not_shown"] if fwf != "pass" and ctx["source"] else 0,
         f"tests.fail_without_fix: {fwf}" + ("" if ctx["source"] else " (no source changed: nothing to revert)")),
        ("reviewer_disagreement", len(disagree) * w["per_reviewer_disagreement"],
         f"{len(disagree)} clause(s) x {w['per_reviewer_disagreement']}" + (f": {', '.join(disagree)}" if disagree else "")),
        ("failed_checks", len(failed) * w["per_failed_check"], f"{len(failed)} failed check(s) x {w['per_failed_check']}" + (f": {', '.join(failed)}" if failed else "")),
    ]
    score = round(sum(p for _, p, _ in factors), 1)
    tier = "silent"
    for t in TIERS[1:]:
        if score >= w["thresholds"][t]:
            tier = t
    return {"score": score, "tier": tier, "thresholds": w["thresholds"],
            "factors": [{"factor": f, "points": p, "reason": r} for f, p, r in factors]}


# --- the whole decision -------------------------------------------------------

def decide(facts: dict, reviews: dict, reqs: dict, m: Mandate, mandate_sig: dict, caps: dict,
           panel: dict | None = None, adjudication: dict | None = None, earlier: dict | None = None) -> dict:
    """`reviews` are verified reviews; `caps` maps area -> {"cap", "reason"} from the trust ledger.
    `panel` (from Mandate.panel) says who participates; reviews from anyone else are ignored.
    `adjudication` is the adjudicator's output: it can only add reasons and drivers (apply_adjudication).
    `earlier` maps reviewer -> [(pass name, verified review), ...] newest first: their open findings carry forward."""
    d = m["decision"]
    areas = touched_areas(facts, m)
    panel = panel or m.panel([a["name"] for a in areas])
    reviews = {n: r for n, r in reviews.items() if n in panel["reviewers"]}
    by_kind = lambda k: [f["path"] for f in files(facts) if f.get("kind") == k]  # noqa: E731
    ctx = {"facts": facts, "areas": areas, "mandate_sig": mandate_sig, "allowed_deps": allowed_dependencies(m),
           "generated": by_kind("generated"), "source": by_kind("source"), "tests": by_kind("test")}
    untrusted = None
    if injection_found(facts):
        untrusted = ("injection_scan found text addressed to automated reviewers in the change, so reviewers saw planted "
                     "instructions and their verdicts don't count: " + "; ".join(injection_lines(facts)))
    clauses = decide_clauses(reqs, reviews, facts, m, required_reviewers(m, panel), untrusted)
    carried, refuted = carry_forward(reviews, earlier, facts)
    findings = grade_findings(reviews, facts, m, carried)
    open_disputes = disputes(clauses, findings)
    adj_drivers = apply_adjudication(clauses, adjudication, open_disputes)
    rules = fire_rules(ctx, m)
    risk = risk_score(ctx, clauses, m)
    refusals = [{**r, "reviewer": name, "model": rev.get("model")} for name, rev in reviews.items() for r in rev.get("refusals", [])]
    for r in refusals:
        r["routes"], r["route_reason"] = classify_refusal(r, reqs, areas, clauses, m)

    bands = ", ".join(f"{t}>={v}" for t, v in risk["thresholds"].items())
    top = sorted((f for f in risk["factors"] if f["points"]), key=lambda f: -f["points"])[:3]
    top_s = " + ".join(f"{f['factor']} {f['points']}" for f in top)
    drivers = [{"source": "risk score", "id": "risk", "tier": risk["tier"], "why": f"score {risk['score']} ({bands}); largest: {top_s}"}]
    drivers += [{"source": "mandate rule", "id": r["id"], "tier": r["tier"], "why": f"{r['message']} [{r['evidence']}]"} for r in rules]
    for a in areas:
        c = caps.get(a["name"], {"cap": a["max_ai_tier"], "reason": "mandate clearance right"})
        a["cap"], a["cap_reason"] = c["cap"], c["reason"]
        drivers.append({"source": "trust cap", "id": a["name"], "tier": c["cap"], "why": f"{a['name']}: AI may clear at most to {c['cap']} ({c['reason']})"})
    drivers += [{"source": "refused clause", "id": c["id"], "tier": d["refused_clause_tier"], "codes": [r["code"] for r in c["reasons"]],
                 "why": "; ".join(f"{r['code']}: {r['detail']}" for r in c["reasons"])} for c in clauses if c["status"] == "refused"]
    drivers += [{"source": "held before", "id": c["id"], "tier": d.get("held_before_tier", "notify"),
                 "why": f"met, but not achieved by this change: {c['reasons'][-1]['detail']}"} for c in clauses if c["status"] == "held_before"]
    drivers += adj_drivers
    drivers += [{"source": "reviewer refusal", "id": f"{r['reviewer']}", "tier": r["routes"],
                 "why": f"{r['topic']} ({r['reason']})" + ("" if r["routes"] == d["reviewer_refusal_tier"] else f" [{r['route_reason']}]")}
                for r in refusals]
    drivers += [{"source": "verified finding", "id": f"{f['reviewer']}:{f['id']}", "tier": f["tier"],
                 "why": f"{f['severity']}: {f['title']}" + (f" ({f['tier_reason']})" if f.get("tier_reason") else "")}
                for f in findings if f["status"] == "verified" and f["tier"] != "silent"]

    gate = principle_zero(clauses, areas, facts)
    if gate:
        drivers.append({"source": "failing check", "id": "principle-0", "tier": "ask",
                        "why": "a mandated check failed or errored; no verdict, adjudication or trust can clear the change [" + "; ".join(gate) + "]"})

    drivers.sort(key=lambda x: (-TIERS.index(x["tier"]), SOURCE_ORDER.index(x["source"])))
    tier = strictest("silent", *(x["tier"] for x in drivers))
    assert not gate or tier in ("ask", "block"), "principle 0: a failing mandated check was cleared"
    prim = primary_area(areas)
    return {
        "tier": tier,
        "decisive": [x for x in drivers if x["tier"] == tier],
        "drivers": drivers,
        "primary_area": prim["name"] if prim else None,
        "owner": prim["owner"] if prim else m["owner"],
        "notify": sorted({a["owner"] for a in areas} - {prim["owner"] if prim else m["owner"]}),
        "areas": areas,
        "clauses": clauses,
        "findings": findings,
        "reviewer_refusals": refusals,
        "rules_fired": rules,
        "risk": risk,
        "panel": panel,
        "disputes": open_disputes,
        "carried_forward": [f"{f['reviewer']}:{f['id']}" for f in carried],
        "refuted": refuted,
        "reproduced": {f"{f['reviewer']}:{f['id']}": f["repro"]["status"] for f in findings if f.get("repro")},
        "reviewers_untrusted": ({"rule": "R-INJECT", "reviewers": sorted(reviews), "why": untrusted, "lines": injection_lines(facts)}
                                if untrusted else None),
        "principle_zero": gate,
    }


def principle_zero(clauses: list[dict], areas: list[dict], facts: dict) -> list[str]:
    """Principle 0: a failing check can't be argued away. Lists every mandated check (an area's `checks`, or a
    clause's checks) whose status is fail or error, and asserts no such clause is proven or held_before. The
    caller adds an `ask` floor that no trust cap or verdict can lower (the mandate's own rules may block)."""
    bad = [f"{c} ({a['name']}): {check_status(facts, c)}" for a in areas for c in a["checks"] if check_status(facts, c) in NOT_PASSING]
    for c in clauses:
        failing = [x for x in c["checks"] if x["status"] in NOT_PASSING]
        assert not (failing and c["status"] in ("proven", "held_before")), f"principle 0: {c['id']} proven with a failing check"
        bad += [f"{x['id']} ({c['id']}): {x['status']}" for x in failing]
    return list(dict.fromkeys(bad))
