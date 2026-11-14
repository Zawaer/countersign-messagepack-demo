"""SIMULATED: trust over time. Every number this module produces is simulated and says so.

A stream of changes per area, week by week. Each change is defective with a configurable probability. The AI
(deterministic checks + reviewer panel) misses a defect with a probability taken from what we MEASURED where we
have it (checks: seeded defects that survived every check; panel: issues the reviewers missed on the four real
changes) and assumed where we don't (human miss rate, change volumes). Routing uses the real trust rules:
caps come from countersign.trust.derive() over a synthetic ledger, so the escape -> probation -> spot-checks ->
restore cycle is the same code the pipeline runs.

Per change:
  AI recommendation  clear (silent/notify) with probability p_clear[area] if it sees no problem; a defect it catches -> ask
  tier               the stricter of the recommendation and the area's current cap (trust.derive)
  routed (ask)       a human reads it (cost: full-read minutes; we assume the pack saves nothing on the read itself),
                     catches a defect with probability 1 - human_miss; the human's review grades the AI's recommendation
                     like a spot-check when the AI would have cleared it
  cleared            costs nothing, unless spot-checked (probability spot_rate, full-read minutes)
  escape             a defect nobody caught. If it was AI-cleared, it surfaces `escape_delay` weeks later as an escape event:
                     the area drops to `ask` and starts probation. A human-signed escape leaves the AI's cap alone.

Scenarios (same random draws for each): countersign (the mandate as written, 10% spot-checks), no-spot-checks,
countersign+canaries (what-if: weekly seeded defects through the panel and a stricter restore rule), no-withdrawal
(mandate caps from day one, never withdrawn) and full-human-review (baseline: every change read in full, same CI checks). A drift event can make the reviewers worse mid-run (R1: evidence made
Codex agreeable), to show how fast escapes and spot-checks pull the clearance back.
"""

from __future__ import annotations

import json
import random
from copy import deepcopy
from pathlib import Path

from . import trust
from .common import HUMAN_TIERS, Workspace, strictest, write_json
from .mandate import load

DEFAULTS = {
    "weeks": 52, "replicates": 200, "seed": 2026,
    # area -> changes per week, true defect rate, P(AI clears a change it sees no problem in), full-read minutes
    "areas": {
        "generator-analyzer-core": {"per_week": 12, "defect_rate": 0.10, "p_clear": 0.45, "full_read_min": 30},
        "runtime-core": {"per_week": 6, "defect_rate": 0.10, "p_clear": 0.45, "full_read_min": 40},
        "build": {"per_week": 3, "defect_rate": 0.05, "p_clear": 0.6, "full_read_min": 10},
        "tests": {"per_week": 6, "defect_rate": 0.03, "p_clear": 0.8, "full_read_min": 10},
        "docs": {"per_week": 4, "defect_rate": 0.02, "p_clear": 0.9, "full_read_min": 5},
    },
    "checks_miss": 3 / 14,      # MEASURED: 3 of 14 seeded defects survive every check (evidence/*-mut*/facts.json)
    "panel_miss": 0.5,          # ASSUMED between MEASURED Claude 1/5 and Codex 5/5 on check-invisible issues (see MEASUREMENT.md)
    "human_miss": 0.35,         # ASSUMED: a full human read misses about a third of defects
    "spot_rate": 0.10,
    "escape_delay": 12,         # MEASURED: median 84 days from merge to the first fix/revert over the 11 historical escapes
    "drift": {"week": 26, "panel_miss": 1.0},
    # canaries: seeded defects the checks miss, sent through the reviewer panel each week; if the panel's miss rate over
    # `window` weeks exceeds `threshold`, that counts as a disagreeing spot-check (cap tightens, probation)
    "canaries": {"per_week": 2, "window": 4, "threshold": 0.75},
    # what-if for the countersign+canaries scenario only: restoring clearance needs 20 agreeing spot-checks, not the
    # mandate's 3 (agreement on a clean change is weak evidence, so 3 restores clearance within days)
    "whatif_restore_after": 20,   # from week 26 the panel catches nothing the checks miss (Codex v2 behaviour)
}


def _panel_miss(cfg: dict, week: int) -> float:
    return cfg["drift"]["panel_miss"] if cfg.get("drift") and week >= cfg["drift"]["week"] else cfg["panel_miss"]


def run_once(cfg: dict, m, spot_rate: float, mode: str, rng: random.Random, canaries: bool = False) -> list[dict]:
    """mode: countersign | static (mandate caps from day one, never withdrawn) | baseline (every change read in full).
    Deterministic checks run in every mode, the baseline included (normal CI): a defect they catch never escapes.
    A defect the reviewer panel catches is a verified finding in the pack, so it is caught too. Only defects that
    both miss depend on a human reading the change. Returns one dict per week."""
    events: list[dict] = []
    seq = 0

    def ev(type_, area, **payload):
        nonlocal seq
        seq += 1
        # each simulated event stands for a distinct change, signed by the area's owner (trust counts a spot-check
        # only from the owner, once per pack)
        owner = next((a.owner for a in m.areas if a.name == area), "sim")
        events.append({"seq": seq, "type": type_, "signer": owner,
                       "payload": {"areas": [area], "simulated": True, "pack_sha256": f"sim-{seq}", **payload}})

    if mode == "countersign":
        for a in cfg["areas"]:  # a fresh area has no track record: it starts on probation
            ev("escape", a, change="onboarding", kind="onboarding", ai_cleared=True)
    pending: list[tuple[int, str]] = []  # (week the escape surfaces, area)
    canary_log: dict[str, list[int]] = {}
    weeks = []
    for w in range(cfg["weeks"]):
        for due, area in [p for p in pending if p[0] == w]:
            ev("escape", area, change=f"w{w}", kind="incident", ai_cleared=True)
        pending = [p for p in pending if p[0] != w]
        caps = trust.caps(trust.derive(m, events if mode == "countersign" else []))
        stat = {"week": w + 1, "changes": 0, "defects": 0, "routed": 0, "minutes": 0.0, "escapes": 0, "escapes_ai_cleared": 0,
                "caught_by_spotcheck": 0, "cleared_share": 0.0}
        panel_miss = _panel_miss(cfg, w)
        if canaries:  # seeded defects the checks cannot see, fed to the reviewer panel every week (known answer)
            c = cfg["canaries"]
            for area in cfg["areas"]:
                hist = canary_log.setdefault(area, [])
                hist.append(sum(rng.random() < panel_miss for _ in range(c["per_week"])))
                window = hist[-c["window"]:]
                if len(window) == c["window"] and sum(window) / (c["per_week"] * c["window"]) > c["threshold"]:
                    ev("spotcheck", area, change=f"canary-w{w}", result="disagree")
                    hist.clear()
        for area, p in cfg["areas"].items():
            for _ in range(p["per_week"]):
                defect = rng.random() < p["defect_rate"]
                r_chk, r_pan, r_human, r_spot, r_clear = (rng.random() for _ in range(5))
                stat["changes"] += 1
                stat["defects"] += defect
                checks_see = defect and r_chk >= cfg["checks_miss"]
                human_finds = defect and r_human >= cfg["human_miss"]
                if mode == "baseline":
                    stat["routed"] += 1
                    stat["minutes"] += p["full_read_min"]
                    stat["escapes"] += defect and not checks_see and not human_finds
                    continue
                ai_sees = checks_see or (defect and r_pan >= panel_miss)
                rec = "ask" if ai_sees else ("notify" if r_clear < p["p_clear"] else "ask")
                tier = strictest(rec, caps[area]["cap"])
                if tier in HUMAN_TIERS:
                    stat["routed"] += 1
                    stat["minutes"] += p["full_read_min"]
                    if defect and not ai_sees and not human_finds:
                        stat["escapes"] += 1  # human-signed: the human owned it, the AI's cap is unchanged
                    if rec not in HUMAN_TIERS:  # the human's read grades what the AI would have cleared
                        ev("spotcheck", area, change=f"w{w}", result="disagree" if human_finds else "agree")
                    continue
                if r_spot < spot_rate:
                    stat["minutes"] += p["full_read_min"]
                    ev("spotcheck", area, change=f"w{w}", result="disagree" if human_finds else "agree")
                    if human_finds:
                        stat["caught_by_spotcheck"] += 1
                        continue
                if defect:
                    stat["escapes"] += 1
                    stat["escapes_ai_cleared"] += 1
                    pending.append((w + cfg["escape_delay"], area))
        stat["cleared_share"] = round(1 - stat["routed"] / stat["changes"], 3)
        weeks.append(stat)
    return weeks


def _mandate(ws: Workspace, cfg: dict):
    """The real mandate; `restore_after` (if set) overrides trust.restore_after_agreeing_spotchecks for a what-if."""
    m = load(ws)
    if cfg.get("restore_after"):
        m.data = deepcopy(m.data)
        m.data["trust"]["restore_after_agreeing_spotchecks"] = cfg["restore_after"]
    return m


def simulate(ws: Workspace, cfg: dict | None = None) -> dict:
    cfg = {**deepcopy(DEFAULTS), **(cfg or {})}
    m = _mandate(ws, cfg)
    m_whatif = _mandate(ws, {**cfg, "restore_after": cfg["whatif_restore_after"]})
    scenarios = {"countersign": ("countersign", cfg["spot_rate"], False, m), "no-spot-checks": ("countersign", 0.0, False, m),
                 "countersign+canaries": ("countersign", cfg["spot_rate"], True, m_whatif),
                 "no-withdrawal": ("static", 0.0, False, m), "full-human-review": ("baseline", 0.0, False, m)}
    out = {"simulated": True, "config": cfg, "scenarios": {}}
    for name, (mode, spot, can, mm) in scenarios.items():
        runs = [run_once(cfg, mm, spot, mode, random.Random(cfg["seed"] + i), can) for i in range(cfg["replicates"])]
        weekly = []
        for w in range(cfg["weeks"]):
            col = [r[w] for r in runs]
            avg = lambda k: round(sum(c[k] for c in col) / len(col), 3)  # noqa: E731
            weekly.append({"week": w + 1, "minutes": avg("minutes"), "escapes": avg("escapes"), "escapes_ai_cleared": avg("escapes_ai_cleared"),
                           "routed_share": round(1 - avg("cleared_share"), 3), "caught_by_spotcheck": avg("caught_by_spotcheck")})
        out["scenarios"][name] = weekly
    out["summary"] = summary(out)
    return out


def _mean(rows, key, a, b):
    xs = [r[key] for r in rows[a:b]]
    return round(sum(xs) / len(xs), 2) if xs else None


def summary(r: dict) -> dict:
    d = r["config"]["drift"]["week"] if r["config"].get("drift") else r["config"]["weeks"]
    s = {}
    for name, rows in r["scenarios"].items():
        s[name] = {"minutes_per_week_first_4": _mean(rows, "minutes", 0, 4), "minutes_per_week_before_drift": _mean(rows, "minutes", 8, d),
                   "minutes_per_week_after_drift": _mean(rows, "minutes", d, len(rows)),
                   "escapes_per_week_before_drift": _mean(rows, "escapes", 8, d), "escapes_per_week_after_drift": _mean(rows, "escapes", d, len(rows)),
                   "routed_share_before_drift": _mean(rows, "routed_share", 8, d), "routed_share_after_drift": _mean(rows, "routed_share", d, len(rows)),
                   "escapes_total": round(sum(x["escapes"] for x in rows), 1)}
    return {"simulated": True, "weeks": r["config"]["weeks"], "replicates": r["config"]["replicates"], "drift_week": d, **s}


def sensitivity(ws: Workspace, base: dict | None = None) -> list[dict]:
    """Escapes and minutes per week over a small grid of the two assumptions that matter most."""
    rows = []
    for panel in (0.2, 0.5, 1.0):
        for spot in (0.0, 0.05, 0.10, 0.20):
            cfg = {**deepcopy(DEFAULTS), **(base or {}), "panel_miss": panel, "spot_rate": spot, "drift": None, "replicates": 60}
            m = load(ws)
            runs = [run_once(cfg, m, spot, "countersign", random.Random(cfg["seed"] + i)) for i in range(cfg["replicates"])]
            base_runs = [run_once(cfg, m, 0.0, "baseline", random.Random(cfg["seed"] + i)) for i in range(cfg["replicates"])]
            per = lambda rs, k: round(sum(w[k] for r in rs for w in r[8:]) / (len(rs) * (cfg["weeks"] - 8)), 2)  # noqa: E731
            rows.append({"panel_miss": panel, "spot_rate": spot, "escapes_per_week": per(runs, "escapes"), "baseline_escapes_per_week": per(base_runs, "escapes"),
                         "minutes_per_week": per(runs, "minutes"), "baseline_minutes_per_week": per(base_runs, "minutes"), "simulated": True})
    return rows


# --- chart (self-contained SVG inside HTML; no external assets) ------------------------------------------------

SERIES = [("countersign", "Countersign, 10% spot-checks", "--series-1"), ("no-spot-checks", "Countersign, spot-checks off", "--series-2"),
          ("countersign+canaries", "What-if: + weekly canaries, restore after 20 agreeing checks", "--series-4"),
          ("full-human-review", "Full human review (baseline, same CI checks)", "--series-3")]


def _panel(rows_by: dict, key: str, title: str, unit: str, x0: int, y0: int, w: int, h: int, drift: int | None) -> str:
    weeks = len(next(iter(rows_by.values())))
    ymax = max(r[key] for rows in rows_by.values() for r in rows) * 1.1 or 1
    sx = lambda i: x0 + 56 + (w - 90) * i / (weeks - 1)  # noqa: E731
    sy = lambda v: y0 + 28 + (h - 56) * (1 - v / ymax)  # noqa: E731
    out = [f'<text x="{x0}" y="{y0 + 14}" class="t">{title}</text>']
    for k in range(5):
        v = ymax * k / 4
        out.append(f'<line x1="{x0 + 56}" x2="{x0 + w - 34}" y1="{sy(v):.1f}" y2="{sy(v):.1f}" class="grid"/>'
                   f'<text x="{x0 + 50}" y="{sy(v) + 4:.1f}" class="ax" text-anchor="end">{v:.0f}</text>' if ymax >= 10 else
                   f'<line x1="{x0 + 56}" x2="{x0 + w - 34}" y1="{sy(v):.1f}" y2="{sy(v):.1f}" class="grid"/>'
                   f'<text x="{x0 + 50}" y="{sy(v) + 4:.1f}" class="ax" text-anchor="end">{v:.2f}</text>')
    for wk in (1, 13, 26, 39, 52):
        if wk <= weeks:
            out.append(f'<text x="{sx(wk - 1):.1f}" y="{y0 + h - 10}" class="ax" text-anchor="middle">wk {wk}</text>')
    if drift:
        out.append(f'<line x1="{sx(drift - 1):.1f}" x2="{sx(drift - 1):.1f}" y1="{y0 + 24}" y2="{y0 + h - 28}" class="drift"/>'
                   f'<text x="{sx(drift - 1) + 4:.1f}" y="{y0 + 36}" class="ax">reviewers degrade</text>')
    for name, label, var in SERIES:
        rows = rows_by[name]
        pts = " ".join(f"{sx(i):.1f},{sy(r[key]):.1f}" for i, r in enumerate(rows))
        out.append(f'<polyline points="{pts}" fill="none" stroke="var({var})" stroke-width="2" stroke-linejoin="round"><title>{label}</title></polyline>')
        for i, r in enumerate(rows):
            out.append(f'<circle cx="{sx(i):.1f}" cy="{sy(r[key]):.1f}" r="6" class="hit"><title>{label}, week {i + 1}: {r[key]} {unit}</title></circle>')
    return "\n".join(out)


def _rolling(rows_by: dict, key: str, n: int = 4) -> dict:
    out = {}
    for name, rows in rows_by.items():
        out[name] = [{key: round(sum(x[key] for x in rows[max(0, i - n + 1):i + 1]) / len(rows[max(0, i - n + 1):i + 1]), 3)} for i in range(len(rows))]
    return out


def chart_html(r: dict) -> str:
    drift = r["config"]["drift"]["week"] if r["config"].get("drift") else None
    W, H = 720, 260
    svg = (f'<svg viewBox="0 0 {W} {2 * H + 10}" role="img" aria-label="Simulated human review minutes and escapes per week">'
           + _panel(r["scenarios"], "minutes", "Human review minutes per week (SIMULATED)", "min", 0, 0, W, H, drift)
           + _panel(_rolling(r["scenarios"], "escapes"), "escapes", "Escapes per week, 4-week rolling mean (SIMULATED)", "escapes", 0, H + 10, W, H, drift) + "</svg>")
    legend = "".join(f'<span class="lg"><i style="background:var({v})"></i>{lab}</span>' for _, lab, v in SERIES)
    s = r["summary"]
    rows = "".join(f"<tr><td>{lab}</td><td>{s[n]['minutes_per_week_first_4']}</td><td>{s[n]['minutes_per_week_before_drift']}</td>"
                   f"<td>{s[n]['escapes_per_week_before_drift']}</td><td>{s[n]['minutes_per_week_after_drift']}</td><td>{s[n]['escapes_per_week_after_drift']}</td></tr>"
                   for n, lab, _ in SERIES + [("no-withdrawal", "No trust ledger: clearance never withdrawn (table only)", "")])
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Countersign: trust over time (SIMULATED)</title>
<style>
.viz-root{{color-scheme:light;--surface-1:#fcfcfb;--text-primary:#0b0b0b;--text-secondary:#52514e;--grid:#e4e3df;
--series-1:#2a78d6;--series-2:#eb6834;--series-3:#1baf7a;--series-4:#eda100;font:14px system-ui,sans-serif;background:var(--surface-1);color:var(--text-primary);max-width:760px;margin:24px auto;padding:0 16px}}
@media (prefers-color-scheme:dark){{.viz-root{{color-scheme:dark;--surface-1:#1a1a19;--text-primary:#f0efec;--text-secondary:#c3c2b7;--grid:#383835;
--series-1:#3987e5;--series-2:#d95926;--series-3:#199e70;--series-4:#c98500}}}}
body{{margin:0;background:var(--surface-1)}} .t{{fill:var(--text-primary);font-weight:600;font-size:13px}} .ax{{fill:var(--text-secondary);font-size:11px}}
.grid{{stroke:var(--grid);stroke-width:1}} .drift{{stroke:var(--text-secondary);stroke-dasharray:4 4}} .hit{{fill:transparent}} .hit:hover{{fill:var(--text-secondary)}}
.lg{{margin-right:16px;color:var(--text-secondary)}} .lg i{{display:inline-block;width:14px;height:3px;margin-right:6px;vertical-align:middle;border-radius:2px}}
table{{border-collapse:collapse;margin-top:12px;font-size:13px}} td,th{{border-bottom:1px solid var(--grid);padding:4px 8px;text-align:right}} td:first-child,th:first-child{{text-align:left}}
.banner{{border:2px solid var(--series-2);padding:6px 10px;border-radius:4px;font-weight:600}}
</style></head><body><div class="viz-root">
<p class="banner">SIMULATED. Inputs: measured catch rates of our checks and reviewers, assumed volumes and human miss rate (see docs/MEASUREMENT.md).</p>
<h2>Trust over time: {s['replicates']} runs of {s['weeks']} weeks, averaged</h2>
<div>{legend}</div>{svg}
<table><thead><tr><th>Scenario</th><th>min/wk, weeks 1-4</th><th>min/wk, wk 9-{s['drift_week']}</th><th>escapes/wk, wk 9-{s['drift_week']}</th>
<th>min/wk after drift</th><th>escapes/wk after drift</th></tr></thead><tbody>{rows}</tbody></table>
<p class="ax" style="fill:none">Every area starts on probation (no track record). Hover a point for its value. Generated by <code>countersign simulate</code>.</p>
</div></body></html>
"""


def write(ws: Workspace, r: dict, sens: list[dict] | None = None) -> Path:
    d = ws.root / "measurement" / "simulation"
    write_json(d / "results.json", r)
    if sens is not None:
        write_json(d / "sensitivity.json", {"simulated": True, "rows": sens})
    (d / "trust_over_time.html").write_text(chart_html(r), encoding="utf-8")
    return d


def main_summary(r: dict) -> str:
    return json.dumps(r["summary"], indent=1)
