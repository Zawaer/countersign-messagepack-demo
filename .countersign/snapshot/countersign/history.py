"""Historical replay: route real, merged upstream PRs with Countersign's deterministic stage only, then compare with
what actually happened to them (reverted / needed a follow-up fix = an "escape").

Real data, not simulated: the PRs, their diffs and the escapes come from MessagePack-CSharp's own history
(`--repo`, a full clone; read-only: git diff/show/ls-tree). The escape labels are our judgement, made by the rule in
measurement/history/README.md, and every label is listed with its link in measurement/history/labels.yaml.

Facts from the diff (no build, no models):
- diff.by_file with `kind` (source / test / generated / doc / build), the same rules as evidence/scripts/facts.py
- public_api: a PublicAPI.*.txt or AnalyzerReleases.*.md change, or a public/protected declaration added or removed
  in a shipped library (src/MessagePack/**, src/MessagePack.Annotations/**)
- checks, in one of two modes:
    diff-only    nothing was run, so every mandated check is absent (the mandate routes that to `ask`)
    ci-credited  build / tests.targeted / tests.full_suite credited as `pass` because the PR was merged with green
                 upstream CI (not re-run by us); tests.fail_without_fix credited as `pass` when the PR changes tests
                 alongside source (a proxy: we did not revert the source and run them)
  ci-credited is the lenient mode: it is the most a facts stage could clear, so it is the honest stress test.

Routing is countersign.decide.decide() with the signed mandate as written, no reviews and no requirement clauses.
AI reviewers can only add drivers (findings, refusals, disagreement), never remove one (unanimity, D8), so the tier
here is the MOST LENIENT tier Countersign could have given: escapes in the cleared bucket are an upper bound.
"""

from __future__ import annotations

import re
import subprocess
from collections import Counter
from pathlib import Path

import yaml

from . import decide as decide_mod
from .common import HUMAN_TIERS, TIERS, Workspace, write_json
from .mandate import load

MODES = ("ci-credited", "diff-only")
SHIPPED = re.compile(r"src/(MessagePack|MessagePack\.Annotations)/")
DECL = re.compile(r"^\s*(public|protected)\s+(?!override\b)[^=;]*?\b(class|struct|record|interface|enum|delegate|event|const|static|readonly|virtual|abstract|sealed|partial|[\w<>\[\],?.]+\s+\w+\s*[({;=])")
UPSTREAM = "https://github.com/MessagePack-CSharp/MessagePack-CSharp"


class Repo:
    def __init__(self, path: str):
        self.path = path

    def git(self, *a: str) -> str:
        return subprocess.run(["git", "-C", self.path, *a], capture_output=True, text=True, check=True).stdout

    def first_parent(self, sha: str) -> str:
        return self.git("rev-list", "--parents", "-n1", sha).split()[1]


def kind(path: str, tt_files: set[str]) -> str:
    """Same rules as evidence/scripts/facts.py: generated, doc, build, test, source."""
    if path.endswith(".g.cs"):
        return "generated"
    if (path.endswith((".md", ".txt")) and "PublicAPI" not in path) or path.startswith("doc/"):
        return "build" if path.endswith(("AnalyzerReleases.Unshipped.md", "AnalyzerReleases.Shipped.md")) else "doc"
    if path.endswith((".csproj", ".props", ".targets", ".sln", ".json", ".yml", ".yaml")) or "PublicAPI" in path:
        return "build"
    if path.startswith("tests/"):
        return "test"
    if path.endswith(".cs") and path[:-3] + ".tt" in tt_files:
        return "generated"
    return "source"


def _public_decl_delta(repo: Repo, base: str, head: str) -> list[str]:
    """Public/protected declaration lines added or removed in shipped libraries (a line that only moved cancels out)."""
    added, removed = Counter(), Counter()
    cur = None
    for line in repo.git("diff", "-U0", base, head, "--", "src/MessagePack/", "src/MessagePack.Annotations/").splitlines():
        if line.startswith("+++ "):
            cur = line[6:] if line.startswith("+++ b/") else None
        elif cur and cur.endswith(".cs") and not cur.endswith(".g.cs") and line[:1] in "+-" and not line.startswith(("+++", "---")):
            if DECL.match(line[1:]):
                (added if line[0] == "+" else removed)[re.sub(r"\s+", " ", line[1:].strip())] += 1
    return sorted((added - removed).keys() | (removed - added).keys())


def facts_from_diff(repo: Repo, pr: dict, mode: str) -> dict:
    head = pr["merge_commit"]
    base = repo.first_parent(head)
    tt = {f for f in repo.git("ls-tree", "-r", "--name-only", head).split() if f.endswith(".tt")}
    by = []
    for line in repo.git("diff", "--numstat", base, head).splitlines():
        a, d, p = line.split("\t", 2)
        p = re.sub(r"\{.* => (.*)\}", r"\1", p).replace("//", "/")  # renames: keep the new path
        by.append({"path": p, "ins": int(a) if a != "-" else 0, "del": int(d) if d != "-" else 0, "kind": kind(p, tt)})
    api_files = [f["path"] for f in by if "PublicAPI" in f["path"] or "AnalyzerReleases" in f["path"]]
    decls = _public_decl_delta(repo, base, head)
    changed = bool(api_files or decls)
    checks = [{"id": "public_api", "status": "fail" if changed else "pass", "changed": changed,
               "summary": ("public surface changed: " + "; ".join(api_files + decls[:5])) if changed else "no public API change found in the diff",
               "tool": "diff scan (PublicAPI.*.txt, AnalyzerReleases.*.md, public/protected declarations in shipped libraries)"}]
    if mode == "ci-credited":
        credited = "credited: merged with green upstream CI (not re-run here)"
        checks += [{"id": c, "status": "pass", "summary": credited, "credited": True} for c in ("build", "tests.targeted", "tests.full_suite")]
        src = any(f["kind"] == "source" for f in by)
        tests = any(f["kind"] == "test" for f in by)
        if src and tests:
            checks.append({"id": "tests.fail_without_fix", "status": "pass", "credited": True,
                           "summary": "proxy: tests changed alongside source (not run with the source reverted)"})
    return {"change": f"PR#{pr['number']}", "head": head[:8], "base": base[:8], "commit_message": pr["title"],
            "diff": {"files": len(by), "insertions": sum(f["ins"] for f in by), "deletions": sum(f["del"] for f in by), "by_file": by},
            "checks": checks, "mode": mode, "simulated": False}


def route(facts: dict, m) -> dict:
    """Deterministic stage only: the signed mandate as written, no reviews, no clauses, no trust-ledger state."""
    d = decide_mod.decide(facts, {}, {"requirements": []}, m, {"valid": True, "reason": "replay applies the signed mandate as written"}, {})
    return {"tier": d["tier"], "score": d["risk"]["score"], "primary_area": d["primary_area"],
            "why": [f"{w['source']}: {w['id']}" for w in d["decisive"]],
            "risk_factors": {f["factor"]: f["points"] for f in d["risk"]["factors"] if f["points"]}}


def load_labels(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def replay(ws: Workspace, labels_path: Path | None = None) -> dict:
    labels_path = labels_path or ws.root / "measurement" / "history" / "labels.yaml"
    lab = load_labels(labels_path)
    repo = Repo(ws.repo)
    m = load(ws)
    escapes = {e["pr"]: e for e in lab["escapes"]}
    excluded = {e["pr"] for e in lab.get("excluded", [])}
    dataset = load_labels(labels_path.with_name("dataset.yaml"))["dataset"]
    rows = []
    for pr in dataset:
        if pr["number"] in excluded:
            continue
        row = {"pr": pr["number"], "title": pr["title"], "merged": pr["merged"], "url": f"{UPSTREAM}/pull/{pr['number']}",
               "escape": pr["number"] in escapes, "confidence": escapes.get(pr["number"], {}).get("confidence")}
        for mode in MODES:
            f = facts_from_diff(repo, pr, mode)
            r = route(f, m)
            row[mode] = {**r, "cleared": r["tier"] not in HUMAN_TIERS}
            row["files"], row["lines"] = f["diff"]["files"], f["diff"]["insertions"] + f["diff"]["deletions"]
        rows.append(row)
    out = {"source": f"{UPSTREAM} (clone at {ws.repo})", "mandate": {"path": m.path, "version": m.version, "sha256": m.sha256},
           "simulated": False, "labels": str(labels_path.relative_to(ws.root)), "prs": rows, "modes": {}}
    for mode in MODES:
        out["modes"][mode] = summarize(rows, mode)
    out["unattributed_regressions"] = lab.get("unattributed", [])
    return out


def summarize(rows: list[dict], mode: str, min_conf: str = "medium") -> dict:
    keep = {"high": {"high"}, "medium": {"high", "medium"}}[min_conf]
    esc = lambda r: r["escape"] and r["confidence"] in keep  # noqa: E731
    table = {(e, c): 0 for e in (True, False) for c in (True, False)}
    for r in rows:
        table[(esc(r), r[mode]["cleared"])] += 1
    tiers = Counter(r[mode]["tier"] for r in rows)
    n = len(rows)
    missed = [r for r in rows if esc(r) and r[mode]["cleared"]]
    return {
        "n": n, "tiers": {t: tiers.get(t, 0) for t in TIERS},
        "routed_to_humans": n - sum(r[mode]["cleared"] for r in rows),
        "share_routed_to_humans": round((n - sum(r[mode]["cleared"] for r in rows)) / n, 3) if n else None,
        "escapes": table[(True, True)] + table[(True, False)],
        "escapes_high_confidence": sum(r["escape"] and r["confidence"] == "high" for r in rows),
        "confusion": {"escape_routed": table[(True, False)], "escape_cleared": table[(True, True)],
                      "clean_routed": table[(False, False)], "clean_cleared": table[(False, True)]},
        "escapes_cleared": [{"pr": r["pr"], "title": r["title"], "tier": r[mode]["tier"], "why": r[mode]["why"]} for r in missed],
        "escape_recall": round(table[(True, False)] / (table[(True, True)] + table[(True, False)]), 3) if table[(True, True)] + table[(True, False)] else None,
        "escape_rate_routed": _rate(table[(True, False)], table[(True, False)] + table[(False, False)]),
        "escape_rate_cleared": _rate(table[(True, True)], table[(True, True)] + table[(False, True)]),
    }


def _rate(a: int, b: int):
    return round(a / b, 3) if b else None


def write(ws: Workspace, result: dict) -> Path:
    d = ws.root / "measurement" / "history"
    write_json(d / "results.json", result)
    (d / "results.md").write_text(to_markdown(result), encoding="utf-8")
    return d


def to_markdown(r: dict) -> str:
    out = ["# Historical replay: real MessagePack-CSharp PRs routed by Countersign's deterministic stage", "",
           f"**Real data** (`simulated: false`): {len(r['prs'])} merged upstream PRs, their real diffs, and escapes labelled by the rule in "
           "[README.md](README.md) (every label and its link: [labels.yaml](labels.yaml)). "
           f"Mandate `{r['mandate']['path']}` v{r['mandate']['version']} as signed, sha256 `{r['mandate']['sha256'][:12]}`; no reviews, no models, no builds.", "",
           "Reviewers can only add reasons to route to a human, never remove one, so these tiers are the most lenient Countersign could give: "
           "escapes in the cleared bucket are an upper bound on what the AI would have let through.", ""]
    for mode in MODES:
        s = r["modes"][mode]
        c = s["confusion"]
        out += [f"## Mode `{mode}`", "",
                f"- Routed to a human (ask/block): **{s['routed_to_humans']} of {s['n']}** ({s['share_routed_to_humans']:.0%}); "
                f"tiers: " + ", ".join(f"{t} {k}" for t, k in s["tiers"].items()),
                f"- Escapes in the dataset: {s['escapes']} ({s['escapes_high_confidence']} high-confidence)",
                f"- **Escapes Countersign would have cleared: {c['escape_cleared']} of {s['escapes']}**", "",
                "| | routed to human | cleared by AI |", "|---|---:|---:|",
                f"| escape (reverted / follow-up fix) | {c['escape_routed']} | {c['escape_cleared']} |",
                f"| no escape found | {c['clean_routed']} | {c['clean_cleared']} |", ""]
        if s["escapes_cleared"]:
            out += ["Escapes in the cleared bucket (named, not hidden):", ""]
            out += [f"- #{x['pr']} {x['title']} -> {x['tier']} ({'; '.join(x['why'])})" for x in s["escapes_cleared"]]
            out.append("")
    out += ["## Every PR", "", "| PR | Merged | Title | Files | Lines | Escape | ci-credited tier | score | diff-only tier | Decisive drivers (ci-credited) |",
            "|---|---|---|---:|---:|---|---|---:|---|---|"]
    for p in r["prs"]:
        ci = p["ci-credited"]
        out.append(f"| [#{p['pr']}]({p['url']}) | {p['merged']} | {p['title'][:70].replace('|', '/')} | {p['files']} | {p['lines']} | "
                   f"{('yes (' + p['confidence'] + ')') if p['escape'] else '-'} | {ci['tier']} | {ci['score']} | {p['diff-only']['tier']} | "
                   f"{'; '.join(ci['why'])[:160]} |")
    if r.get("unattributed_regressions"):
        out += ["", "## Regressions we could not attribute to one PR in the set", ""]
        out += [f"- {u['issue']}: {u['what']} ({u['why_unattributed']})" for u in r["unattributed_regressions"]]
    return "\n".join(out) + "\n"
