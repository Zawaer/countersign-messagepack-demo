"""Stage 7: per-area trust, derived only from signed ledger events (no hidden state).

- Start: each area's cap is the mandate's max_ai_tier (its clearance right).
- escape on a change the AI cleared (silent/notify) -> every area that change touched drops to `escape_cap`
  and enters probation.
- spotcheck disagree -> the cap tightens by `disagree_tightens_by` steps and probation (re)starts.
- spotcheck agree while on probation -> streak + 1; after `restore_after_agreeing_spotchecks` in a row the
  mandate cap is restored.
"""

from __future__ import annotations

from .common import TIERS, strictest
from .mandate import Mandate


def derive(m: Mandate, entries: list[dict]) -> dict[str, dict]:
    t = m["trust"]
    need = t["restore_after_agreeing_spotchecks"]
    state = {a.name: {"cap": a.max_ai_tier, "mandate_cap": a.max_ai_tier, "probation": False, "streak": 0,
                      "needed": need, "reason": "mandate clearance right", "history": []} for a in m.areas}
    for e in entries:
        p = e["payload"]
        if e["type"] not in ("spotcheck", "escape"):
            continue
        for area in p.get("areas", []):
            s = state.get(area)
            if s is None:
                continue
            ref = f"ledger #{e['seq']}"
            if e["type"] == "escape":
                if not p.get("ai_cleared"):
                    s["history"].append(f"{ref}: escape on {p['change']} ({p['kind']}), but a human signed it at {p.get('tier')}: AI cap unchanged")
                    continue
                s.update(cap=strictest(s["cap"], t["escape_cap"]), probation=True, streak=0,
                         reason=f"probation after escape on {p['change']} ({p['kind']}, {ref}); 0/{need} agreeing spot-checks")
                s["history"].append(f"{ref}: escape on AI-cleared {p['change']} ({p['kind']}) -> cap {s['cap']}, probation")
            elif p["result"] == "disagree":
                tightened = TIERS[min(len(TIERS) - 2, TIERS.index(s["cap"]) + t["disagree_tightens_by"])]
                s.update(cap=strictest(s["cap"], tightened), probation=True, streak=0,
                         reason=f"probation after {e['signer']} disagreed on {p['change']} ({ref}); 0/{need} agreeing spot-checks")
                s["history"].append(f"{ref}: {e['signer']} disagreed with the AI on {p['change']} -> cap {s['cap']}, probation")
            else:
                s["streak"] += 1
                if s["probation"] and s["streak"] >= need:
                    s.update(cap=s["mandate_cap"], probation=False, reason=f"restored after {need} agreeing spot-checks ({ref})")
                    s["history"].append(f"{ref}: {e['signer']} agreed on {p['change']} -> {need} in a row, cap restored to {s['cap']}")
                else:
                    if s["probation"]:
                        s["reason"] = s["reason"].rsplit(";", 1)[0] + f"; {s['streak']}/{need} agreeing spot-checks"
                    s["history"].append(f"{ref}: {e['signer']} agreed with the AI on {p['change']} (streak {s['streak']})")
    return state


def caps(state: dict[str, dict]) -> dict[str, dict]:
    return {a: {"cap": s["cap"], "reason": s["reason"]} for a, s in state.items()}
