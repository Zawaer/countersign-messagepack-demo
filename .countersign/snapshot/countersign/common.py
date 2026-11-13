"""Shared helpers: tiers, canonical JSON, hashing, and where files live."""

from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import yaml

TIERS = ["silent", "notify", "ask", "block"]  # least to most strict
HUMAN_TIERS = {"ask", "block"}
DEFAULT_REPO = os.environ.get("COUNTERSIGN_REPO", "/data/src/mp")  # the MessagePack clone; CI sets COUNTERSIGN_REPO


def strictest(*tiers: str) -> str:
    return max(tiers, key=TIERS.index)


def canonical(obj) -> bytes:
    """Canonical JSON bytes: sorted keys, no whitespace, UTF-8. Hashes and signatures are taken over this."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def read_json(path: Path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def base_change(change: str) -> str:
    """'2283-mut1' -> '2283'. Seeded mutants reuse the requirements of the change they mutate."""
    return re.sub(r"-mut\d+$", "", change)


def is_mutant(change: str) -> bool:
    return base_change(change) != change


@dataclass
class Workspace:
    """Where every stage reads and writes.

    root:   mandate/, requirements/, keys/, .keys/ (shared policy and identities)
    inputs: evidence/, reviews/ and the outputs packs/, ledger/, measurement/ (defaults to root).
            `--inputs tests/fixtures` is therefore a self-contained simulated world with its own ledger.
    """

    root: Path
    inputs: Path
    repo: str = DEFAULT_REPO
    mandate_file: str = "mandate/messagepack.mandate.yaml"

    @classmethod
    def at(cls, root=".", inputs=None, repo=DEFAULT_REPO, mandate=None) -> "Workspace":
        root = Path(root).resolve()
        ws = cls(root=root, inputs=Path(inputs).resolve() if inputs else root, repo=repo)
        if mandate:
            ws.mandate_file = mandate
        return ws

    # inputs
    def facts_path(self, change: str) -> Path:
        return self.inputs / "evidence" / change / "facts.json"

    def reviews(self, change: str) -> dict[str, dict]:
        """reviews/<change>/<reviewer>.json. Dotted names are not reviews: superseded passes (claude.v1.json) and the
        adjudicator's output (adjudication.gemini.json) live next to them; raw/ holds raw model responses."""
        folder = self.inputs / "reviews" / change
        return {p.stem: read_json(p) for p in sorted(folder.glob("*.json")) if "." not in p.stem} if folder.is_dir() else {}

    def adjudication_path(self, change: str) -> Path | None:
        folder = self.inputs / "reviews" / change
        found = sorted(folder.glob("adjudication.*.json")) if folder.is_dir() else []
        return found[0] if found else None

    def requirements(self, change: str) -> dict:
        for c in (change, base_change(change)):
            for folder in (self.inputs, self.root):
                p = folder / "requirements" / f"{c}.yaml"
                if p.exists():
                    data = yaml.safe_load(p.read_text(encoding="utf-8"))
                    data["_path"] = str(p.relative_to(folder)) if folder == self.root else str(p)
                    return data
        raise FileNotFoundError(f"no requirements/{change}.yaml (or {base_change(change)}.yaml)")

    def changes(self) -> list[str]:
        folder = self.inputs / "evidence"
        found = [p.name for p in folder.iterdir() if (p / "facts.json").exists()] if folder.is_dir() else []
        return sorted(found, key=lambda c: (base_change(c), c))

    # outputs
    @property
    def mandate_path(self) -> Path:
        return self.root / self.mandate_file

    def pack_dir(self, change: str) -> Path:
        return self.inputs / "packs" / change

    @property
    def ledger_path(self) -> Path:
        return self.inputs / "ledger" / "ledger.jsonl"

    @property
    def public_keys(self) -> Path:
        return self.root / "keys"

    @property
    def private_keys(self) -> Path:
        return self.root / ".keys"

    @property
    def measurement_dir(self) -> Path:
        return self.inputs / "measurement"
