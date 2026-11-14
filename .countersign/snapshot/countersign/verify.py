"""Stage 3: check every piece of evidence a reviewer cites. No verified evidence, no finding.

Each evidence item comes back with `verified` (true/false), `substantive` (true/false) and a `note` saying exactly
what was checked. Review JSON is untrusted model output (failure mode R7), so:
- only `substantive` items count towards a verdict or a finding: a code quote at head or base in a file the change
  touches, a test with a claimed outcome that matches, a check with a claimed status that matches. A requirement
  quote shows the reviewer read the clause, not that the code meets it: it may verify, it never counts.
- verified is not relevant (red team R1 to R4, docs/security/REDTEAM.md). Towards a requirement verdict:
  a code quote counts only on a line the change touched (added at head, removed at base; a seeded mutation's line
  too) and only if it is real code (MIN_QUOTE_CHARS non-space characters including an identifier; MIN_DOC_QUOTE_CHARS
  in a documentation file, where the changed text may be a short anchor); a test counts only
  if the change adds or edits it, or the clause lists it under `tests:`; a check never counts on its own (it may
  accompany, not satisfy, `min_verified_evidence`) unless the clause names it (`checks:`) or, for a `docs` clause,
  the mandate's requirement_checks for docs do (decide.decide_clauses applies that part: it has the mandate). Anything else that verifies is kept and shown as context.
  Findings keep the wider rule (any verified quote of real code in a touched file): a finding only routes stricter.
- `rev` must be `head` or `base`; `file` must be a relative path inside the change's diff (base may also cite the
  mandate's `decision.base_context_files`); git gets `--end-of-options`, so nothing a model writes becomes an option.
- a malformed item (wrong types) is rejected with a note, never a crash.
"""

from __future__ import annotations

import re
import subprocess
from copy import deepcopy


MIN_QUOTE_CHARS = 12  # non-whitespace characters a code quote needs to count (R1: a lone `}` verifies anywhere)
MIN_DOC_QUOTE_CHARS = 6  # in a documentation file (kind doc) the changed text can be a short anchor like `(#aot)`
_IDENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]{2,}")
_HUNK = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")
_METHOD = re.compile(r"^\s*(?:\[[^\]]*\]\s*)*(?:(?:public|private|protected|internal|static|async|virtual|override|sealed|unsafe)\s+)+"
                     r"[\w<>\[\],.?\s]*?\b(\w+)\s*\(")


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def real_code(quote: str, minimum: int = MIN_QUOTE_CHARS) -> bool:
    """Enough of a quote to point at something: `minimum` non-space characters and an identifier."""
    return len(re.sub(r"\s+", "", quote)) >= minimum and bool(_IDENT.search(quote))


def _test_method(name: str) -> str:
    return str(name).split("(")[0].rsplit(".", 1)[-1]


class Verifier:
    def __init__(self, repo: str, facts: dict, requirements: dict, line_tolerance: int = 3, base_context_files: list[str] | None = None):
        self.repo, self.facts, self.tolerance = repo, facts, line_tolerance
        self.diff_paths = {f["path"] for f in facts.get("diff", {}).get("by_file", [])}
        self.doc_paths = {f["path"] for f in facts.get("diff", {}).get("by_file", []) if f.get("kind") == "doc"}
        self.base_context = set(base_context_files or [])
        self.reqs = {r["id"]: r for r in requirements.get("requirements", [])}
        self.checks = {c["id"]: c for c in facts.get("checks", [])}
        # every run of a test, per check: the same name can appear in tests.targeted (head, passed) and in
        # tests.fail_without_fix (source reverted, failed by design), so a name alone is ambiguous.
        self.test_runs: dict[str, list[tuple[str, dict]]] = {}
        for c in facts.get("checks", []):
            for t in c.get("tests", []):
                self.test_runs.setdefault(t["name"], []).append((c["id"], t))
        self._files: dict[tuple[str, str], list[str] | None] = {}
        self._changed: dict[str, dict[str, set[int]]] | None = None
        self._edited: set[str] | None = None
        self.new_tests = {t["name"] for runs in self.test_runs.values() for _, t in runs if t.get("new") is True}

    # --- what the change touched (red team R1 to R4) --------------------------
    def changed_lines(self, rev_name: str, path: str) -> set[int]:
        """Line numbers the change touched in `path`: added at head, removed at base (git diff -U0 base head).
        A seeded mutation's line counts as touched at head."""
        if self._changed is None:
            self._changed = {"head": {}, "base": {}}
            base, head = self.facts.get("base"), self.facts.get("head")
            if all(isinstance(r, str) and r and not r.startswith("-") for r in (base, head)):
                r = subprocess.run(["git", "-C", self.repo, "-c", "core.quotePath=off", "diff", "-U0", "--no-color", "--no-ext-diff",
                                    "--no-renames", "--end-of-options", base, head], capture_output=True)
                cur = cur_old = None
                header = False
                for line in r.stdout.decode("utf-8", "replace").splitlines() if r.returncode == 0 else []:
                    if line.startswith("diff --git "):
                        header, cur, cur_old = True, None, None
                    elif header and line.startswith("+++ "):
                        cur = line[6:] if line.startswith("+++ b/") else None
                    elif header and line.startswith("--- "):
                        cur_old = line[6:] if line.startswith("--- a/") else None
                    elif (m := _HUNK.match(line)):
                        header = False
                        a, b, c, d = int(m[1]), int(m[2] if m[2] is not None else 1), int(m[3]), int(m[4] if m[4] is not None else 1)
                        if cur_old:
                            self._changed["base"].setdefault(cur_old, set()).update(range(a, a + b))
                        if cur:
                            self._changed["head"].setdefault(cur, set()).update(range(c, c + d))
            mut = self.facts.get("mutation") or {}
            if mut.get("file") and isinstance(mut.get("line"), int):
                self._changed["head"].setdefault(mut["file"], set()).add(mut["line"])
        return self._changed.get(rev_name, {}).get(path, set())

    def edited_tests(self) -> set[str]:
        """Method names of tests whose body (definition line to its closing brace) has a line added at head."""
        if self._edited is None:
            self._edited = set()
            for path in sorted(self.diff_paths):
                touched = self.changed_lines("head", path)
                lines = self._git_lines(self.facts.get("head", ""), path) if touched and path.endswith(".cs") else None
                for i, text in enumerate(lines or []):
                    m = _METHOD.match(text)
                    if not m:
                        continue
                    end, depth, opened = i, 0, False
                    for j in range(i, min(len(lines), i + 400)):
                        depth += lines[j].count("{") - lines[j].count("}")
                        opened = opened or "{" in lines[j]
                        end = j
                        if (opened and depth <= 0) or (not opened and lines[j].rstrip().endswith(";")):
                            break
                    if any(n in touched for n in range(i + 1, end + 2)):
                        self._edited.add(m[1])
        return self._edited

    # --- per kind -------------------------------------------------------
    def _git_lines(self, rev: str, path: str) -> list[str] | None:
        key = (rev, path)
        if key not in self._files:
            r = subprocess.run(["git", "-C", self.repo, "show", "--end-of-options", f"{rev}:{path}"], capture_output=True)
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
        rev_name, path = item.get("rev", "head"), item.get("file", "")
        if rev_name not in ("head", "base"):
            return False, f"evidence must cite head or base, not {str(rev_name)[:40]!r}"
        if not isinstance(path, str) or not path or path.startswith(("-", "/")) or ".." in path.split("/") or "\\" in path:
            return False, f"not a relative repository path: {str(path)[:80]!r}"
        if path not in self.diff_paths and not (rev_name == "base" and path in self.base_context):
            return False, f"{path} is not in the change's diff" + (" (nor in base_context_files)" if rev_name == "base" else "")
        if not isinstance(item.get("quote", ""), str) or isinstance(item.get("line", 0), bool) or not isinstance(item.get("line", 0), int):
            return False, "malformed evidence item: line must be an integer and quote a string"
        rev = self.facts.get(rev_name)
        if not isinstance(rev, str) or not rev or rev.startswith("-"):
            return False, f"facts.json has no usable {rev_name} revision"
        lines = self._git_lines(rev, path)
        lines = self._apply_mutation(lines, path) if rev_name == "head" else lines
        if lines is None:
            return False, f"{path} does not exist at {rev_name} ({rev}) in {self.repo}"
        quote, line = _norm(item.get("quote", "")), item.get("line", 0)
        if not quote:
            return False, "empty quote"
        lo, hi = max(1, line - self.tolerance), min(len(lines), line + self.tolerance)
        hits = [n for n in range(lo, hi + 1) if quote in _norm(lines[n - 1])]
        if not hits:
            anywhere = [n for n, text in enumerate(lines, 1) if quote in _norm(text)]
            where = f"; it does occur at line {anywhere[0]}, outside tolerance" if anywhere else "; not found anywhere in the file"
            return False, f"quote not on {item['file']}:{line} ±{self.tolerance} at {rev_name}{where}"
        touched = self.changed_lines(rev_name, path)
        best = min(hits, key=lambda n: (n not in touched, abs(n - line), n))  # a touched line first, then the nearest
        off = f" (found at line {best}, {abs(best - line)} off)" if best != line else ""
        self._last_code = {"line": best, "touched": best in touched}
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
    def item(self, item, req: str | None = None, use: str = "verdict") -> dict:
        """Verify one evidence item. `use` is what it is cited for: "verdict" (a requirement verdict on clause `req`),
        "finding" or "refutation". `substantive` says whether it counts there; `context` explains why it doesn't."""
        if not isinstance(item, dict):
            return {"kind": "malformed", "raw": str(item)[:200], "verified": False, "substantive": False, "note": "malformed evidence item: not an object"}
        kind = item.get("kind")
        fn = getattr(self, kind, None) if kind in ("code", "test", "check", "requirement", "issue") else None
        self._last_code = None
        try:
            ok, note = fn(item) if fn else (False, f"unknown evidence kind {kind!r}")
        except (TypeError, ValueError, AttributeError, KeyError) as e:
            ok, note = False, f"malformed evidence item ({type(e).__name__})"
        out = {**item, "verified": ok, "substantive": ok and self.substantive(item), "note": note}
        if out["substantive"]:
            why = self.irrelevant(item, req, use)
            if why:
                out["substantive"], out["context"] = False, why
                out["note"] = f"{note}; context only, not counted: {why}"
        return out

    def irrelevant(self, item: dict, req: str | None, use: str) -> str | None:
        """Why a verified item says nothing about this change (red team R1 to R4), or None if it counts."""
        kind = item.get("kind")
        if kind == "code":
            minimum = MIN_DOC_QUOTE_CHARS if item.get("file") in self.doc_paths else MIN_QUOTE_CHARS
            if not real_code(_norm(item.get("quote", "")), minimum):
                return f"the quote is too short to point at anything (fewer than {minimum} non-space characters or no identifier)"
            if use == "verdict" and not (self._last_code or {}).get("touched"):
                side = "added at head" if item.get("rev", "head") == "head" else "removed at base"
                return f"line {(self._last_code or {}).get('line')} of {item.get('file')} is not a line this change touched ({side})"
        elif kind == "test" and use == "verdict":
            name = item.get("name", "")
            listed = (self.reqs.get(req) or {}).get("tests") or []
            if name not in listed and name not in self.new_tests and _test_method(name) not in self.edited_tests():
                return f"test {name} is not added or edited by this change, nor listed in the clause's tests:"
        return None

    @staticmethod
    def substantive(item: dict) -> bool:
        """Evidence about the change itself (before the relevance rules in `irrelevant`). Only these count towards
        min_verified_evidence and a finding's support."""
        kind = item.get("kind")
        if kind == "code":
            return True  # already confined to head/base and the change's files
        if kind == "test":
            return bool(item.get("outcome"))
        if kind == "check":
            return bool(item.get("status") or item.get("outcome"))
        return False  # requirement quotes, issue text


def _items(x) -> list:
    return x if isinstance(x, list) else []


def verify_review(review: dict, v: Verifier) -> dict:
    """Annotate one reviewer's output. Findings with no substantive verified evidence are marked rejected (kept, not
    dropped). `verified_count` counts every verified item (for display); `substantive_count` is what decides."""
    out = deepcopy(review)
    out["requirement_verdicts"] = [x for x in _items(out.get("requirement_verdicts")) if isinstance(x, dict)]
    out["findings"] = [x for x in _items(out.get("findings")) if isinstance(x, dict)]
    for verdict in out["requirement_verdicts"]:
        verdict["evidence"] = [v.item(e, verdict.get("req"), "verdict") for e in _items(verdict.get("evidence"))]
        verdict["verified_count"] = sum(e["verified"] for e in verdict["evidence"])
        # a check never satisfies the minimum on its own (R3): it counts only next to relevant code or test evidence,
        # unless the clause itself names it (`checks:` in the requirement file, owner-authored like `tests:`)
        listed = set((v.reqs.get(verdict.get("req")) or {}).get("checks") or [])
        alone = [e for e in verdict["evidence"] if e["substantive"] and e.get("kind") == "check" and e.get("id") not in listed]
        core = sum(e["substantive"] for e in verdict["evidence"]) - len(alone)
        verdict["substantive_count"] = core + (len(alone) if core else 0)
        if alone and not core:
            for e in alone:
                e["substantive"], e["context"] = False, "a check may accompany code or test evidence, never count on its own"
                e["note"] += f"; context only, not counted: {e['context']}"
    for f in out["findings"]:
        f["evidence"] = [v.item(e, None, "finding") for e in _items(f.get("evidence"))]
        f["verified_count"] = sum(e["verified"] for e in f["evidence"])
        f["substantive_count"] = sum(e["substantive"] for e in f["evidence"])
        f["status"] = "verified" if f["substantive_count"] else "rejected"
        f["reviewer"] = out.get("reviewer")
        f.setdefault("id", "?")
        f["severity"] = f.get("severity") if f.get("severity") in ("blocker", "major", "minor", "info") else "major"
        f.setdefault("title", "")
        f.setdefault("claim", "")
        if f["status"] == "rejected":
            f["rejection_reason"] = (("no cited evidence about the change could be verified: " + "; ".join(e["note"] for e in f["evidence"]))
                                     if f["evidence"] else "no evidence cited")
    if "refutations" in out:
        out["refutations"] = [x for x in _items(out["refutations"]) if isinstance(x, dict)]
    for r in out.get("refutations", []):  # a later pass saying an earlier finding is not a defect (see decide.carry_forward)
        r["evidence"] = [v.item(e, None, "refutation") for e in _items(r.get("evidence"))]
        r["verified_count"] = sum(e["verified"] for e in r["evidence"])
    return out
