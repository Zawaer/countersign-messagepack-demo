"""CRACI as a witness: pull CRACI's own record of the facts job (job SBOM, network trace) into facts.json.

The facts job reproduces stage 1 for a change on a CRACI runner. CRACI watched that job from outside: it proxied
its traffic under the job's network policy and recorded every connection, and it writes an SBOM of the packages
it saw the job download. Those are a third party's records of what building the change touched, not ours. This
module fetches them through the CRACI API (https://api.craci.com, OpenAPI at /openapi.json) and adds two checks:

  craci.sbom     CRACI's CycloneDX job SBOM, compared with our restore-graph SBOM (deps.delta)
  craci.network  CRACI's network trace: hosts reached, bytes, the policy rule that matched, proxy violations

Both are token-gated. Without CRACI_API_TOKEN both checks are `skipped` with reason "no CRACI_API_TOKEN" and the
command exits 0: a missing token never fails a build. The token is sent only in the Authorization header and is
never printed or written.

usage: python3 -m countersign.craci attach --facts F --repo OWNER/REPO --run-id N [--job facts] [--out DIR]
  The GitHub job id is CRACI_JOB_ID if set, else looked up with GITHUB_TOKEN (GET /repos/{repo}/actions/runs/{run}/jobs,
  first job whose name starts with --job). Stdlib only, so the workflow runs it with the runner's python3.
"""

from __future__ import annotations

import fnmatch
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path

API = os.environ.get("CRACI_API_URL", "https://api.craci.com")
GITHUB_API = os.environ.get("GITHUB_API_URL", "https://api.github.com")
NO_TOKEN = "no CRACI_API_TOKEN"


class ApiError(Exception):
    def __init__(self, status: int, detail: str):
        super().__init__(f"HTTP {status}: {detail}")
        self.status = status


def urllib_get(url: str, headers: dict, timeout: float = 60) -> tuple[int, bytes]:
    req = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


class Client:
    """The three CRACI endpoints we use. `get` is injectable (tests pass a stub shaped like the OpenAPI spec)."""

    def __init__(self, token: str, get=urllib_get, sleep=time.sleep, retries_409: int = 12, wait_409: float = 10):
        self.token, self.get, self.sleep = token, get, sleep
        self.retries_409, self.wait_409 = retries_409, wait_409

    def _call(self, path: str, params: dict) -> bytes:
        url = f"{API}{path}?{urllib.parse.urlencode(params)}"
        for attempt in range(self.retries_409 + 1):
            status, body = self.get(url, {"Authorization": f"Bearer {self.token}", "Accept": "application/json, application/vnd.cyclonedx+json"})
            if status == 200:
                return body
            if status in (409, 503) and attempt < self.retries_409:  # 409: job not terminal yet (CRACI is finalizing it)
                self.sleep(self.wait_409)
                continue
            raise ApiError(status, _problem(body))
        raise ApiError(409, "job never became terminal")

    def job(self, repo: str, job_id: str) -> dict:
        return {"provider": "github", "repo": repo, "job_id": str(job_id)}

    def sbom(self, repo: str, job_id: str) -> dict:
        return json.loads(self._call("/v1preview1/sbom", self.job(repo, job_id)))

    def network_trace(self, repo: str, job_id: str) -> dict:
        return json.loads(self._call("/v1preview1/network-trace", self.job(repo, job_id)))


def _problem(body: bytes) -> str:
    try:
        p = json.loads(body)
        return f"{p.get('title', '')}: {p.get('detail', '')}".strip(": ")
    except (ValueError, AttributeError):
        return body[:200].decode(errors="replace")


def github_job_id(repo: str, run_id: str, prefix: str, token: str | None, get=urllib_get) -> str:
    headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    status, body = get(f"{GITHUB_API}/repos/{repo}/actions/runs/{run_id}/jobs?per_page=100", headers)
    if status != 200:
        raise ApiError(status, f"GitHub jobs lookup: {_problem(body)}")
    for j in json.loads(body).get("jobs", []):
        if j.get("name", "").startswith(prefix):
            return str(j["id"])
    raise ApiError(404, f"no job named {prefix}* in run {run_id}")


# ---------------------------------------------------------------- summaries


def summarize_sbom(doc: dict, ours: list[dict]) -> dict:
    """CRACI's job SBOM next to ours (the deps.delta SBOMs of base and head)."""
    comps = doc.get("components", [])
    purls = sorted({c.get("purl", "") for c in comps if c.get("purl")})
    by_type = Counter(p.split("/", 1)[0] for p in purls)
    our_purls = {c["purl"].lower() for d in ours for c in d.get("components", []) if c.get("purl", "").startswith("pkg:nuget/")}
    craci_nuget = {p.lower() for p in purls if p.startswith("pkg:nuget/")}
    unexplained = sorted(craci_nuget - our_purls)
    props = {p.get("name"): p.get("value") for p in doc.get("metadata", {}).get("properties", [])}
    complete = {k: v for k, v in props.items() if "complete" in (k or "").lower()}
    out = {"spec_version": doc.get("specVersion"), "serial": doc.get("serialNumber"), "components": len(comps),
           "by_purl_type": dict(sorted(by_type.items())), "completeness": complete or None,
           "nuget_seen_by_craci": len(craci_nuget), "nuget_in_our_graph": len(our_purls),
           "nuget_seen_by_craci_not_in_our_graph": unexplained,
           "other_components": [p for p in purls if not p.startswith("pkg:nuget/")][:100]}
    note = ("CRACI has no NuGet source type, so the facts job reaches NuGet through a TLS connection rule, which CRACI does "
            "not inspect for packages: the NuGet graph is recorded by deps.delta, CRACI records the connections (craci.network)")
    if unexplained:
        out |= {"status": "fail", "summary": f"CRACI saw {len(unexplained)} NuGet package(s) downloaded that are not in the "
                                             f"restore graph of base or head: {', '.join(unexplained[:5])}"}
    else:
        out |= {"status": "pass",
                "summary": (f"CRACI's job SBOM: {len(comps)} components ({', '.join(f'{k} {v}' for k, v in sorted(by_type.items())) or 'none'}); "
                            f"{len(craci_nuget)} NuGet, all in our restore graph ({len(our_purls)} NuGet packages)"
                            + ("" if craci_nuget else f". {note}"))}
    return out


def _host(url: str) -> str:
    return urllib.parse.urlsplit(url).hostname or url


def summarize_trace(trace: dict, allow: list[str] | None = None) -> dict:
    """Per-host connections, bytes and matched rules; every denied observation is a proxy violation."""
    hosts: dict = {}
    denied, dns = [], 0
    for o in trace.get("observations", []):
        proto = o.get("protocol")
        if proto == "dns":
            dns += 1
            continue
        if proto == "http":
            h = o["http"]
            host, ok, rule, why = _host(h.get("originUrl", "")), not h.get("policyDenied"), h.get("matchedRule"), h.get("denyReason")
            sent, recv = 0, int(h.get("bodySizeBytes") or 0)
        elif proto == "tcp":
            t = o["tcp"]
            host = t.get("tlsServerName") or (t.get("resolvedHosts") or [t.get("remoteIp", "?")])[0]
            ok, rule, why = bool(t.get("allowed")), t.get("matchedRule"), t.get("denyReason")
            sent, recv = int(t.get("bytesToRemote") or 0), int(t.get("bytesFromRemote") or 0)
            host = f"{host}:{t.get('port')}" if t.get("port") not in (443, None) else host
        elif proto == "ssh_git":
            s = o["sshGit"]
            host, ok, rule, why = s.get("host", "?"), bool(s.get("allowed")), s.get("matchedRule"), s.get("denyReason")
            sent, recv = int(s.get("bytesToUpstream") or 0), int(s.get("bytesFromUpstream") or 0)
        else:
            continue
        e = hosts.setdefault(host, {"host": host, "connections": 0, "bytes_sent": 0, "bytes_received": 0, "rules": set(), "denied": 0})
        e["connections"] += 1
        e["bytes_sent"] += sent
        e["bytes_received"] += recv
        if rule:
            e["rules"].add(rule)
        if not ok:
            e["denied"] += 1
            denied.append({"sequence": o.get("sequence"), "at": o.get("observedAt"), "protocol": proto, "host": host, "reason": why})
    rows = sorted(({**e, "rules": sorted(e["rules"])} for e in hosts.values()), key=lambda e: -e["bytes_received"])
    outside = []
    if allow:
        outside = sorted(h for h in hosts if not any(fnmatch.fnmatch(h.split(":")[0].lower(), p.lower()) for p in allow)
                         and not hosts[h]["denied"])
    job = trace.get("job", {})
    out = {"schema_version": trace.get("schemaVersion"), "job": {k: job.get(k) for k in ("runId", "jobId", "runAttempt", "commitSha", "branch", "jobName", "status")},
           "observations": len(trace.get("observations", [])), "dns_queries": dns, "hosts": rows,
           "proxy_violations": denied, "allowed_hosts_outside_declared_tls_patterns": outside}
    top = ", ".join(f"{r['host']} ({_mb(r['bytes_received'])})" for r in rows[:6])
    if denied:
        tried = sorted({d["host"] + (f" ({d['reason']})" if d["reason"] else "") for d in denied})
        out |= {"status": "fail", "summary": f"{len(denied)} proxy violation(s): the build tried to reach {', '.join(tried)}"}
    else:
        out |= {"status": "pass", "summary": f"{sum(r['connections'] for r in rows)} connections to {len(rows)} hosts, 0 proxy violations: {top}"}
    if outside:
        out["summary"] += f"; allowed by a preset rather than a listed host: {', '.join(outside)}"
    return out


def _mb(n: int) -> str:
    return f"{n / 1e6:.1f} MB" if n >= 1e5 else f"{n / 1e3:.0f} kB"


# ---------------------------------------------------------------- attach to facts.json


def attach(facts_path: Path, repo: str, run_id: str | None, job: str = "facts", out_dir: Path | None = None,
           env: dict | None = None, get=urllib_get, sleep=time.sleep) -> list[dict]:
    env = os.environ if env is None else env
    facts = json.loads(facts_path.read_text())
    out_dir = out_dir or facts_path.parent / "craci"
    token = env.get("CRACI_API_TOKEN", "").strip()
    base = {"tool": "CRACI API v1preview1 (https://api.craci.com)", "source": {"repo": repo, "run_id": run_id, "job": job}}
    if not token:
        checks = [{"id": i, **base, "status": "skipped", "reason": NO_TOKEN, "summary": f"not fetched: {NO_TOKEN} (the job's record is in the CRACI app: View trace / SBOM)"}
                  for i in ("craci.sbom", "craci.network")]
    else:
        checks = []
        try:
            job_id = env.get("CRACI_JOB_ID") or github_job_id(repo, run_id, job, env.get("GITHUB_TOKEN"), get=get)
        except ApiError as e:
            job_id, err = None, str(e)
        c = Client(token, get=get, sleep=sleep)
        src = {**base["source"], "job_id": job_id}
        ours = []
        for p in ("sbom.cdx.json", "../base/sbom.cdx.json"):
            f = facts_path.parent / p
            if f.exists():
                ours.append(json.loads(f.read_text()))
        for cid, fetch, fname, summarize in (
                ("craci.sbom", c.sbom, "sbom.cdx.json", lambda d: summarize_sbom(d, ours)),
                ("craci.network", c.network_trace, "network-trace.json", lambda d: summarize_trace(d, _allow(facts)))):
            if job_id is None:
                checks.append({"id": cid, **base, "source": src, "status": "error", "summary": f"could not find the GitHub job id: {err}"})
                continue
            try:
                doc = fetch(repo, job_id)
            except ApiError as e:
                checks.append({"id": cid, **base, "source": src, "status": "error", "summary": f"CRACI API: {e}"})
                continue
            out_dir.mkdir(parents=True, exist_ok=True)
            (out_dir / fname).write_text(json.dumps(doc, indent=1) + "\n")
            rel = os.path.relpath(out_dir / fname, facts_path.parent.parent.parent)
            checks.append({"id": cid, **base, "source": src, "raw": rel, **summarize(doc)})
    facts["checks"] = [x for x in facts["checks"] if x["id"] not in ("craci.sbom", "craci.network")] + checks
    facts_path.write_text(json.dumps(facts, indent=2))
    return checks


def _allow(facts: dict) -> list[str]:
    eg = next((c for c in facts.get("checks", []) if c["id"] == "build.egress"), None)
    return (eg or {}).get("policy", {}).get("tls_server_name_patterns", [])


def main(argv: list[str] | None = None) -> int:
    a = list(sys.argv[1:] if argv is None else argv)
    if not a or a[0] != "attach":
        print(__doc__)
        return 2

    def opt(k, d=None):
        return a[a.index(k) + 1] if k in a else d
    checks = attach(Path(opt("--facts")), opt("--repo", os.environ.get("GITHUB_REPOSITORY", "")), opt("--run-id", os.environ.get("GITHUB_RUN_ID")),
                    opt("--job", "facts"), Path(opt("--out")) if opt("--out") else None)
    for c in checks:
        print(f"{c['id']}: {c['status']} - {c['summary']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
