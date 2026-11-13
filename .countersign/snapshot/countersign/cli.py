"""countersign CLI. Every command reads and writes plain files, so each step can be replayed and audited."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import costs as costs_mod, keys, ledger, llm, mandate as mandate_mod, measure, pack as pack_mod, trust
from .common import DEFAULT_REPO, HUMAN_TIERS, Workspace, canonical, read_json, sha256_hex, write_json


def _ws(a) -> Workspace:
    return Workspace.at(a.root, a.inputs, a.repo, a.mandate)


def _load_pack(ws: Workspace, ref: str) -> tuple[dict, Path]:
    path = Path(ref).resolve() if ref.endswith(".json") else ws.pack_dir(ref) / "pack.json"
    if not path.exists():
        raise SystemExit(f"no pack at {path}: run `countersign review <change>` first")
    return read_json(path), path


def cmd_review(a) -> int:
    ws = _ws(a)
    for change in a.changes:
        p = pack_mod.build(ws, change)
        out = pack_mod.write(ws, p)
        if not a.quiet:
            print(pack_mod.card(p) + "\n")
        print(f"wrote {out}/pack.json, pack.md, pack.html  (tier {p['tier']}, owner {p['owner']})")
    return 0


def cmd_route(a) -> int:
    ws = _ws(a)
    changes = ws.changes() if a.all or not a.changes else a.changes
    print(f"{'change':<12} {'tier':<7} {'score':>6}  {'owner':<7} reason")
    for c in changes:
        p = pack_mod.build(ws, c)
        w = p["why"][0]
        more = f" (+{len(p['why']) - 1} more)" if len(p["why"]) > 1 else ""
        print(f"{c:<12} {p['tier']:<7} {p['risk']['score']:>6}  {p['owner']:<7} [{w['source']}] {w['id']}: {w['why']}{more}")
    return 0


def cmd_sign(a) -> int:
    ws = _ws(a)
    p, path = _load_pack(ws, a.pack)
    fresh = pack_mod.build(ws, p["change"])
    if canonical(fresh) != canonical(p):
        raise SystemExit(f"{path} is out of date (inputs, mandate or trust changed): re-run `countersign review {p['change']}` and read it again")
    print(pack_mod.card(p) + "\n")
    if a.signer != p["owner"]:
        raise SystemExit(f"{a.signer} is not the owner of this change; the mandate names {p['owner']}")
    decision = a.decision or input(f"{a.signer}, type your decision {p['signoff']['allowed_decisions']}: ").strip()
    if decision not in p["signoff"]["allowed_decisions"]:
        raise SystemExit(f"decision {decision!r} not allowed for tier {p['tier']}: {p['signoff']['allowed_decisions']}")
    note = a.note if a.note is not None else input("note (optional): ").strip()
    payload = {"change": p["change"], "pack_path": str(path.relative_to(ws.root)), "pack_sha256": sha256_hex(canonical(p)),
               "decision": decision, "note": note, "tier": p["tier"], "ai_cleared": p["tier"] not in HUMAN_TIERS,
               "areas": [x["name"] for x in p["areas"]], "mandate_sha256": p["mandate"]["sha256"],
               "statement": p["signoff"]["statement"]}
    e = ledger.append(ws, "signoff", payload, a.signer)
    write_json(path.parent / "signoff.json", e)
    print(f"signed: ledger #{e['seq']} {decision} by {a.signer}, hash {e['hash'][:16]}")
    return 0


def cmd_verify_ledger(a) -> int:
    ws = _ws(a)
    problems, warnings = ledger.verify(ws)
    n = len(ledger.read(ws)) if not any("not valid JSON" in p for p in problems) else "?"
    for w in warnings:
        print(f"warning: {w}")
    if problems:
        print(f"LEDGER INVALID ({len(problems)} problems):")
        for p in problems:
            print(f"  {p}")
        return 1
    print(f"ledger OK: {n} entries, hash chain intact, every signature verifies")
    return 0


def cmd_trust(a) -> int:
    ws = _ws(a)
    m = mandate_mod.load(ws)
    state = trust.derive(m, ledger.read(ws))
    print(f"{'area':<26} {'owner':<6} {'mandate':<7} {'cap now':<7} {'probation':<9} reason")
    for area in m.areas:
        s = state[area.name]
        prob = f"{s['streak']}/{s['needed']}" if s["probation"] else "no"
        print(f"{area.name:<26} {area.owner:<6} {s['mandate_cap']:<7} {s['cap']:<7} {prob:<9} {s['reason']}")
        for h in s["history"]:
            print(f"{'':<28}{h}")
    return 0


def _event_pack(ws: Workspace, change: str, areas: list[str] | None = None) -> dict:
    p, _ = _load_pack(ws, change)
    return {"change": change, "pack_sha256": sha256_hex(canonical(p)), "tier": p["tier"], "ai_recommendation": p["ai_recommendation"],
            "ai_cleared": p["tier"] not in HUMAN_TIERS, "areas": areas or [x["name"] for x in p["areas"]]}


def cmd_spotcheck(a) -> int:
    ws = _ws(a)
    base = _event_pack(ws, a.change)
    # A spot-check grades the AI's own recommendation. On probation the area cap forces `ask`, but the AI's
    # recommendation under the mandate is still recorded, so agreeing spot-checks can earn the right back.
    if base["ai_recommendation"] in HUMAN_TIERS:
        raise SystemExit(f"the AI itself routed {a.change} to a human ({base['ai_recommendation']}); spot-checks grade changes the AI would clear")
    e = ledger.append(ws, "spotcheck", {**base, "result": a.result, "note": a.note, "simulated": a.simulated}, a.signer)
    print(f"ledger #{e['seq']}: {a.signer} {a.result}s with the AI on {a.change} (areas: {', '.join(base['areas'])})")
    return cmd_trust(a)


def cmd_escape(a) -> int:
    ws = _ws(a)
    p, _ = _load_pack(ws, a.change)
    base = _event_pack(ws, a.change, a.area or [p["primary_area"]])
    e = ledger.append(ws, "escape", {**base, "kind": a.kind, "note": a.note, "simulated": a.simulated}, a.signer)
    print(f"ledger #{e['seq']}: escape ({a.kind}) on {a.change}, AI-cleared: {base['ai_cleared']}, areas: {', '.join(base['areas'])}")
    return cmd_trust(a)


def cmd_keygen(a) -> int:
    priv, pub = keys.keygen(_ws(a), a.name, a.force)
    print(f"private key: {priv} (gitignored)\npublic key:  {pub}")
    return 0


def cmd_sign_mandate(a) -> int:
    sig = mandate_mod.sign(_ws(a), a.signer)
    print(f"mandate v{sig['version']} sha256 {sig['sha256'][:16]} signed by {sig['signer']} (recorded in the ledger)")
    return 0


def cmd_replay(a) -> int:
    ws = _ws(a)
    r = measure.replay(ws)
    measure.write(ws, r)
    print(measure.to_markdown(r))
    print(f"wrote {ws.measurement_dir}/results.json and results.md")
    return 0


def cmd_review_llm(a) -> int:
    ws = _ws(a)
    status = 0
    for change in a.changes:
        try:
            out = llm.run_review(ws, change, a.reviewer, a.repo, budget=a.context_chars)
        except llm.LLMError as e:
            print(f"error: {change}: {e}", file=sys.stderr)
            status = 1
            continue
        r = read_json(out)
        print(f"wrote {out.relative_to(ws.inputs)} ({r['model']}): " + ", ".join(f"{v['req']} {v['verdict']}" for v in r["requirement_verdicts"])
              + f"; {len(r['findings'])} findings, {len(r['refusals'])} refusals; tokens {r['runner']['usage']}")
    return status


def cmd_adjudicate(a) -> int:
    ws = _ws(a)
    status = 0
    for change in a.changes:
        try:
            out = llm.run_adjudication(ws, change, a.repo, a.adjudicator)
        except llm.LLMError as e:
            print(f"error: {change}: {e}", file=sys.stderr)
            status = 1
            continue
        if out is None:
            print(f"{change}: no disputes between the reviewers; adjudicator not run")
        else:
            r = read_json(out)
            print(f"wrote {out.relative_to(ws.inputs)} ({r['model']}): {len(r['rulings'])} rulings on {', '.join(r['disputes_given'])}")
    return status


def cmd_costs(a) -> int:
    out = costs_mod.write(_ws(a))
    print(f"wrote {out}")
    return 0


def parser() -> argparse.ArgumentParser:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--root", default=".", help="repo root holding mandate/, requirements/, packs/, ledger/, keys/ (default: .)")
    common.add_argument("--inputs", default=None, help="folder holding evidence/, reviews/ and the outputs packs/, ledger/, measurement/ "
                                                       "(default: --root; e.g. tests/fixtures for the simulated world)")
    common.add_argument("--repo", default=DEFAULT_REPO, help=f"git repo the code quotes are checked against (default: {DEFAULT_REPO})")
    common.add_argument("--mandate", default=None, help="mandate file relative to --root")
    ap = argparse.ArgumentParser(prog="countersign", description="AI review under a signed mandate; a named human countersigns.")
    sub = ap.add_subparsers(dest="cmd", required=True)

    def add(name, fn, help_):
        sp = sub.add_parser(name, parents=[common], help=help_)
        sp.set_defaults(fn=fn)
        return sp

    sp = add("review", cmd_review, "verify + decide + write the evidence pack for one or more changes")
    sp.add_argument("changes", nargs="+")
    sp.add_argument("-q", "--quiet", action="store_true")
    sp = add("route", cmd_route, "one line per change: tier and the rule that decided it")
    sp.add_argument("changes", nargs="*")
    sp.add_argument("--all", action="store_true")
    sp = add("sign", cmd_sign, "owner countersigns a pack; appended to the ledger")
    sp.add_argument("pack", help="packs/<change>/pack.json or a change id")
    sp.add_argument("--as", dest="signer", required=True)
    sp.add_argument("--decision", choices=["accept", "reject", "request-changes"])
    sp.add_argument("--note")
    add("verify-ledger", cmd_verify_ledger, "re-check the hash chain and every signature")
    add("trust", cmd_trust, "per-area clearance caps derived from the ledger")
    sp = add("spotcheck", cmd_spotcheck, "a human re-reviews an AI-cleared change")
    sp.add_argument("change")
    sp.add_argument("--as", dest="signer", required=True)
    sp.add_argument("--result", choices=["agree", "disagree"], required=True)
    sp.add_argument("--note", default="")
    sp.add_argument("--simulated", action="store_true", help="mark as a staged/demo event")
    sp = add("escape", cmd_escape, "record a revert or incident traced to a change")
    sp.add_argument("change")
    sp.add_argument("--as", dest="signer", required=True)
    sp.add_argument("--kind", choices=["revert", "incident"], required=True)
    sp.add_argument("--area", action="append", help="area the escape is traced to (repeatable; default: the change's primary area)")
    sp.add_argument("--note", default="")
    sp.add_argument("--simulated", action="store_true", help="mark as a staged/demo event")
    sp = add("keygen", cmd_keygen, "create an Ed25519 key pair for a named owner")
    sp.add_argument("--name", required=True)
    sp.add_argument("--force", action="store_true")
    sp = add("sign-mandate", cmd_sign_mandate, "the mandate owner signs the current mandate")
    sp.add_argument("--as", dest="signer", required=True)
    sp = add("review-llm", cmd_review_llm, "stage 2 from a model API (OpenAI-compatible): writes reviews/<change>/<reviewer>.json")
    sp.add_argument("changes", nargs="+")
    sp.add_argument("--reviewer", required=True, choices=sorted(llm.PRESETS))
    sp.add_argument("--context-chars", type=int, default=None, help=f"context budget in characters (default {llm.DEFAULT_CONTEXT_CHARS})")
    sp = add("adjudicate", cmd_adjudicate, "only if reviewers disagree: the adjudicator's rulings (advisory; never clears)")
    sp.add_argument("changes", nargs="+")
    sp.add_argument("--adjudicator", default=None, help="default: the mandate's adjudicator")
    add("costs", cmd_costs, "render docs/COSTS.md from measurement/costs.yaml")
    add("replay", cmd_replay, "run every change (incl. seeded mutants) and write measurement/results.{json,md}")
    return ap


def main(argv=None) -> int:
    a = parser().parse_args(argv)
    try:
        return a.fn(a)
    except (FileNotFoundError, FileExistsError, PermissionError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
