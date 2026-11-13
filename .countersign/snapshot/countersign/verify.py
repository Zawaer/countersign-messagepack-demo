"""Stage 3: check every piece of evidence a reviewer cites. No verified evidence, no finding.

Each evidence item comes back with `verified` (true/false) and a `note` saying exactly what was checked.
"""

from __future__ import annotations

import re
import subprocess
from copy import deepcopy


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


class Verifier:
    def __init__(self, repo: str, facts: dict, requirements: dict, line_tolerance: int = 3):
        self.repo, self.facts, self.tolerance = repo, facts, line_tolerance
        self.reqs = {r["id"]: r for r in requirements.get("requirements", [])}
        self.checks = {c["id"]: c for c in facts.get("checks", [])}
        # every run of a test, per check: the same name can appear in tests.targeted (head, passed) and in
        # tests.fail_without_fix (source reverted, failed by design), so a name alone is ambiguous.
        self.test_runs: dict[str, list[tuple[str, dict]]] = {}
        for c in facts.get("checks", []):
            for t in c.get("tests", []):
                self.test_runs.setdefault(t["name"], []).append((c["id"], t))
        self._files: dict[tuple[str, str], list[str] | None] = {}

    # --- per kind -------------------------------------------------------
    def _git_lines(self, rev: str, path: str) -> list[str] | None:
        key = (rev, path)
        if key not in self._files:
            r = subprocess.run(["git", "-C", self.repo, "show", f"{rev}:{path}"], capture_output=True)
            self._files[key] = r.stdout.decode("utf-8", "replace").splitlines() if r.returncode == 0 else None
        return self._files[key]

    def _apply_mutation(self, lines: list[str] | None, path: str) -> list[str] | None:
        """A seeded mutant is the branch head plus one recorded line edit; replay that edit so quotes check against the mutant."""
        mut = self.facts.get("mutation") or {}
        if lines is None or mut.get("file") != path or not mut.get("line") or mut.get("before") is None:
            return lines
        n = int(mut["line"]) - 1
        if n < len(lines) and mut["before"] in lines[n]:
            lines = [*lines[:n], lines[n].replace(mut["before"], mut.get("after", "")), *lines[n + 1:]]
        return lines

    def code(self, item: dict) -> tuple[bool, str]:
        rev_name = item.get("rev", "head")
        rev = self.facts.get(rev_name, rev_name) if rev_name in ("head", "base") else rev_name
        lines = self._git_lines(rev, item.get("file", ""))
        lines = self._apply_mutation(lines, item.get("file", "")) if rev_name == "head" else lines
        if lines is None:
            return False, f"{item.get('file')} does not exist at {rev_name} ({rev}) in {self.repo}"
        quote, line = _norm(item.get("quote", "")), int(item.get("line", 0))
        if not quote:
            return False, "empty quote"
        lo, hi = max(1, line - self.tolerance), min(len(lines), line + self.tolerance)
        hits = [n for n in range(lo, hi + 1) if quote in _norm(lines[n - 1])]
        if not hits:
            anywhere = [n for n, text in enumerate(lines, 1) if quote in _norm(text)]
            where = f"; it does occur at line {anywhere[0]}, outside tolerance" if anywhere else "; not found anywhere in the file"
            return False, f"quote not on {item['file']}:{line} ±{self.tolerance} at {rev_name}{where}"
        best = min(hits, key=lambda n: abs(n - line))
        off = f" (found at line {best}, {abs(best - line)} off)" if best != line else ""
        return True, f"quote matches {item['file']}:{line} at {rev_name} {rev[:8]}{off}"

    @staticmethod
    def _head_run(check_id: str) -> bool:
        """Runs on the change's own head (targeted, full suite, execution), not the source-reverted or base runs."""
        return "fail_without_fix" not in check_id and "base" not in check_id

    def test(self, item: dict) -> tuple[bool, str]:
        """Verified if a run on the change's head has the cited outcome. `check` on the item pins one run
        (which may then be a fail_without_fix run: citing a failure there is legitimate evidence)."""
        name = item.get("name", "")
        runs = self.test_runs.get(name)
        if not runs:
            return False, f"test {name!r} is not in facts.json"
        if item.get("check"):
            runs = [(cid, t) for cid, t in runs if cid == item["check"]]
            if not runs:
                return False, f"test {name!r} was not run by check {item['check']!r}"
            pool = runs
        else:
            pool = [(cid, t) for cid, t in runs if self._head_run(cid)]
        want = item.get("outcome")
        hits = [(cid, t) for cid, t in pool if not want or t["outcome"] == want]
        if hits:
            cid, t = hits[0]
            return True, f"facts.json {cid}: {t['outcome']}" + (" (new test)" if t.get("new") else "")
        seen = ", ".join(f"{cid}: {t['outcome']}" for cid, t in runs)
        other = [cid for cid, t in runs if not self._head_run(cid) and t["outcome"] == want]
        if other and not item.get("check"):
            return False, (f"reviewer says {want}, but on the change's head facts.json has {seen if pool else 'no run'}; "
                           f"{want} only in {', '.join(other)} (the source-reverted/base run): add check: {other[0]!r} to cite that run")
        return False, f"reviewer says {want}, facts.json says {seen}"

    def check(self, item: dict) -> tuple[bool, str]:
        c = self.checks.get(item.get("id", ""))
        if c is None:
            return False, f"check {item.get('id')!r} is not in facts.json"
        claimed = item.get("status") or item.get("outcome")
        if claimed and claimed != c["status"]:
            return False, f"reviewer says {claimed}, facts.json says {c['status']}"
        return True, f"facts.json: {c['id']} {c['status']}: {c.get('summary', '')}".rstrip(": ")

    def requirement(self, item: dict) -> tuple[bool, str]:
        r = self.reqs.get(item.get("req", ""))
        if r is None:
            return False, f"requirement {item.get('req')!r} is not in the requirement set"
        quote = _norm(item.get("quote", ""))
        if quote and quote not in _norm(r["text"]):
            return False, f"quote does not occur in {r['id']}"
        return True, f"{r['id']} text contains the quote" if quote else f"{r['id']} exists"

    def issue(self, item: dict) -> tuple[bool, str]:
        # The pipeline runs offline, so it cannot confirm what an issue page says. Unverifiable is not verified.
        return False, "issue text cannot be verified offline (not counted as evidence)"

    # --- dispatch -------------------------------------------------------
    def item(self, item: dict) -> dict:
        fn = getattr(self, str(item.get("kind")), None) if item.get("kind") in ("code", "test", "check", "requirement", "issue") else None
        ok, note = fn(item) if fn else (False, f"unknown evidence kind {item.get('kind')!r}")
        return {**item, "verified": ok, "note": note}


def verify_review(review: dict, v: Verifier) -> dict:
    """Annotate one reviewer's output. Findings with no verified evidence are marked rejected (kept, not dropped)."""
    out = deepcopy(review)
    for verdict in out.get("requirement_verdicts", []):
        verdict["evidence"] = [v.item(e) for e in verdict.get("evidence", [])]
        verdict["verified_count"] = sum(e["verified"] for e in verdict["evidence"])
    for f in out.get("findings", []):
        f["evidence"] = [v.item(e) for e in f.get("evidence", [])]
        f["verified_count"] = sum(e["verified"] for e in f["evidence"])
        f["status"] = "verified" if f["verified_count"] else "rejected"
        f["reviewer"] = out.get("reviewer")
        if f["status"] == "rejected":
            f["rejection_reason"] = "no cited evidence could be verified: " + "; ".join(e["note"] for e in f["evidence"]) if f["evidence"] else "no evidence cited"
    return out
