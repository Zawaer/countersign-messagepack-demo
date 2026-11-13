"""Countersign inside a GitHub pull-request flow.

    python -m countersign.github check     (CI, on pull_request)   pack -> sticky comment, commit status, review request
    python -m countersign.github command   (CI, on issue_comment)  /countersign accept|reject|request-changes|status
    python -m countersign.github sign-pr   (owner's machine)       sign the PR's pack with the owner's own key, post it

The owner's private key never reaches CI. `sign-pr` builds the same pack CI built (packs are deterministic), signs a
ledger entry locally and posts it as a `/countersign <decision>` comment. CI then checks that the commenter is the
GitHub login the config maps to the pack's owner, that the entry is signed by that owner's key (keys/<owner>.pub from
the protected default branch), that it covers exactly this pack and chains onto the ledger tip, and only then appends
it to the ledger branch and flips the `countersign/tier` status. Without a valid signature nothing changes.

GitHub API calls use urllib with GITHUB_TOKEN (CI) or `gh` (owner's machine). Nothing here reads or prints secrets.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

import yaml
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from . import keys, ledger, pack as pack_mod
from .common import HUMAN_TIERS, Workspace, canonical, now_iso, sha256_hex, write_json

MARKER = "<!-- countersign:sticky -->"
FENCE = "countersign-signoff"
COMMAND = re.compile(r"^/countersign\s+(accept|reject|request-changes|status)\b[ \t]*(.*)$", re.M)
SIGNED_BLOCK = re.compile(r"```" + FENCE + r"\s*\n(.*?)\n```", re.S)


# --- config, workspace, live facts ---------------------------------------------------------------------------

def load_config(path: str) -> dict:
    cfg = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    cfg.setdefault("owners", {})
    cfg.setdefault("branch_pattern", r"ju26-issue-(?P<change>\d+)")
    cfg.setdefault("ledger_branch", "countersign-ledger")
    cfg.setdefault("status_context", "countersign/tier")
    cfg.setdefault("recorded", True)
    return cfg


def change_for_branch(cfg: dict, branch: str) -> str | None:
    m = re.fullmatch(cfg["branch_pattern"], branch)
    return m.group("change") if m else None


def workspace(snapshot: str, repo_dir: str, ledger_text: str | None) -> Workspace:
    """A throwaway copy of the pinned snapshot with the authoritative ledger dropped in, so building a pack never
    touches a tracked file. Packs do not depend on where the snapshot or the git repo live (same inputs, same hash)."""
    tmp = Path(tempfile.mkdtemp(prefix="countersign-"))
    shutil.copytree(snapshot, tmp / "ws", ignore=shutil.ignore_patterns("packs", "__pycache__", ".keys"))
    ws = Workspace.at(tmp / "ws", None, str(Path(repo_dir).resolve()))
    if ledger_text is not None:
        ws.ledger_path.parent.mkdir(parents=True, exist_ok=True)
        ws.ledger_path.write_text(ledger_text, encoding="utf-8")
    return ws


def _git(repo_dir: str, *args: str) -> str:
    return subprocess.run(["git", "-C", repo_dir, *args], check=True, capture_output=True, text=True).stdout


def live_facts(repo_dir: str, base: str, head: str) -> dict:
    """The part of facts.json CI recomputes on every run: which commits, which files, how many lines."""
    head = _git(repo_dir, "rev-parse", head).strip()
    mb = _git(repo_dir, "merge-base", base, head).strip()
    files = {}
    for line in _git(repo_dir, "diff", "--numstat", "--no-renames", mb, head).splitlines():
        ins, dele, path = line.split("\t", 2)
        files[path] = (0 if ins == "-" else int(ins), 0 if dele == "-" else int(dele))
    return {"base": mb, "head": head, "files": files,
            "insertions": sum(i for i, _ in files.values()), "deletions": sum(d for _, d in files.values())}


def mismatches(p: dict, live: dict) -> list[str]:
    """Differences between the evidence the pack was built from and the PR as it is now. Any difference means the
    recorded reviews are about other code, so nothing can clear and nobody can countersign until a live run."""
    out = []
    if not live["head"].startswith(p["head"]):
        out.append(f"evidence is for head {p['head']}, the PR head is {live['head'][:8]}")
    if not live["base"].startswith(p["base"]):
        out.append(f"evidence is for base {p['base']}, the PR's merge base is {live['base'][:8]}")
    rec = {f["path"]: (f.get("ins"), f.get("del")) for f in p["diff"].get("by_file", [])}
    if rec and set(rec) != set(live["files"]):
        out.append(f"files differ: {len(set(rec) ^ set(live['files']))} paths not in both")
    if (p["diff"]["files"], p["diff"]["insertions"], p["diff"]["deletions"]) != (len(live["files"]), live["insertions"], live["deletions"]):
        out.append(f"diff stats differ: recorded {p['diff']['files']} files +{p['diff']['insertions']} -{p['diff']['deletions']}, "
                   f"live {len(live['files'])} files +{live['insertions']} -{live['deletions']}")
    return out


def latest_signoff(ws: Workspace, change: str, pack_sha: str) -> dict | None:
    """The newest ledger signoff for this exact pack. A signoff on an older pack of the same change does not count."""
    found = [e for e in ledger.read(ws) if e.get("type") == "signoff"
             and e["payload"].get("change") == change and e["payload"].get("pack_sha256") == pack_sha]
    return found[-1] if found else None


def status_for(p: dict, stale: list[str], signoff: dict | None, ledger_problems: list[str]) -> tuple[str, str]:
    owner = p["owner"]
    if ledger_problems:
        return "failure", f"ledger does not verify: {ledger_problems[0]}"
    if stale:
        return "pending", f"evidence out of date ({stale[0]}): needs a live review run"
    if signoff:
        d, n = signoff["payload"]["decision"], signoff["seq"]
        return ({"accept": ("success", f"countersigned by {owner}: accept (ledger #{n})"),
                 "reject": ("failure", f"rejected by {owner} (ledger #{n})"),
                 "request-changes": ("failure", f"changes requested by {owner} (ledger #{n})")}[d])
    if p["tier"] not in HUMAN_TIERS:
        return "success", f"AI-cleared: {p['tier']} under mandate v{p['mandate']['version']}"
    if p["tier"] == "ask":
        return "pending", f"ask: awaiting countersignature by {owner}"
    return "failure", f"block: {p['why'][0]['id']} (owner {owner} may only reject or request changes)"


# --- GitHub API ----------------------------------------------------------------------------------------------

class GitHub:
    def __init__(self, repo: str, token: str | None = None):
        self.repo, self.token = repo, token or os.environ.get("GITHUB_TOKEN")
        self.api = os.environ.get("GITHUB_API_URL", "https://api.github.com")

    def call(self, method: str, path: str, body=None, ok404: bool = False):
        url = path if path.startswith("http") else f"{self.api}/repos/{self.repo}{path}"
        req = urllib.request.Request(url, method=method, data=None if body is None else json.dumps(body).encode(),
                                     headers={"Authorization": f"Bearer {self.token}", "Accept": "application/vnd.github+json",
                                              "X-GitHub-Api-Version": "2022-11-28", "User-Agent": "countersign"})
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                raw = r.read()
                return json.loads(raw) if raw else None
        except urllib.error.HTTPError as e:
            if ok404 and e.code == 404:
                return None
            raise RuntimeError(f"GitHub {method} {path}: HTTP {e.code} {e.read()[:300]!r}") from None

    def upsert_sticky(self, number: int, body: str) -> str:
        page = 1
        while True:
            comments = self.call("GET", f"/issues/{number}/comments?per_page=100&page={page}")
            for c in comments:
                if MARKER in (c.get("body") or "") and c["user"]["type"] == "Bot":
                    return self.call("PATCH", f"/issues/comments/{c['id']}", {"body": body})["html_url"]
            if len(comments) < 100:
                break
            page += 1
        return self.call("POST", f"/issues/{number}/comments", {"body": body})["html_url"]

    def comment(self, number: int, body: str) -> None:
        self.call("POST", f"/issues/{number}/comments", {"body": body})

    def status(self, sha: str, state: str, description: str, context: str, target_url: str | None) -> None:
        body = {"state": state, "description": description[:140], "context": context}
        if target_url:
            body["target_url"] = target_url
        self.call("POST", f"/statuses/{sha}", body)

    def route_to_owner(self, number: int, login: str, author: str) -> str:
        """Request the owner's review. GitHub refuses a review request to the PR's own author, so then assign instead."""
        if login.lower() != author.lower():
            try:
                self.call("POST", f"/pulls/{number}/requested_reviewers", {"reviewers": [login]})
                return "review requested"
            except RuntimeError as e:
                print(f"review request failed, assigning instead: {e}", file=sys.stderr)
        self.call("POST", f"/issues/{number}/assignees", {"assignees": [login]})
        return "assigned (GitHub does not let the PR's author be requested as its reviewer)"

    def set_tier_label(self, number: int, tier: str) -> None:
        for t in ("silent", "notify", "ask", "block"):
            if t != tier:
                self.call("DELETE", f"/issues/{number}/labels/tier:{t}", ok404=True)
        self.call("POST", f"/issues/{number}/labels", {"labels": [f"tier:{tier}"]})


def _run_url() -> str | None:
    if os.environ.get("GITHUB_RUN_ID"):
        return f"{os.environ.get('GITHUB_SERVER_URL', 'https://github.com')}/{os.environ['GITHUB_REPOSITORY']}/actions/runs/{os.environ['GITHUB_RUN_ID']}"
    return None


# --- the sticky comment --------------------------------------------------------------------------------------

def render(p: dict, pack_sha: str, live: dict, stale: list[str], signoff: dict | None, status: tuple[str, str],
           cfg: dict, pin: str, gh_repo: str, number: int) -> str:
    owner, login = p["owner"], cfg["owners"].get(p["owner"])
    who = f"{owner} (@{login})" if login else f"{owner} (no GitHub login mapped in .countersign/config.yaml)"
    sig = p["mandate"].get("signature") or {}
    lines = [MARKER, f"## Countersign · {status[1]}", ""]
    if cfg.get("recorded"):
        lines += ["> **Recorded reviews; a live run calls the reviewers with the same prompt** "
                  "(`prompts/review-v1.md`). This demo replays the reviews, the adjudication and the build/test results "
                  f"recorded for this change in Zawaer/countersign@`{pin[:12]}` (`reviews/{p['change']}/`, "
                  f"`evidence/{p['change']}/facts.json`). Computed live on every run: the diff below, the match between "
                  "it and the recorded evidence, citation verification against this repo's git objects, the decision, "
                  "the pack and its hash, the ledger check and this status.", ""]
    live_line = (f"yes: head `{live['head'][:8]}`, base `{live['base'][:8]}`, {len(live['files'])} files "
                 f"+{live['insertions']} -{live['deletions']} (recomputed from git just now)")
    rows = [
        ("Tier", f"**{p['tier']}** (strictest of {len(p['drivers'])} drivers; AI's own recommendation: {p['ai_recommendation']})"),
        ("Decides", who + f", owner of area `{p['primary_area']}` in the signed mandate"),
        ("Mandate", f"`{p['mandate']['id']}` v{p['mandate']['version']}, sha256 `{p['mandate']['sha256'][:16]}`, "
                    f"signature {'valid' if sig.get('valid') else 'NOT valid'} ({sig.get('signed_by', '?')})"),
        ("Evidence matches this PR", live_line if not stale else "**no**: " + "; ".join(stale)),
        ("Pack sha256", f"`{pack_sha}`"),
        ("Countersignature", (f"**{signoff['payload']['decision']}** by {signoff['signer']} at {signoff['ts']}, ledger "
                              f"#{signoff['seq']} (`{signoff['hash'][:16]}`), Ed25519 verified against `keys/{signoff['signer'].lower()}.pub`; "
                              f"note: {signoff['payload'].get('note') or '-'}") if signoff else "none yet"),
    ]
    lines += ["| | |", "|---|---|"] + [f"| {k} | {v} |" for k, v in rows] + [""]
    if not signoff and not stale and p["tier"] in HUMAN_TIERS:
        allowed = "|".join(p["signoff"]["allowed_decisions"])
        lines += ["### How the owner countersigns", "",
                  f"{owner} signs with their own key on their own machine (CI never holds it), from a clone of this repo:", "",
                  "```bash",
                  f"PYTHONPATH=.countersign/snapshot python3 -m countersign.github sign-pr {number} --gh-repo {gh_repo} \\",
                  f"  --as {owner} --decision <{allowed}> --note \"...\" --key <path to your {owner.lower()}.key> --post",
                  "```", "",
                  f"That shows the sign-off card, signs a ledger entry over this pack's hash and posts it here as "
                  f"`/countersign <decision> <note>`. CI verifies the signature against `keys/{owner.lower()}.pub` and that "
                  f"the commenter is @{login or '?'}, appends it to the `{cfg['ledger_branch']}` branch and sets "
                  f"`{cfg['status_context']}`. A plain `/countersign accept` without the signed block changes nothing. "
                  "Merging `main` requires that status to pass.", ""]
    lines += ["<details open><summary><b>Evidence pack</b> (pack.md: what was checked and by whom, what was refused and why, "
              "what was not checked, residual risk)</summary>", "", pack_mod.to_markdown(p), "", "</details>"]
    body = "\n".join(lines)
    return body if len(body) < 65000 else body[:64000] + "\n\n_(truncated: the full pack is in the workflow artifact)_\n</details>"


# --- commands ------------------------------------------------------------------------------------------------

def _pr_context(gh: GitHub, number: int) -> dict:
    pr = gh.call("GET", f"/pulls/{number}")
    return {"number": number, "head_ref": pr["head"]["ref"], "head_sha": pr["head"]["sha"],
            "base_sha": pr["base"]["sha"], "author": pr["user"]["login"]}


def _evaluate(a, cfg: dict, pr: dict) -> tuple:
    change = change_for_branch(cfg, pr["head_ref"])
    if not change:
        return (None,) * 7
    ledger_text = Path(a.ledger_dir, "ledger.jsonl").read_text(encoding="utf-8") if a.ledger_dir else None
    ws = workspace(a.snapshot, a.repo_dir, ledger_text)
    p = pack_mod.build(ws, change)
    out = pack_mod.write(ws, p)
    if a.artifacts:
        shutil.copytree(out, Path(a.artifacts) / change, dirs_exist_ok=True)
    pack_sha = sha256_hex(canonical(p))
    live = live_facts(a.repo_dir, pr["base_sha"], pr["head_sha"])
    stale = mismatches(p, live)
    problems, _ = ledger.verify(ws)
    return ws, change, p, pack_sha, live, stale, problems


def _publish(a, gh: GitHub, cfg: dict, pr: dict, ws, p, pack_sha, live, stale, problems) -> tuple[str, str]:
    signoff = None if (stale or problems) else latest_signoff(ws, p["change"], pack_sha)
    st = status_for(p, stale, signoff, problems)
    pin = Path(a.snapshot, "PINNED").read_text().strip() if Path(a.snapshot, "PINNED").exists() else "unknown"
    body = render(p, pack_sha, live, stale, signoff, st, cfg, pin, gh.repo, pr["number"])
    gh.status(pr["head_sha"], st[0], st[1], cfg["status_context"], _run_url())
    url = gh.upsert_sticky(pr["number"], body)
    gh.set_tier_label(pr["number"], p["tier"])
    print(f"{p['change']}: tier {p['tier']}, status {st[0]} ({st[1]}), pack {pack_sha[:16]}, comment {url}")
    return st


def cmd_check(a) -> int:
    cfg = load_config(a.config)
    gh = GitHub(a.gh_repo)
    pr = _pr_context(gh, a.pr)
    ws, change, p, pack_sha, live, stale, problems = _evaluate(a, cfg, pr)
    if not change:
        print(f"branch {pr['head_ref']} does not name a change (pattern {cfg['branch_pattern']}); nothing to do")
        return 0
    _publish(a, gh, cfg, pr, ws, p, pack_sha, live, stale, problems)
    login = cfg["owners"].get(p["owner"])
    if login and p["tier"] in HUMAN_TIERS and not stale:
        print(f"routing to {p['owner']} (@{login}): {gh.route_to_owner(pr['number'], login, pr['author'])}")
    return 0


def verify_signed_entry(entry: dict, ws: Workspace, p: dict, pack_sha: str, decision: str, note: str) -> list[str]:
    """Every reason this entry may not be appended. Empty list = it is the owner's signature over exactly this pack,
    chained onto the current ledger tip."""
    errs = []
    entries = ledger.read(ws)
    pl = entry.get("payload") or {}
    expect = {"type": "signoff", "signer": p["owner"], "seq": len(entries) + 1,
              "prev": entries[-1]["hash"] if entries else ledger.GENESIS}
    for k, v in expect.items():
        if entry.get(k) != v:
            errs.append(f"{k} is {entry.get(k)!r}, expected {v!r}" + (" (the ledger moved on: sign again)" if k in ("seq", "prev") else ""))
    want = {"change": p["change"], "pack_sha256": pack_sha, "decision": decision, "note": note, "tier": p["tier"],
            "mandate_sha256": p["mandate"]["sha256"], "statement": p["signoff"]["statement"]}
    for k, v in want.items():
        if pl.get(k) != v:
            errs.append(f"payload.{k} is {pl.get(k)!r}, expected {v!r}")
    if decision not in p["signoff"]["allowed_decisions"]:
        errs.append(f"decision {decision} not allowed for tier {p['tier']} ({p['signoff']['allowed_decisions']})")
    if ledger.entry_hash(entry) != entry.get("hash"):
        errs.append("hash does not match the entry's content")
    ok, why = keys.verify(ws, p["owner"], str(entry.get("hash")).encode(), entry.get("sig", ""))
    if not ok:
        errs.append(why)
    return errs


def cmd_command(a) -> int:
    cfg = load_config(a.config)
    event = json.loads(Path(a.event).read_text(encoding="utf-8"))
    body, commenter = event["comment"]["body"] or "", event["comment"]["user"]["login"]
    m = COMMAND.search(body)
    if not m or "pull_request" not in event["issue"]:
        print("not a /countersign command on a pull request; ignoring")
        return 0
    verb, note = m.group(1), m.group(2).strip()
    gh = GitHub(a.gh_repo)
    pr = _pr_context(gh, event["issue"]["number"])
    ws, change, p, pack_sha, live, stale, problems = _evaluate(a, cfg, pr)
    if not change:
        gh.comment(pr["number"], f"Countersign: branch `{pr['head_ref']}` does not name a change, so there is no pack to sign.")
        return 0
    if verb == "status":
        _publish(a, gh, cfg, pr, ws, p, pack_sha, live, stale, problems)
        return 0
    owner, login = p["owner"], cfg["owners"].get(p["owner"])
    reply = None
    if not login or commenter.lower() != login.lower():
        reply = (f"Not recorded: the signed mandate names **{owner}** as the owner of change {change}, and "
                 f"`.countersign/config.yaml` maps {owner} to {'@' + login if login else 'no GitHub login'}. "
                 f"A comment from {commenter} cannot countersign it.")
    elif stale or problems:
        reply = "Not recorded: " + "; ".join(stale or problems) + ". Nothing can be countersigned until the evidence matches the PR."
    else:
        block = SIGNED_BLOCK.search(body)
        if not block:
            reply = (f"Not recorded yet: a countersignature is an Ed25519 signature by {owner}'s own key, which CI does not "
                     "hold. Run this on your machine; it shows the card, signs and posts the signed entry here:\n\n```bash\n"
                     f"PYTHONPATH=.countersign/snapshot python3 -m countersign.github sign-pr {pr['number']} --gh-repo {gh.repo} "
                     f"--as {owner} --decision {verb} --note {json.dumps(note)} --key <path to your {owner.lower()}.key> --post\n```")
        else:
            try:
                entry = json.loads(block.group(1))
                errs = verify_signed_entry(entry, ws, p, pack_sha, verb, note)
            except (json.JSONDecodeError, AttributeError, TypeError) as e:
                errs = [f"signed block is not a ledger entry: {e}"]
            if errs:
                reply = "Not recorded: the signed entry does not verify.\n\n" + "\n".join(f"- {e}" for e in errs)
            else:
                with ws.ledger_path.open("a", encoding="utf-8") as f:
                    f.write(json.dumps(entry, sort_keys=True, ensure_ascii=False) + "\n")
                after, _ = ledger.verify(ws)
                if after:
                    reply = "Not recorded: the ledger would not verify with this entry: " + "; ".join(after)
                else:
                    try:
                        _commit_ledger(a.ledger_dir, ws, cfg, entry, pr["number"])
                    except subprocess.CalledProcessError as e:
                        reply = f"Not recorded: pushing the ledger failed ({e.stderr.strip()[:200] if e.stderr else e}). Sign again."
                    else:
                        st = _publish(a, gh, cfg, pr, ws, p, pack_sha, live, stale, [])
                        write_json(Path(a.artifacts or tempfile.mkdtemp()) / "signoff.json", entry)
                        reply = (f"Recorded: **{verb}** by {owner}, ledger #{entry['seq']} (`{entry['hash'][:16]}`) on branch "
                                 f"`{cfg['ledger_branch']}`. Signature verified against `keys/{owner.lower()}.pub`; it covers pack "
                                 f"`{pack_sha[:16]}` and chains onto the previous entry. `{cfg['status_context']}`: {st[0]} ({st[1]}).")
    gh.comment(pr["number"], reply)
    print(reply)
    return 0


def _commit_ledger(ledger_dir: str, ws: Workspace, cfg: dict, entry: dict, number: int) -> None:
    shutil.copyfile(ws.ledger_path, Path(ledger_dir, "ledger.jsonl"))
    run = lambda *x: subprocess.run(["git", "-C", ledger_dir, *x], check=True, capture_output=True, text=True)  # noqa: E731
    run("add", "ledger.jsonl")
    run("-c", "user.name=countersign[bot]", "-c", "user.email=countersign@users.noreply.github.com", "commit", "-q", "-m",
        f"ledger #{entry['seq']}: {entry['payload']['decision']} on change {entry['payload']['change']} by {entry['signer']} (PR #{number})")
    run("push", "-q", "origin", f"HEAD:{cfg['ledger_branch']}")


def make_entry(ws: Workspace, p: dict, signer: str, decision: str, note: str, key_b64: str, extra: dict | None = None) -> dict:
    """The same signoff entry `countersign sign` writes, chained onto the ledger in `ws`, signed with the given key."""
    entries = ledger.read(ws)
    entry = {"seq": len(entries) + 1, "ts": now_iso(), "type": "signoff", "signer": signer,
             "prev": entries[-1]["hash"] if entries else ledger.GENESIS,
             "payload": {"change": p["change"], "pack_path": f"packs/{p['change']}/pack.json", "pack_sha256": sha256_hex(canonical(p)),
                         "decision": decision, "note": note, "tier": p["tier"], "ai_cleared": p["tier"] not in HUMAN_TIERS,
                         "areas": [x["name"] for x in p["areas"]], "mandate_sha256": p["mandate"]["sha256"],
                         "statement": p["signoff"]["statement"], **(extra or {})}}
    entry["hash"] = ledger.entry_hash(entry)
    key = Ed25519PrivateKey.from_private_bytes(base64.b64decode(key_b64))
    entry["sig"] = base64.b64encode(key.sign(entry["hash"].encode())).decode()
    return entry


def _gh(*args: str) -> str:
    return subprocess.run(["gh", *args], check=True, capture_output=True, text=True).stdout


def cmd_sign_pr(a) -> int:
    """Owner's machine: rebuild the PR's pack, show the card, sign a ledger entry with the owner's key, post it."""
    cfg = load_config(a.config)
    pr_raw = json.loads(_gh("api", f"repos/{a.gh_repo}/pulls/{a.pr}"))
    pr = {"number": a.pr, "head_ref": pr_raw["head"]["ref"], "head_sha": pr_raw["head"]["sha"], "base_sha": pr_raw["base"]["sha"]}
    subprocess.run(["git", "-C", a.repo_dir, "fetch", "-q", "origin", pr["head_ref"], pr_raw["base"]["ref"]], check=True)
    ledger_text = base64.b64decode(json.loads(_gh("api", f"repos/{a.gh_repo}/contents/ledger.jsonl?ref={cfg['ledger_branch']}"))["content"]).decode()
    ws = workspace(a.snapshot, a.repo_dir, ledger_text)
    change = change_for_branch(cfg, pr["head_ref"])
    if not change:
        raise SystemExit(f"branch {pr['head_ref']} does not name a change")
    p = pack_mod.build(ws, change)
    stale = mismatches(p, live_facts(a.repo_dir, pr["base_sha"], pr["head_sha"]))
    if stale:
        raise SystemExit("cannot sign: " + "; ".join(stale))
    print(pack_mod.card(p) + "\n")
    if a.signer != p["owner"]:
        raise SystemExit(f"{a.signer} is not the owner of this change; the mandate names {p['owner']}")
    if a.decision not in p["signoff"]["allowed_decisions"]:
        raise SystemExit(f"decision {a.decision} not allowed for tier {p['tier']}: {p['signoff']['allowed_decisions']}")
    a.note = a.note.strip()
    if "\n" in a.note:
        raise SystemExit("keep the note on one line")
    pack_sha = sha256_hex(canonical(p))
    entry = make_entry(ws, p, a.signer, a.decision, a.note, Path(a.key).expanduser().read_text(),
                       {"pr": f"https://github.com/{a.gh_repo}/pull/{a.pr}", "pr_head": pr["head_sha"]})
    errs = verify_signed_entry(entry, ws, p, pack_sha, a.decision, a.note)
    if errs:
        raise SystemExit("the signed entry would be refused:\n  " + "\n  ".join(errs))
    body = (f"/countersign {a.decision} {a.note}\n\n{p['signoff']['statement']}\n\n<details><summary>Signed ledger entry "
            f"(Ed25519, {a.signer}; pack {pack_sha[:16]})</summary>\n\n```{FENCE}\n{json.dumps(entry, sort_keys=True, ensure_ascii=False)}\n```\n</details>\n")
    if a.post:
        subprocess.run(["gh", "pr", "comment", str(a.pr), "-R", a.gh_repo, "--body-file", "-"], input=body, text=True, check=True)
        print(f"posted to https://github.com/{a.gh_repo}/pull/{a.pr}; CI verifies it and records it in the ledger")
    else:
        print(body)
    return 0


def parser() -> argparse.ArgumentParser:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--snapshot", default=".countersign/snapshot", help="pinned Countersign snapshot (mandate, keys, recorded inputs)")
    common.add_argument("--config", default=".countersign/config.yaml", help="GitHub login per owner, branch pattern, ledger branch")
    common.add_argument("--repo-dir", default=".", help="git checkout holding the PR's commits")
    common.add_argument("--gh-repo", default=os.environ.get("GITHUB_REPOSITORY"), help="owner/name on GitHub")
    ap = argparse.ArgumentParser(prog="countersign.github", description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name, fn in (("check", cmd_check), ("command", cmd_command)):
        sp = sub.add_parser(name, parents=[common])
        sp.set_defaults(fn=fn)
        sp.add_argument("--ledger-dir", required=True, help="checkout of the ledger branch (ledger.jsonl)")
        sp.add_argument("--artifacts", help="copy the built pack here")
        if name == "check":
            sp.add_argument("--pr", type=int, required=True)
        else:
            sp.add_argument("--event", default=os.environ.get("GITHUB_EVENT_PATH"))
    sp = sub.add_parser("sign-pr", parents=[common], help="owner: sign a PR's pack with your own key and post it")
    sp.set_defaults(fn=cmd_sign_pr)
    sp.add_argument("pr", type=int)
    sp.add_argument("--as", dest="signer", required=True)
    sp.add_argument("--decision", choices=["accept", "reject", "request-changes"], required=True)
    sp.add_argument("--note", default="")
    sp.add_argument("--key", required=True, help="your Ed25519 private key (raw, base64), e.g. from `countersign keygen`")
    sp.add_argument("--post", action="store_true", help="post the comment with gh (otherwise print it)")
    return ap


def main(argv=None) -> int:
    a = parser().parse_args(argv)
    return a.fn(a)


if __name__ == "__main__":
    raise SystemExit(main())
