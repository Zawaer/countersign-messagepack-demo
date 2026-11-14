"""Stage 7: per-area trust stages, derived only from signed ledger events (no hidden state).

The ladder is ask -> notify -> silent (the AI's clearance right in an area), never above the area's max_ai_tier.
The mandate's `trust.stages` table says what each stage needs; this module only applies it:

- Start: each area is at its mandate cap (the owner delegated that right when signing the mandate).
- Drop one stage (never below ask), and restart probation, on: an escape on a change the AI cleared, a
  disagreeing spot-check, or a canary run (seeded defects sent through the panel) where the panel missed one.
- Climb one stage (never above the mandate cap) when the next stage's entry requirements hold: N agreeing
  spot-checks in a row since the last drop or climb, at least X% agreement over the last W spot-checks, and no
  escape in the area's last Y changes (signoffs + spot-checks).
- Release gate: the stage was earned by specific reviewer versions (model + prompt_version): the ones in the
  signed registry, plus any that passed the seeded-defect set in a `canary` event. If a current reviewer runs a
  version that did neither, every area is held at `ask` until it does.

Events: `spotcheck`, `escape` and `canary` ledger entries; each records the reviewer versions it was made with.
Which events count (mandate v5, red team L1-L3):
- Routing uses the ledger only after `ledger.verify` passes (hash chain, signatures); otherwise no event is used
  and every area is at ask, with the reason (`verified`).
- A canary releases a reviewer version only if it lists every id of `release_gate.seeded_set`, claims that many
  seeded, and caught at least `min_catch_rate` of them.
- A spot-check counts only if its signer owns the area, and once per pack (`pack_sha256`); others are ignored and
  the area history says why.
"""

from __future__ import annotations

from . import ledger
from .common import TIERS, strictest
from .mandate import Mandate

LADDER = ["ask", "notify", "silent"]  # strictest first; `block` is never a trust stage


def _down(tier: str) -> str:
    """One stage stricter, never past ask."""
    return LADDER[max(0, LADDER.index(tier) - 1)] if tier in LADDER else "ask"


def _up(tier: str, cap: str) -> str | None:
    """One stage more lenient, never past the area's mandate cap. None if already there."""
    if tier not in LADDER or cap not in LADDER or LADDER.index(tier) >= LADDER.index(cap):
        return None
    return LADDER[LADDER.index(tier) + 1]


def stages(m: Mandate) -> dict[str, dict]:
    """The entry requirements per stage. `restore_after_agreeing_spotchecks` (not in the signed mandate) is a
    what-if override of N for every stage, used by the simulation."""
    t = m["trust"]
    out = {k: dict(v or {}) for k, v in t.get("stages", {}).items()}
    if t.get("restore_after_agreeing_spotchecks"):
        for k in out:
            if k != "ask":
                out[k]["agreeing_spotchecks"] = t["restore_after_agreeing_spotchecks"]
    return out


def version_key(name: str, r: dict) -> tuple[str, str, str]:
    return (name, str(r.get("model")), str(r.get("prompt_version")))


def seeded_set(m: Mandate) -> list[str]:
    """The seeded-defect ids a canary must cover to release a reviewer version (trust.release_gate.seeded_set)."""
    s = m["trust"].get("release_gate", {}).get("seeded_set") or []
    return [str(x) for x in s] if isinstance(s, list) else []


def canary_release(m: Mandate, p: dict) -> tuple[bool, str]:
    """Does this canary payload pass the release gate? It must name every id of the mandate's seeded set (`defects`),
    claim exactly that many seeded, and catch at least min_catch_rate of them (`missed` ids count against it)."""
    gate = m["trust"].get("release_gate", {})
    want = seeded_set(m)
    if not want:
        return False, "the mandate lists no seeded set, so no canary can release a reviewer version"
    ran = {str(x) for x in p.get("defects") or []}
    missing = [x for x in want if x not in ran]
    if missing:
        return False, (f"covers {len(want) - len(missing)} of the {len(want)} seeded defects the mandate lists "
                       f"(missing {', '.join(missing[:3])}{', ...' if len(missing) > 3 else ''})")
    seeded = p.get("seeded")
    if seeded != len(want):
        return False, f"claims {seeded} seeded, but the mandate's set has {len(want)}"
    missed = {str(x) for x in p.get("missed") or []} & set(want)
    try:
        caught = min(int(p.get("caught", 0)), len(want) - len(missed))
    except (TypeError, ValueError):
        return False, f"caught is not a number ({p.get('caught')!r})"
    rate = gate.get("min_catch_rate", 1.0)
    if caught / len(want) < rate:
        return False, f"caught {caught}/{len(want)}, below the mandated {rate:.0%}"
    return True, f"{caught}/{len(want)}"


def earned_versions(m: Mandate, entries: list[dict]) -> dict[tuple, str]:
    """Reviewer versions that earned the current stages: the signed registry, and canary passes of the seeded set."""
    out = {version_key(n, r): "signed mandate registry" for n, r in m.reviewers.items() if r.get("role") == "reviewer"}
    for e in entries:
        p = e["payload"]
        if e["type"] != "canary":
            continue
        ok, why = canary_release(m, p)
        if ok:
            for r in p.get("reviewers", []):
                out.setdefault(version_key(r["name"], r), f"passed the seeded-defect set (ledger #{e['seq']}, {why})")
    return out


def ignored_canaries(m: Mandate, entries: list[dict]) -> list[str]:
    """Canary runs that released nothing, with the reason (shown by `countersign trust`)."""
    out = []
    for e in entries:
        if e["type"] == "canary" and e["payload"].get("reviewers"):
            ok, why = canary_release(m, e["payload"])
            if not ok:
                out.append(f"ledger #{e['seq']}: canary by {e.get('signer')} releases no reviewer version: {why}")
    return out


def spotcheck_ignored(m: Mandate, e: dict, area: str, counted: set) -> str | None:
    """Why a spot-check does not count for `area` (None if it counts). Only the area's named owner grades the AI
    there, and each pack counts once: 50 signatures on one pack are one spot-check, not 50 (red team L3)."""
    p = e["payload"]
    owner = m.area(area).owner
    if e.get("signer") != owner:
        return f"{e.get('signer')} is not the owner of {area} ({owner})"
    if p.get("result") not in ("agree", "disagree"):
        return f"result {p.get('result')!r} is neither agree nor disagree"
    if not p.get("pack_sha256"):
        return "it names no pack (pack_sha256), so it cannot be counted once per pack"
    if (area, p["pack_sha256"]) in counted:
        return f"pack {str(p['pack_sha256'])[:12]} was already spot-checked in this area"
    return None


def invalid(m: Mandate, problems: list[str]) -> dict[str, dict]:
    """Trust state when the ledger does not verify: no trust event is used, every area at ask (red team L1)."""
    why = f"ledger invalid: {problems[0]}" + (f" (+{len(problems) - 1} more)" if len(problems) > 1 else "")
    state = derive(m, [])
    for s in state.values():
        s["cap"], s["reason"], s["gate"], s["next"], s["needed"] = "ask", why, why, None, None
    return state


def verified(ws, m: Mandate, reviewers: dict[str, dict] | None = None) -> tuple[dict[str, dict], list[str]]:
    """derive() over the ledger only after ledger.verify passes; otherwise every area at ask. Returns (state, problems)."""
    problems, _ = ledger.verify(ws)
    if problems:
        return invalid(m, problems), problems
    return derive(m, ledger.read(ws), reviewers), []


def derive(m: Mandate, entries: list[dict], reviewers: dict[str, dict] | None = None) -> dict[str, dict]:
    """Per-area state. `reviewers` (name -> {model, prompt_version}) are the versions reviewing the change at hand;
    when given, the release gate is applied to them."""
    st = stages(m)
    state = {a.name: {"cap": a.max_ai_tier, "mandate_cap": a.max_ai_tier, "probation": False, "streak": 0,
                      "needed": None, "next": None, "reason": "mandate clearance right", "history": [],
                      "spotchecks": [], "changes_since_escape": None, "gate": None} for a in m.areas}

    def requirements(s: dict) -> None:
        nxt = _up(s["cap"], s["mandate_cap"])
        s["next"] = nxt
        s["needed"] = st.get(nxt, {}).get("agreeing_spotchecks") if nxt else None

    def try_climb(s: dict, ref: str) -> bool:
        nxt = _up(s["cap"], s["mandate_cap"])
        if not nxt:
            return False
        req = st.get(nxt, {})
        window = s["spotchecks"][-req.get("agreement_window", len(s["spotchecks"]) or 1):]
        agreement = sum(window) / len(window) if window else 0.0
        quiet = s["changes_since_escape"] is None or s["changes_since_escape"] >= req.get("no_escapes_in_last", 0)
        if s["streak"] >= req.get("agreeing_spotchecks", 0) and agreement >= req.get("min_agreement", 0) and quiet:
            s["cap"], s["streak"] = nxt, 0
            s["probation"] = s["cap"] != s["mandate_cap"]
            s["reason"] = (f"climbed to {nxt} ({ref}): {req.get('agreeing_spotchecks', 0)} agreeing spot-checks in a row, "
                           f"{agreement:.0%} agreement, no escape in the last {req.get('no_escapes_in_last', 0)} changes")
            s["history"].append(f"{ref}: entry requirements for {nxt} met -> cap {nxt}")
            return True
        return False

    def drop(s: dict, ref: str, why: str) -> None:
        s["cap"], s["streak"], s["probation"] = strictest(s["cap"], _down(s["cap"])), 0, True
        s["reason"] = f"probation after {why} ({ref})"

    counted: set[tuple[str, str]] = set()  # (area, pack_sha256) spot-checks already counted
    for e in entries:
        p = e["payload"]
        if e["type"] not in ("spotcheck", "escape", "canary", "signoff"):
            continue
        for area in p.get("areas", []):
            s = state.get(area)
            if s is None:
                continue
            ref = f"ledger #{e['seq']}"
            if e["type"] == "signoff":
                if s["changes_since_escape"] is not None:
                    s["changes_since_escape"] += 1
                continue
            if e["type"] == "escape":
                if not p.get("ai_cleared"):
                    s["history"].append(f"{ref}: escape on {p['change']} ({p['kind']}), but a human signed it at {p.get('tier')}: AI cap unchanged")
                    continue
                s["changes_since_escape"] = 0
                drop(s, ref, f"escape on {p['change']} ({p['kind']})")
                s["history"].append(f"{ref}: escape on AI-cleared {p['change']} ({p['kind']}) -> cap {s['cap']}, probation")
            elif e["type"] == "canary":
                missed = p.get("seeded", 0) - p.get("caught", 0)
                if missed > 0:
                    drop(s, ref, f"the panel missed {missed} of {p['seeded']} seeded defects")
                    s["history"].append(f"{ref}: canary run missed {missed}/{p['seeded']} seeded defects -> cap {s['cap']}, probation")
                else:
                    s["history"].append(f"{ref}: canary run caught {p.get('caught')}/{p.get('seeded')} seeded defects")
            else:
                skip = spotcheck_ignored(m, e, area, counted)
                if skip:
                    s["history"].append(f"{ref}: spot-check by {e.get('signer')} on {p.get('change')} ignored: {skip}")
                    continue
                counted.add((area, p["pack_sha256"]))
                agree = p["result"] != "disagree"
                s["spotchecks"].append(1 if agree else 0)
                if s["changes_since_escape"] is not None:
                    s["changes_since_escape"] += 1
                if not agree:
                    drop(s, ref, f"{e['signer']} disagreed on {p['change']}")
                    s["history"].append(f"{ref}: {e['signer']} disagreed with the AI on {p['change']} -> cap {s['cap']}, probation")
                else:
                    s["streak"] += 1
                    if not try_climb(s, ref):
                        s["history"].append(f"{ref}: {e['signer']} agreed with the AI on {p['change']} (streak {s['streak']})")
            requirements(s)
            if s["probation"] and s["next"]:
                quiet = st.get(s["next"], {}).get("no_escapes_in_last", 0)
                cse = s["changes_since_escape"]
                s["reason"] = (s["reason"].split("; ")[0] + f"; {s['streak']}/{s['needed']} agreeing spot-checks towards {s['next']}"
                               + (f", {cse}/{quiet} changes since the escape" if cse is not None and cse < quiet else ""))

    for s in state.values():
        requirements(s)
    if reviewers:
        earned = earned_versions(m, entries)
        new = [f"{n} {r.get('model')}/{r.get('prompt_version')}" for n, r in sorted(reviewers.items()) if version_key(n, r) not in earned]
        if new:
            why = (f"reviewer version not yet released: {', '.join(new)} has not passed the seeded-defect set "
                   "(a new model or prompt restarts at ask)")
            for s in state.values():
                s["gate"] = why
                if s["cap"] != "ask":
                    s["cap"], s["reason"] = "ask", why
    return state


def caps(state: dict[str, dict]) -> dict[str, dict]:
    return {a: {"cap": s["cap"], "reason": s["reason"]} for a, s in state.items()}


def table(m: Mandate) -> list[dict]:
    """The mandate's stage table, as rows for `countersign trust` and the docs."""
    st = stages(m)
    return [{"stage": k, **st.get(k, {})} for k in LADDER]


__all__ = ["derive", "verified", "invalid", "caps", "table", "stages", "earned_versions", "canary_release", "TIERS"]
