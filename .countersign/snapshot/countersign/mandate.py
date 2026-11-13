"""The review mandate: a versioned, owner-signed policy saying what the AI may clear alone.

Everything that decides a tier (areas, owners, weights, thresholds, hard rules) lives in the YAML,
not in code, so a judge or owner can read the policy without reading Python.
The signature lives next to it in <mandate>.sig and is also recorded in the ledger (type mandate_change).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from functools import lru_cache

import yaml

from . import keys, ledger
from .common import TIERS, Workspace, now_iso, read_json, sha256_hex, write_json

SENSITIVITY = ["low", "medium", "high", "critical"]


@lru_cache(maxsize=None)
def glob_regex(glob: str) -> re.Pattern:
    """Path glob: '**' matches across folders, '*' and '?' stay inside one path segment."""
    out, i = "", 0
    while i < len(glob):
        if glob.startswith("**/", i):
            out, i = out + "(?:.*/)?", i + 3
        elif glob.startswith("**", i):
            out, i = out + ".*", i + 2
        elif glob[i] == "*":
            out, i = out + "[^/]*", i + 1
        elif glob[i] == "?":
            out, i = out + "[^/]", i + 1
        else:
            out, i = out + re.escape(glob[i]), i + 1
    return re.compile(out + r"\Z")


def matches(path: str, globs: list[str]) -> bool:
    return any(glob_regex(g).match(path) for g in globs)


@dataclass
class Area:
    name: str
    owner: str
    paths: list[str]
    sensitivity: str
    max_ai_tier: str  # the most lenient tier the AI may assign alone in this area
    checks: list[str] = field(default_factory=list)  # deterministic checks that must pass for any change here
    description: str = ""
    confidential: bool | None = None  # None: inherit the repo-wide `confidential` setting


class Mandate:
    def __init__(self, data: dict, path: str, raw: bytes):
        self.data, self.path, self.sha256 = data, path, sha256_hex(raw)
        self.areas = [Area(name=n, **a) for n, a in data["areas"].items()]
        for a in self.areas:
            assert a.max_ai_tier in TIERS and a.sensitivity in SENSITIVITY, f"bad area {a.name}"

    def __getitem__(self, key):
        return self.data[key]

    @property
    def version(self) -> str:
        return str(self.data["version"])

    def area_for(self, path: str) -> Area:
        """First area whose globs match wins (order in the YAML is the precedence)."""
        for a in self.areas:
            if matches(path, a.paths):
                return a
        return self.area(self.data["default_area"])

    def area(self, name: str) -> Area:
        return next(a for a in self.areas if a.name == name)

    @property
    def reviewers(self) -> dict[str, dict]:
        """The reviewer registry: name -> vendor, role (reviewer | adjudicator), self_hostable, model."""
        return self.data.get("reviewers", {})

    def panel(self, area_names: list[str]) -> dict:
        """Who may read this change, from the registry and the confidentiality of the areas it touches.

        A change is confidential if the repo is, or any touched area says `confidential: true` (an area's own
        `false` overrides the repo default for that area only). In a confidential change only `self_hostable`
        reviewers may read the code; everyone else is excluded and the pack says so.
        Returns the participating reviewers (every one of them must say `met` for a clause to be proven),
        the adjudicator (if allowed) and the excluded entries with the reason."""
        repo_conf = bool(self.data.get("confidential", False))
        conf_areas = [a.name for a in self.areas if a.name in area_names and (a.confidential if a.confidential is not None else repo_conf)]
        confidential = bool(conf_areas)
        why = (f"confidential areas touched: {', '.join(conf_areas)}" if confidential
               else "repo and touched areas are not confidential")
        reviewers, adjudicator, excluded = [], None, []
        for name, r in self.reviewers.items():
            if confidential and not r.get("self_hostable", False):
                excluded.append({"name": name, "vendor": r.get("vendor"), "role": r.get("role"),
                                 "reason": f"not self-hostable; may not read code in a confidential change ({why})"})
            elif r.get("role") == "reviewer":
                reviewers.append(name)
            elif r.get("role") == "adjudicator" and adjudicator is None:
                adjudicator = name
        return {"confidential": confidential, "why": why, "reviewers": reviewers, "adjudicator": adjudicator, "excluded": excluded}

    def summary(self, ws: Workspace) -> dict:
        return {"path": self.path, "id": self.data["id"], "version": self.version, "owner": self.data["owner"],
                "sha256": self.sha256, "signature": signature_status(ws, self)}


def load(ws: Workspace) -> Mandate:
    raw = ws.mandate_path.read_bytes()
    return Mandate(yaml.safe_load(raw), ws.mandate_file, raw)


def _sig_path(ws: Workspace):
    return ws.mandate_path.with_name(ws.mandate_path.name + ".sig")


def signature_status(ws: Workspace, m: Mandate) -> dict:
    p = _sig_path(ws)
    if not p.exists():
        return {"valid": False, "reason": "mandate is not signed"}
    sig = read_json(p)
    if sig["sha256"] != m.sha256:
        return {"valid": False, "signed_by": sig["signer"], "reason": "mandate changed after it was signed"}
    if sig["signer"] != m["owner"]:
        return {"valid": False, "signed_by": sig["signer"], "reason": f"signed by {sig['signer']}, but the owner is {m['owner']}"}
    ok, why = keys.verify(ws, sig["signer"], m.sha256.encode(), sig["sig"])
    return {"valid": ok, "signed_by": sig["signer"], "signed_at": sig["ts"], "reason": why}


def sign(ws: Workspace, signer: str) -> dict:
    """The mandate owner signs sha256(mandate file); the change is also recorded in the ledger."""
    m = load(ws)
    if signer != m["owner"]:
        raise PermissionError(f"only the mandate owner ({m['owner']}) may sign it, not {signer}")
    sig = {"signer": signer, "sha256": m.sha256, "version": m.version, "ts": now_iso(),
           "sig": keys.sign(ws, signer, m.sha256.encode())}
    write_json(_sig_path(ws), sig)
    ledger.append(ws, "mandate_change", {"mandate": m.path, "version": m.version, "sha256": m.sha256}, signer)
    return sig
