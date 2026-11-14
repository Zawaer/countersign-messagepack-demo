"""Append-only, hash-chained, signed ledger (ledger/ledger.jsonl).

Each line is one entry:
  {"seq", "ts", "type", "payload", "prev", "signer", "hash", "sig"}
  hash = sha256(canonical(entry without hash and sig))
  prev = hash of the previous entry (64 zeros for the first)
  sig  = Ed25519 signature by `signer` over the ASCII hex `hash`
Editing, deleting, reordering or inserting a line breaks the chain or a signature; verify() reports where.
"""

from __future__ import annotations

import json

from . import keys
from .common import Workspace, canonical, now_iso, read_json, sha256_hex

GENESIS = "0" * 64
TYPES = {"signoff", "spotcheck", "escape", "canary", "mandate_change"}


def read(ws: Workspace) -> list[dict]:
    if not ws.ledger_path.exists():
        return []
    return [json.loads(line) for line in ws.ledger_path.read_text(encoding="utf-8").splitlines() if line.strip()]


def entry_hash(entry: dict) -> str:
    return sha256_hex(canonical({k: v for k, v in entry.items() if k not in ("hash", "sig")}))


def append(ws: Workspace, type_: str, payload: dict, signer: str) -> dict:
    if type_ not in TYPES:
        raise ValueError(f"unknown ledger entry type {type_!r}")
    entries = read(ws)
    entry = {
        "seq": len(entries) + 1,
        "ts": now_iso(),
        "type": type_,
        "payload": payload,
        "prev": entries[-1]["hash"] if entries else GENESIS,
        "signer": signer,
    }
    entry["hash"] = entry_hash(entry)
    entry["sig"] = keys.sign(ws, signer, entry["hash"].encode())
    ws.ledger_path.parent.mkdir(parents=True, exist_ok=True)
    with ws.ledger_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, sort_keys=True, ensure_ascii=False) + "\n")
    return entry


def verify(ws: Workspace) -> tuple[list[str], list[str]]:
    """Returns (problems, warnings). Problems mean the ledger cannot be trusted from that line on."""
    problems, warnings = [], []
    if not ws.ledger_path.exists():
        return problems, ["no ledger yet"]
    prev = GENESIS
    lines = ws.ledger_path.read_text(encoding="utf-8").splitlines()
    for n, line in enumerate(lines, start=1):
        try:
            e = json.loads(line)
        except json.JSONDecodeError:
            problems.append(f"line {n}: not valid JSON")
            continue
        if not isinstance(e, dict):
            problems.append(f"line {n}: not a ledger entry (expected a JSON object)")
            prev = None
            continue
        if e.get("type") not in TYPES:
            problems.append(f"line {n}: unknown entry type {e.get('type')!r}")
        if e.get("seq") != n:
            problems.append(f"line {n}: seq is {e.get('seq')}, expected {n} (entry removed, inserted or reordered)")
        if e.get("prev") != prev:
            problems.append(f"line {n}: prev does not match the hash of line {n - 1} (chain broken)")
        if entry_hash(e) != e.get("hash"):
            problems.append(f"line {n}: content does not match its hash (entry edited after it was written)")
        ok, why = keys.verify(ws, e.get("signer", "?"), str(e.get("hash")).encode(), e.get("sig", ""))
        if not ok:
            problems.append(f"line {n}: {why}")
        prev = e.get("hash")
        # A signed pack that was changed afterwards is not a broken ledger, but the signature no longer covers it.
        p = e.get("payload")
        if not isinstance(p, dict):
            problems.append(f"line {n}: payload is not an object")
            continue
        if e.get("type") == "signoff" and p.get("pack_path"):
            pack_file = (ws.root / str(p["pack_path"])).resolve()
            if not pack_file.is_relative_to(ws.root.resolve()):
                problems.append(f"line {n}: pack_path {p['pack_path']!r} points outside the workspace")
                continue
            try:
                current = sha256_hex(canonical(read_json(pack_file))) if pack_file.is_file() else None
            except (OSError, ValueError):
                current = "unreadable"
            if current is not None and current != p.get("pack_sha256"):
                warnings.append(f"line {n}: {p['pack_path']} changed since {e.get('signer')} signed it (re-review needed)")
    return problems, warnings
