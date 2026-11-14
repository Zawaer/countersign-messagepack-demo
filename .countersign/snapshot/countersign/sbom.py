"""Dependency SBOMs from a restored .NET tree, and the `deps.delta` check: what a change does to the supply chain.

An agent-written change can add a package, move a version, add a package feed or a build tool, and no code
reviewer reads any of that. This module turns the restored dependency graph of the base and of the head into
two CycloneDX SBOMs and diffs them, so the dependency change becomes review evidence like a failing test.

Stdlib only: evidence/scripts/deps-delta.py runs it with the runner's python3, outside the uv environment.

The graph comes from NuGet's own restore output (obj/**/project.assets.json: the same data `dotnet list
package --include-transitive` prints), for every *.csproj in the tree, not only the solution: a project the
change adds but forgets to put in the .sln still restores and still counts. Vulnerabilities come from NuGet
Audit during that restore (NuGetAuditMode=all: direct and transitive, advisories from nuget.org's
vulnerability database), so the SBOM needs no extra scanner and no extra download host.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import uuid
from pathlib import Path

TOOL = {"name": "countersign-deps", "version": "1"}
AUDIT_RE = re.compile(r"Package '(?P<name>[^']+)' (?P<version>\S+) has a known (?P<severity>\w+) severity vulnerability, (?P<url>\S+)")
SEVERITY_RANK = {"low": 1, "moderate": 2, "high": 3, "critical": 4}
CDX_SEVERITY = {"low": "low", "moderate": "medium", "high": "high", "critical": "critical"}  # NuGet -> CycloneDX enum
CS_NS = uuid.UUID("6f1c2d7e-5a3b-4c8d-9e0f-1a2b3c4d5e6f")  # namespace for deterministic SBOM serial numbers


def purl(name: str, version: str) -> str:
    return f"pkg:nuget/{name}@{version}"


# ---------------------------------------------------------------- reading the restored graph


def read_graph(root: str | Path) -> dict:
    """Every project.assets.json under root -> {projects, packages, vulnerabilities}.

    projects: {relpath: {name, tfms, direct: {pkg: requested range}, project_refs: [relpath], restored: bool}}
    packages: {(name, version): {sha512 (hex), deps: {child name: child version}, direct_in: set, in_projects: set}}
    """
    root = Path(root).resolve()
    projects: dict = {}
    packages: dict = {}
    vulns: dict = {}
    for f in sorted(root.rglob("project.assets.json")):
        d = json.loads(f.read_text(encoding="utf-8-sig"))
        r = d.get("project", {}).get("restore", {})
        ppath = r.get("projectPath")
        if not ppath:
            continue
        rel = _rel(ppath, root)
        direct: dict = {}
        for fw in d.get("project", {}).get("frameworks", {}).values():
            for name, spec in fw.get("dependencies", {}).items():
                if spec.get("target", "Package") == "Package":
                    direct[name] = spec.get("version", "")
        refs = set()
        for fw in r.get("frameworks", {}).values():
            for pr in fw.get("projectReferences", {}).values():
                refs.add(_rel(pr.get("projectPath", ""), root))
        projects[rel] = {"name": r.get("projectName"), "tfms": sorted(d.get("targets", {})), "direct": direct,
                         "project_refs": sorted(refs), "restored": True}
        libs = d.get("libraries", {})
        for tfm, tgt in d.get("targets", {}).items():
            for key, lib in tgt.items():
                if lib.get("type") != "package":
                    continue
                name, version = key.split("/", 1)
                p = packages.setdefault((name, version), {"sha512": _hex(libs.get(key, {}).get("sha512")), "deps": {},
                                                          "direct_in": set(), "in_projects": set()})
                p["in_projects"].add(rel)
                if name in direct:
                    p["direct_in"].add(rel)
                for child in lib.get("dependencies", {}):
                    cv = _resolved(tgt, child)
                    if cv:
                        p["deps"][child] = cv
        for log in d.get("logs", []):
            m = AUDIT_RE.search(log.get("message", ""))
            if log.get("code", "").startswith("NU190") and m:
                k = (m["name"], m["version"], m["url"])
                v = vulns.setdefault(k, {"package": m["name"], "version": m["version"], "severity": m["severity"].lower(),
                                         "advisory": m["url"], "code": log["code"], "projects": set()})
                v["projects"].add(rel)
    return {"projects": projects, "packages": packages, "vulnerabilities": vulns}


def _rel(path: str, root: Path) -> str:
    p = path.replace("\\", "/")
    r = str(root).replace("\\", "/").rstrip("/") + "/"
    return p[len(r):] if p.startswith(r) else p


def _hex(b64: str | None) -> str | None:
    return base64.b64decode(b64).hex() if b64 else None


def _resolved(target: dict, name: str) -> str | None:
    for key, lib in target.items():
        n, _, v = key.partition("/")
        if n.lower() == name.lower() and lib.get("type") == "package":
            return v
    return None


def add_unrestored(graph: dict, csprojs: list[str], restore_errors: dict) -> None:
    """Projects in the tree that produced no assets file (restore failed) are kept as nodes so they stay visible;
    restore errors (e.g. NU1010 in the repo's deliberately broken test-data projects) are attached to every project."""
    for rel in csprojs:
        if rel not in graph["projects"]:
            graph["projects"][rel] = {"name": Path(rel).stem, "tfms": [], "direct": {}, "project_refs": [], "restored": False}
    for rel, errs in restore_errors.items():
        if rel in graph["projects"]:
            graph["projects"][rel]["restore_errors"] = errs


def parse_restore_errors(log: str, root: str | Path) -> dict:
    """`path.csproj : error NU1010: ...` lines from a restore log -> {relpath: [unique messages]}."""
    out: dict = {}
    root = Path(root).resolve()
    for m in re.finditer(r"^\s*(\S+\.csproj) : error (NU\d+): (.*?)(?: \[[^\]]*\])?$", log, re.M):
        out.setdefault(_rel(m[1], root), [])
        msg = f"{m[2]}: {m[3].strip()}"
        if msg not in out[_rel(m[1], root)]:
            out[_rel(m[1], root)].append(msg)
    return out


def merge_configurations(graphs: dict) -> dict:
    """{configuration: graph} -> one graph, the union of all of them (red team S6: a PackageReference conditioned on
    `'$(Configuration)' == 'Release'` is absent from a Debug restore, so the graph of one configuration is not the
    graph that ships). A package, project reference or advisory in any configuration counts. Each package and project
    records the configurations it appeared in; a project counts as restored only if every configuration restored it."""
    out: dict = {"projects": {}, "packages": {}, "vulnerabilities": {}, "configurations": list(graphs)}
    for cfg, g in graphs.items():
        for rel, pr in g["projects"].items():
            o = out["projects"].get(rel)
            if o is None:
                o = out["projects"][rel] = {**pr, "direct": dict(pr["direct"]), "tfms": list(pr["tfms"]),
                                            "project_refs": list(pr["project_refs"]), "configurations": []}
                if "restore_errors" in pr:
                    o["restore_errors"] = list(pr["restore_errors"])
            else:
                for n, v in pr["direct"].items():
                    o["direct"].setdefault(n, v)
                o["tfms"] = sorted(set(o["tfms"]) | set(pr["tfms"]))
                o["project_refs"] = sorted(set(o["project_refs"]) | set(pr["project_refs"]))
                o["restored"] = o["restored"] and pr["restored"]
                errs = pr.get("restore_errors", [])
                if errs:
                    o["restore_errors"] = o.get("restore_errors", []) + [e for e in errs if e not in o.get("restore_errors", [])]
            o["configurations"].append(cfg)
        for key, p in g["packages"].items():
            o = out["packages"].setdefault(key, {"sha512": p["sha512"], "deps": {}, "direct_in": set(), "in_projects": set(),
                                                 "configurations": []})
            o["sha512"] = o["sha512"] or p["sha512"]
            for cn, cv in p["deps"].items():
                o["deps"].setdefault(cn, cv)
            o["direct_in"] |= p["direct_in"]
            o["in_projects"] |= p["in_projects"]
            o["configurations"].append(cfg)
        for key, v in g["vulnerabilities"].items():
            o = out["vulnerabilities"].setdefault(key, {**v, "projects": set()})
            o["projects"] |= v["projects"]
    return out


def only_in(graph: dict, p: dict) -> list[str] | None:
    """The configurations a package appeared in, when that is not all of them (None for a single-configuration graph
    or a package in every configuration: nothing to say, and the SBOM and deps.delta stay as they were)."""
    every = graph.get("configurations") or []
    mine = p.get("configurations") or every
    return sorted(mine) if len(every) > 1 and set(mine) != set(every) else None


# ---------------------------------------------------------------- build inputs outside the package graph


def tree_inputs(root: str | Path) -> dict:
    """Supply-chain inputs that are not packages: SDK pin, dotnet tools, NuGet feeds, MSBuild SDKs."""
    root = Path(root)
    out: dict = {"sdk": None, "msbuild_sdks": {}, "dotnet_tools": {}, "package_sources": {}}
    g = root / "global.json"
    if g.exists():
        gj = json.loads(g.read_text(encoding="utf-8-sig"))
        out["sdk"] = gj.get("sdk", {}).get("version")
        out["msbuild_sdks"] = dict(sorted(gj.get("msbuild-sdks", {}).items()))
    for t in sorted(root.rglob("dotnet-tools.json")):
        if "obj" in t.relative_to(root).parts:
            continue
        rel = t.relative_to(root).as_posix()
        for name, spec in json.loads(t.read_text(encoding="utf-8-sig")).get("tools", {}).items():
            out["dotnet_tools"][f"{rel}:{name}"] = spec.get("version")
    for n in sorted(root.rglob("*")):
        if n.name.lower() == "nuget.config" and "obj" not in n.relative_to(root).parts:
            rel = n.relative_to(root).as_posix()
            for m in re.finditer(r'<add\s+key="([^"]+)"\s+value="([^"]+)"', n.read_text(encoding="utf-8-sig")):
                if m[2].startswith(("http://", "https://")) or "/" in m[2]:
                    out["package_sources"][f"{rel}:{m[1]}"] = m[2]
    return out


# ---------------------------------------------------------------- CycloneDX


def cyclonedx(graph: dict, inputs: dict, *, name: str, sha: str, sdk: str) -> dict:
    """A deterministic CycloneDX 1.6 SBOM (no timestamp; serial number derived from the content)."""
    comps, deps = [], []
    for (n, v), p in sorted(graph["packages"].items(), key=lambda kv: (kv[0][0].lower(), kv[0][1])):
        c = {"type": "library", "bom-ref": purl(n, v), "name": n, "version": v, "purl": purl(n, v),
             "scope": "required",
             "properties": [{"name": "countersign:direct_in", "value": ", ".join(sorted(p["direct_in"]))}] if p["direct_in"] else []}
        if only_in(graph, p):
            c["properties"].append({"name": "countersign:configurations", "value": ", ".join(only_in(graph, p))})
        if p["sha512"]:
            c["hashes"] = [{"alg": "SHA-512", "content": p["sha512"]}]
        if not c["properties"]:
            del c["properties"]
        comps.append(c)
        deps.append({"ref": purl(n, v), "dependsOn": sorted(purl(cn, cv) for cn, cv in p["deps"].items())})
    for key, ver in sorted(inputs.get("dotnet_tools", {}).items()):
        tool = key.split(":", 1)[1]
        comps.append({"type": "application", "bom-ref": f"tool:{key}", "name": tool, "version": ver, "purl": purl(tool, ver),
                      "properties": [{"name": "countersign:kind", "value": "dotnet-tool"},
                                     {"name": "countersign:manifest", "value": key.split(":", 1)[0]}]})
    for rel, pr in sorted(graph["projects"].items()):
        resolved = {n: v for (n, v), p in graph["packages"].items() if rel in p["direct_in"]}
        comps.append({"type": "application", "bom-ref": f"project:{rel}", "name": pr["name"] or Path(rel).stem,
                      "properties": [{"name": "countersign:kind", "value": "project"}, {"name": "countersign:path", "value": rel},
                                     {"name": "countersign:restored", "value": str(pr["restored"]).lower()}]
                      + [{"name": "countersign:tfm", "value": t} for t in pr["tfms"]]})
        deps.append({"ref": f"project:{rel}", "dependsOn": sorted([purl(n, v) for n, v in resolved.items()]
                                                                   + [f"project:{r}" for r in pr["project_refs"]])})
    vulns = []
    for (pn, pv, url), v in sorted(graph["vulnerabilities"].items()):
        vulns.append({"bom-ref": f"vuln:{pn}@{pv}:{url.rsplit('/', 1)[-1]}", "id": url.rsplit("/", 1)[-1],
                      "source": {"name": "nuget.org vulnerability database (NuGet Audit)", "url": url},
                      "ratings": [{"severity": CDX_SEVERITY.get(v["severity"], "unknown")}],
                      "affects": [{"ref": purl(pn, pv)}]})
    doc = {"bomFormat": "CycloneDX", "specVersion": "1.6", "version": 1,
           "metadata": {"tools": {"components": [{"type": "application", **TOOL},
                                                 {"type": "application", "name": "dotnet-sdk (restore, NuGet Audit)", "version": sdk}]},
                        "component": {"type": "application", "bom-ref": f"repo@{sha}", "name": name, "version": sha},
                        "properties": [{"name": f"countersign:{k}", "value": json.dumps(v, sort_keys=True)}
                                       for k, v in sorted(inputs.items())]},
           "components": comps, "dependencies": deps}
    if vulns:
        doc["vulnerabilities"] = vulns
    doc["serialNumber"] = "urn:uuid:" + str(uuid.uuid5(CS_NS, json.dumps(doc, sort_keys=True)))
    return doc


# ---------------------------------------------------------------- the delta


def _names(graph: dict) -> dict:
    out: dict = {}
    for (n, v) in graph["packages"]:
        out.setdefault(n.lower(), (n, set()))[1].add(v)
    return out


def _via(graph: dict, name: str, version: str) -> list[str]:
    """Shortest path(s) from a project's direct reference to name@version: who pulled it in."""
    parents: dict = {}
    for (n, v), p in graph["packages"].items():
        for cn, cv in p["deps"].items():
            parents.setdefault((cn.lower(), cv), set()).add((n, v))
    out = []
    frontier = [((name, version), [f"{name} {version}"])]
    seen = set()
    while frontier and len(out) < 3:
        nxt = []
        for (n, v), path in frontier:
            p = graph["packages"].get((n, v))
            if p and p["direct_in"]:
                out.append(f"{sorted(p['direct_in'])[0]} -> " + " -> ".join(reversed(path)))
            for pn, pv in sorted(parents.get((n.lower(), v), ())):
                if (pn, pv) not in seen:
                    seen.add((pn, pv))
                    nxt.append(((pn, pv), path + [f"{pn} {pv}"]))
        frontier = nxt
    return out[:3]


def delta(base: dict, head: dict, base_inputs: dict, head_inputs: dict, allowed: list[str] | None = None) -> dict:
    """The deps.delta check. status fail when the head brings a package name or version the base did not have,
    a new package feed, or a vulnerability the base did not have, unless every new package is in `allowed`
    (names or name@version; the mandate's allowed_new_dependencies). Everything else is reported, not judged."""
    allowed = [a.lower() for a in (allowed or [])]
    bn, hn = _names(base), _names(head)
    added, changed, removed = [], [], []
    for key, (name, hv) in sorted(hn.items()):
        if key not in bn:
            for v in sorted(hv):
                p = head["packages"][(name, v)]
                added.append({"package": name, "version": v, "purl": purl(name, v), "direct": bool(p["direct_in"]),
                              "direct_in": sorted(p["direct_in"]), "via": _via(head, name, v), **_configs(head, p)})
        elif hv != bn[key][1]:
            bv = bn[key][1]
            for v in sorted(hv - bv):
                p = head["packages"][(name, v)]
                changed.append({"package": name, "from": sorted(bv), "to": v, "purl": purl(name, v),
                                "direct": bool(p["direct_in"]), "via": _via(head, name, v), **_configs(head, p)})
    for key, (name, bv) in sorted(bn.items()):
        if key not in hn:
            removed.append({"package": name, "versions": sorted(bv)})
        elif bv - hn[key][1]:
            removed.append({"package": name, "versions": sorted(bv - hn[key][1]), "still_present": sorted(hn[key][1])})
    new_projects = sorted(set(head["projects"]) - set(base["projects"]))
    gone_projects = sorted(set(base["projects"]) - set(head["projects"]))
    new_direct = []
    for rel, pr in sorted(head["projects"].items()):
        before = base["projects"].get(rel, {}).get("direct", {})
        for n in sorted(set(pr["direct"]) - set(before)):
            new_direct.append({"project": rel, "package": n, "requested": pr["direct"][n], "new_project": rel in new_projects})
    new_refs = []
    for rel, pr in sorted(head["projects"].items()):
        before = set(base["projects"].get(rel, {}).get("project_refs", []))
        new_refs += [{"project": rel, "references": r} for r in pr["project_refs"] if r not in before]
    bvul = {k for k in base["vulnerabilities"]}
    new_vulns = [_vjson(v) for k, v in sorted(head["vulnerabilities"].items()) if k not in bvul]
    kept_vulns = [_vjson(v) for k, v in sorted(head["vulnerabilities"].items()) if k in bvul]
    inputs = {}
    for k in ("sdk", "msbuild_sdks", "dotnet_tools", "package_sources"):
        if base_inputs.get(k) != head_inputs.get(k):
            inputs[k] = {"base": base_inputs.get(k), "head": head_inputs.get(k)}
    new_sources = sorted(set((head_inputs.get("package_sources") or {}).values()) - set((base_inputs.get("package_sources") or {}).values()))
    unrestored = sorted(rel for rel, pr in head["projects"].items() if not pr["restored"])
    errors = {rel: pr["restore_errors"] for rel, pr in sorted(head["projects"].items()) if pr.get("restore_errors")}
    errors_new = {rel: e for rel, e in errors.items() if e != base["projects"].get(rel, {}).get("restore_errors")}
    unrestored_new = sorted({r for r in unrestored if base["projects"].get(r, {}).get("restored", False) or r not in base["projects"]}
                            | set(errors_new))

    def ok(x):
        return x["package"].lower() in allowed or f"{x['package']}@{x.get('version', x.get('to'))}".lower() in allowed
    unallowed = [x for x in added + changed if not ok(x)]
    reasons = []
    if unallowed:
        reasons.append(f"{len(unallowed)} new package(s)/version(s) not allowed by the mandate: "
                       + ", ".join(f"{x['package']} {x.get('version') or x.get('to')}"
                                   + (f" ({', '.join(x['configurations'])} only)" if x.get("configurations") else "")
                                   for x in unallowed[:8]))
    if new_sources:
        reasons.append("new package feed(s): " + ", ".join(new_sources))
    if new_vulns:
        reasons.append(f"{len(new_vulns)} vulnerability hit(s) not on base: "
                       + ", ".join(f"{v['package']} {v['version']} {v['severity']} {v['advisory'].rsplit('/', 1)[-1]}" for v in new_vulns[:5]))
    if unrestored_new:
        reasons.append("project(s) that fail to restore on head but not on base: " + ", ".join(unrestored_new))
    parts = [f"{len(head['packages'])} packages on head ({len(base['packages'])} on base) across {len(head['projects'])} projects",
             f"{len(added)} added, {len(changed)} version changes, {len(removed)} removed"]
    if new_projects:
        parts.append(f"new project(s): {', '.join(new_projects)}")
    if new_direct:
        parts.append(f"{len(new_direct)} new direct reference(s) to packages already in the graph" if not added
                     else f"{len(new_direct)} new direct reference(s)")
    if inputs:
        parts.append("build inputs changed: " + ", ".join(inputs))
    parts.append(f"{len(new_vulns)} new vulnerability hits ({len(kept_vulns)} already on base)")
    return {
        "id": "deps.delta",
        "tool": "dotnet restore (every *.csproj, NuGet Audit mode=all) -> CycloneDX 1.6, base vs head",
        "status": "fail" if reasons else "pass",
        "summary": "; ".join(parts) + (" -> " + "; ".join(reasons) if reasons else ""),
        "fail_reasons": reasons,
        "policy": {"allowed_new_dependencies": allowed, "fail_on": ["package or version not on base and not allowed",
                                                                    "new package feed", "vulnerability not on base",
                                                                    "project that fails to restore on head only"]},
        "new_or_changed": [f"{x['package']}@{x.get('version') or x.get('to')}" for x in added + changed],
        "packages_added": added, "versions_changed": changed, "packages_removed": removed,
        "projects_added": new_projects, "projects_removed": gone_projects,
        "direct_references_added": new_direct, "project_references_added": new_refs,
        "build_inputs_changed": inputs,
        "vulnerabilities_new": new_vulns, "vulnerabilities_also_on_base": kept_vulns,
        "projects_not_restored": unrestored,
        "restore_errors": errors, "restore_errors_not_on_base": errors_new,
        "counts": {"base_packages": len(base["packages"]), "head_packages": len(head["packages"]),
                   "base_projects": len(base["projects"]), "head_projects": len(head["projects"])},
    }


def _configs(graph: dict, p: dict) -> dict:
    c = only_in(graph, p)
    return {"configurations": c} if c else {}


def _vjson(v: dict) -> dict:
    return {"package": v["package"], "version": v["version"], "severity": v["severity"], "advisory": v["advisory"],
            "nuget_code": v["code"], "projects": sorted(v["projects"])}


def write_json(path: str | Path, data) -> None:
    """A CycloneDX document compact, one component per line; anything else indented."""
    if "bomFormat" not in data:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(json.dumps(data, indent=1) + "\n")
        return
    # compact, one component per line: small enough to commit, still diffable
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    head = {k: v for k, v in data.items() if k not in ("components", "dependencies", "vulnerabilities")}
    lines = [json.dumps(head, separators=(",", ":"))[:-1]]
    for k in ("components", "dependencies", "vulnerabilities"):
        if k in data:
            lines.append(f',"{k}":[\n' + ",\n".join(json.dumps(x, separators=(",", ":")) for x in data[k]) + "]")
    Path(path).write_text("\n".join(lines) + "}\n")


def sha256_file(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def env_list(name: str) -> list[str]:
    return [x for x in re.split(r"[\s,]+", os.environ.get(name, "")) if x]
