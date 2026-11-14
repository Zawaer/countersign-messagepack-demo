"""What the AI review costs: an append-only spend ledger (measurement/costs.yaml) and docs/COSTS.md.

Every model call made by `review-llm` / `adjudicate` appends one row automatically, from the API's `usage` field.
Runs made outside the runner (Claude and Codex sessions, CI minutes) are added by hand with `source` saying how
the numbers are known: "api usage field" | "estimate" | "unknown". Nothing is ever rewritten; corrections are new rows.
Self-hosted calls (provider verda) are priced by GPU time, not tokens: the row carries `gpu`, `gpu_seconds`, `gpu_hours`
and `basis`, `usd` is wall-clock x GPUs x the hourly rate (source "estimate"), and the per-token price table is never
applied to them (the same model id is $0 on NVIDIA's free tier, which says nothing about our GPUs).
"""

from __future__ import annotations

import json
import os
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml

from .common import HUMAN_TIERS, Workspace, is_mutant, read_json

HEADER = """# Countersign spend ledger: append-only. One row per model call or CI run; never edit a row, add a correction.
# `countersign costs` renders docs/COSTS.md from it. review-llm and adjudicate append rows automatically.
# source: "api usage field" (tokens from the API response) | "estimate" | "unknown". usd: null = not known.

prices_usd_per_1m: {}

runs:
"""


def path(ws: Workspace) -> Path:
    return ws.measurement_dir / "costs.yaml"


def load(ws: Workspace) -> dict:
    p = path(ws)
    return (yaml.safe_load(p.read_text(encoding="utf-8")) or {}) if p.exists() else {}


def run_url(env=None) -> str | None:
    env = os.environ if env is None else env
    if env.get("GITHUB_RUN_ID") and env.get("GITHUB_REPOSITORY"):
        return f"{env.get('GITHUB_SERVER_URL', 'https://github.com')}/{env['GITHUB_REPOSITORY']}/actions/runs/{env['GITHUB_RUN_ID']}"
    return None


def price_usd(prices: dict, model: str, tokens_in, tokens_out) -> float | None:
    p = prices.get(model)
    if not p or tokens_in is None or tokens_out is None or p.get("in") is None or p.get("out") is None:
        return None
    return round((tokens_in * p["in"] + tokens_out * p["out"]) / 1e6, 4)


def row_usd(prices: dict, r: dict) -> float | None:
    """A row's cost: its own `usd`, else the token price, except for GPU-time rows (never priced per token)."""
    if r.get("usd") is not None or r.get("gpu"):
        return r.get("usd")
    return price_usd(prices, r.get("model", ""), r.get("tokens_in"), r.get("tokens_out"))


def append(ws: Workspace, *, provider: str, model: str, purpose: str, change: str | None, tokens_in: int | None,
           tokens_out: int | None, source: str, usd: float | None = None, when: datetime | None = None,
           extra: dict | None = None) -> dict:
    """Append one row (a JSON flow mapping, which is valid YAML) to the end of the `runs:` list.
    `extra`: more fields for the row (self-hosted: gpu, gpu_seconds, gpu_hours, basis)."""
    p = path(ws)
    if not p.exists():
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(HEADER, encoding="utf-8")
    led = load(ws)
    if usd is None and not (extra or {}).get("gpu"):
        usd = price_usd(led.get("prices_usd_per_1m") or {}, model, tokens_in, tokens_out)
    row = {"when": (when or datetime.now(ZoneInfo("Europe/Helsinki"))).astimezone(ZoneInfo("Europe/Helsinki")).strftime("%Y-%m-%d %H:%M"),
           "provider": provider, "model": model, "purpose": purpose, "change": change,
           "tokens_in": tokens_in, "tokens_out": tokens_out, "usd": usd, "source": source, **(extra or {}), "run_url": run_url()}
    text = p.read_text(encoding="utf-8")
    with p.open("a", encoding="utf-8") as f:
        f.write(("" if text.endswith("\n") else "\n") + "  - " + json.dumps(row, ensure_ascii=False) + "\n")
    return row


def _money(v: float | None) -> str:
    return "unknown" if v is None else f"${v:,.2f}"


def _known(b: dict | None) -> str:
    if not b:
        return "-"
    if b["runs"] == b["unknown"]:
        return "unknown"
    return _money(b["usd"]) + (" + unknown" if b["unknown"] else "")


def _tok(v) -> str:
    return "?" if v is None else f"{v:,}"


def render(ws: Workspace) -> str:
    """docs/COSTS.md: totals per provider, cost per reviewed change, and the human-minutes comparison."""
    from . import measure, pack as pack_mod
    from .mandate import load as load_mandate

    led = load(ws)
    prices = led.get("prices_usd_per_1m") or {}
    runs = led.get("runs") or []
    by_provider: dict[str, dict] = defaultdict(lambda: {"runs": 0, "in": 0, "out": 0, "usd": 0.0, "unknown": 0})
    by_change: dict[str, dict] = defaultdict(lambda: {"usd": 0.0, "unknown": 0, "runs": 0, "who": set()})
    rows = []
    for r in runs:
        usd = row_usd(prices, r)
        p = by_provider[r["provider"]]
        p["runs"] += 1
        p["in"] += r.get("tokens_in") or 0
        p["out"] += r.get("tokens_out") or 0
        if usd is None:
            p["unknown"] += 1
        else:
            p["usd"] += usd
        changes = r.get("changes") or ([r["change"]] if r.get("change") else [])
        for c in changes:  # a multi-change run is split evenly across its changes
            b = by_change[c]
            b["runs"] += 1
            b["who"].add(r["provider"])
            if usd is None:
                b["unknown"] += 1
            else:
                b["usd"] += usd / len(changes)
        link = f" [run]({r['run_url']})" if r.get("run_url") else ""
        rows.append(f"| {r['when']} | {r['provider']} | {r['model']} | {r['purpose']}{link} | {', '.join(changes) or '-'} | "
                    f"{_tok(r.get('tokens_in'))} / {_tok(r.get('tokens_out'))}"
                    + (f" (total {r['tokens_total']:,})" if r.get("tokens_total") else "")
                    + f" | {_money(usd)} | {r.get('source', 'unknown')}"
                    + (f" ({r['gpu']}, {r.get('gpu_seconds')} s wall-clock; {r.get('basis', '')})" if r.get("gpu") else "") + " |")

    m = load_mandate(ws)
    mm = m["measurement"]
    human = []
    for change in [c for c in ws.changes() if not is_mutant(c)]:
        if not ws.reviews(change):
            continue
        pk = pack_mod.build(ws, change, use_trust=False)
        bf = read_json(ws.facts_path(change)).get("diff", {}).get("by_file", [])
        pk["_lines"] = {"source": sum(f.get("ins", 0) + f.get("del", 0) for f in bf if f.get("kind") != "generated"),
                        "generated": sum(f.get("ins", 0) + f.get("del", 0) for f in bf if f.get("kind") == "generated")}
        full, guided = measure._minutes(pk, mm)
        human.append((change, pk["tier"], full, guided))

    known = sum(p["usd"] for p in by_provider.values())
    out = ["# What the AI review costs", "",
           f"_Generated by `countersign costs` from [measurement/costs.yaml](../measurement/costs.yaml) "
           f"({len(runs)} rows). \"unknown\" means the provider bills it somewhere we can't read from here; it is not zero._", "",
           "## Totals per provider", "", "| Provider | Rows | Tokens in / out (known) | Cost | Rows with unknown cost |", "|---|---|---|---|---|"]
    out += [f"| {n} | {p['runs']} | {p['in']:,} / {p['out']:,} | {_money(p['usd']) if p['runs'] > p['unknown'] else 'unknown'} | {p['unknown']} |"
            for n, p in sorted(by_provider.items())]
    out += ["", f"**Known total: {_money(known)}**" + (" plus the rows marked unknown" if any(p["unknown"] for p in by_provider.values()) else ""), "",
            "## Cost per reviewed change", "", "| Change | Rows | Providers | Known cost | Rows with unknown cost |", "|---|---|---|---|---|"]
    out += [f"| {c} | {b['runs']} | {', '.join(sorted(b['who']))} | {_money(b['usd']) if b['runs'] > b['unknown'] else 'unknown'} | {b['unknown']} |" for c, b in sorted(by_change.items())]
    out += ["", "## Against human review time (SIMULATED)", "",
            "_Minutes come from the mandate's reading model (`measurement` block: lines per minute, minutes per file, pack minutes per tier), "
            "not from a stopwatch. They are an estimate to compare orders of magnitude, nothing more._", "",
            "| Change | Tier | Full read (min, simulated) | With the pack (min, simulated) | Saved (min, simulated) | Known AI cost |", "|---|---|---|---|---|---|"]
    out += [f"| {c} | {t} | {f} | {g} | {round(f - g, 1)} | {_known(by_change.get(c))}" + " |" for c, t, f, g in human]
    if human:
        f_tot, g_tot = sum(x[2] for x in human), sum(x[3] for x in human)
        out += ["", f"Simulated totals: full read {round(f_tot, 1)} min, with the pack {round(g_tot, 1)} min "
                f"({sum(1 for x in human if x[1] in HUMAN_TIERS)} of {len(human)} changes still routed to a human)."]
    out += ["", "## Prices used", "", "| Model | $ in / 1M | $ out / 1M | Basis |", "|---|---|---|---|"]
    out += [f"| {k} | {v.get('in')} | {v.get('out')} | {v.get('basis', '')}{' (ASSUMPTION)' if v.get('assumption') else ''} |" for k, v in prices.items()]
    out += ["", "## Every row", "", "| When (Helsinki) | Provider | Model | Purpose | Changes | Tokens in / out | Cost | Source |",
            "|---|---|---|---|---|---|---|---|", *rows, ""]
    out += [f"- {n}" for n in led.get("notes", [])]
    return "\n".join(out) + "\n"


def write(ws: Workspace) -> Path:
    out = ws.root / "docs" / "COSTS.md"
    out.write_text(render(ws), encoding="utf-8")
    return out
