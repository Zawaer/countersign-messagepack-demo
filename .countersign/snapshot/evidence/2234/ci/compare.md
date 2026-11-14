# Change 2234: stage 1 reproduced on CRACI

- Run: https://github.com/Zawaer/countersign/actions/runs/43559084959 (job `facts`: https://github.com/Zawaer/countersign/actions/runs/43559084959/job/132338506177)
- Workflow commit: 9e708dbb849708b99fe45c3269b04f422e907d93 (main), dispatched with `job=facts change=2234`
- Runner: craci-1-1f0727ec (CRACI, size 8), 2026-11-14T04:56:33Z to 2026-11-14T04:59:55Z, 3 min 22 s
- Artifacts: `facts-2234` (facts.json, logs, .trx), `craci-2234` of the earlier run (skipped, no token); CRACI's record is from https://github.com/Zawaer/countersign/actions/runs/43580841815 (below)

## Stage 1 reproduced on CRACI: change 2234 (head 9007cee1, SDK 8.0.402 + 9.0.321)

| Check | Committed (local run) | This run | Same? | This run's summary |
|---|---|---|---|---|
| build | pass | pass | yes | 0 errors, 1 unique warnings |
| tests.targeted | pass | pass | yes | 8 passed, 0 failed, 0 skipped (8 new tests in run) |
| tests.fail_without_fix | pass | pass | yes | new tests fail on base source: 4/8 failed -> tests do cover the change (4 new tests pass without the fix) |
| tests.full_suite | pass | pass | yes | tests/MessagePack.SourceGenerator.Tests: 175 tests, 175 passed, 0 failed (0 not failing on base, 0 also failing on base) |
| public_api | pass | pass | yes | no public API changes: no PublicAPI.Shipped/Unshipped.txt changed, no public/protected declarations added or removed in src/ |
| analyzers | pass | pass | yes | no new warnings |
| tests.targeted.execution | pass | pass | yes | SuppressedSourceGenerationTests: 4 passed, 0 failed (4 new test results; runtime: generator runs inside csc, no CS9057) |
| tests.execution_fail_without_fix | fail | fail | yes | new runtime tests pass on base source: 0/4 failed -> these runtime tests do NOT demonstrate the change (runtime behaviour they check is identical with and witho |
| tests.execution_full_suite | pass | pass | yes | tests/MessagePack.SourceGenerator.ExecutionTests: 16/16 passed (base 14/14), 0 failures not on base; tests/MessagePack.SourceGenerator.MapModeExecutionTests: 22 |
| repro.claude.C2 | pass | pass | yes | reproduced by the pipeline: failed on head (claim: failed), failed on base (claim: failed), passed on control (claim: passed) |
| injection_scan | pass | pass | yes | no text addressed to automated reviewers in the added lines, commit message or PR text |
| deps.delta | pass | pass | yes | 238 packages on head (238 on base) across 30 projects; 0 added, 0 version changes, 0 removed; 0 new vulnerability hits (6 already on base) |
| build.egress | absent | pass | **NO** | built on CRACI under a deny-by-default policy: only 13 TLS host patterns on ports 443 (github.com, codeload.github.com, objects.githubusercontent.com, api.nuget |

12 of 13 check statuses match the committed evidence.

Every check other than `build.egress` also has the same summary text as the committed run. `build.egress` is new: it only runs on CRACI, so the committed (local) facts had none; it was appended to `evidence/2234/facts.json` with `run_url`, every other check left byte-identical.

## build.egress

- Status: **pass**. built on CRACI under a deny-by-default policy: only 13 TLS host patterns on ports 443 (github.com, codeload.github.com, objects.githubusercontent.com, api.nuget.org, *.nuget.org, pkgs.dev.azure.com, ...); presets ['github']; no blocked connection in 40 logs; every NuGet feed the head declares is inside the policy
- Policy: default deny, presets ['github'], ports [443]; sha256 `31fafb855e985c38a31b18cfa9140b83a5b9caa5539eadbdf7344e88b20d2fa1`
- TLS hosts allowed (13): `github.com`, `codeload.github.com`, `objects.githubusercontent.com`, `api.nuget.org`, `*.nuget.org`, `pkgs.dev.azure.com`, `*.vsblob.vsassets.io`, `builds.dotnet.microsoft.com`, `dotnetcli.azureedge.net`, `dotnetcli.blob.core.windows.net`, `*.dot.net`, `dot.net`, `download.visualstudio.microsoft.com`
- Blocked hosts: 0 (none), in 40 logs scanned
- NuGet feeds on head outside the policy: 0
- CRACI job CA sha256: `baa0ee3ae7ed8f66cd7175b67a7351f91531c53a210f3955fbd6b456ccc79b31`; runner craci-1-1f0727ec

## CRACI's own record of the build (craci.network, craci.sbom)

- Source: CRACI API `/v1preview1/network-trace` and `/v1preview1/sbom` for the `facts` job 132405049035 of https://github.com/Zawaer/countersign/actions/runs/43580841815, fetched by the `craci` job of the same run (GitHub-hosted; CRACI's proxy refuses a CRACI job's own calls to api.craci.com). Raw: `evidence/2234/ci/craci/network-trace.json.gz`, `evidence/2234/ci/craci/sbom.cdx.json`.
- `craci.network` **pass**: 3706 observations (555 DNS); 220 allowed connections to 13 hosts; **0 proxy violations** by the change's build.

| Host | Connections | Received | Rule (CRACI) | In build.egress TLS list? |
|---|---|---|---|---|
| `builds.dotnet.microsoft.com` | 17 | 468.2 MB | passthrough-tls-github.com | yes |
| `api.nuget.org` | 87 | 283.5 MB | passthrough-tls-github.com | yes |
| `github.com` | 2 | 19.3 MB | passthrough-tls-github.com | yes |
| `codeload.github.com` | 3 | 4.2 MB | passthrough-tls-github.com | yes |
| `pkgs.dev.azure.com` | 36 | 0.4 MB | passthrough-tls-github.com | yes |
| `ci.dot.net` | 8 | 44 kB | passthrough-tls-github.com | yes |
| `results-receiver.actions.githubusercontent.com` | 44 | 10 kB | github-actions-cache-results-receiver.actions.githubusercontent.com | no: CRACI CI-service rule |
| `launch.actions.githubusercontent.com` | 1 | 2 kB | github-actions-actions.githubusercontent.com | no: CRACI CI-service rule |
| `run.actions.githubusercontent.com` | 1 | 0 kB | github-actions-actions.githubusercontent.com | no: CRACI CI-service rule |
| `broker.actions.githubusercontent.com` | 2 | 0 kB | github-actions-actions.githubusercontent.com | no: CRACI CI-service rule |
| `productionresultssa30.blob.core.windows.net` | 17 | 0 kB | recorded-http-api.github.com | no: CRACI CI-service rule |
| `run-actions-3-azure-eastus.actions.githubusercontent.com` | 1 | 0 kB | github-actions-actions.githubusercontent.com | no: CRACI CI-service rule |
| `token.actions.githubusercontent.com` | 1 | 0 kB | github-actions-actions.githubusercontent.com | no: CRACI CI-service rule |

Against `build.egress`: all 6 TLS hosts the build reached (builds.dotnet.microsoft.com, api.nuget.org, github.com, codeload.github.com, pkgs.dev.azure.com, ci.dot.net) are inside its 13 declared patterns. The other 7 are GitHub Actions service endpoints (runner broker, results, cache) that CRACI always allows. Denied by the policy, listed, and not counted as the change's:
- 2928 certificate revocation lookups over plain HTTP (CRL downloads and OCSP GETs, recognised from the request): `ocsp.digicert.com` 924, `crl3.digicert.com` 633, `crl4.digicert.com` 291, `s.symcb.com` 270, `s.symcd.com` 270, `ts-crl.ws.symantec.com` 270, `ts-ocsp.ws.symantec.com` 270. NuGet makes them when it verifies package signatures, so signing-certificate revocation was **not** checked online in this build (the policy has no rule for port 80). `build.egress` saw none of them: the build log does not show them.
- 3 requests during toolchain setup (`actions/setup-dotnet`, before the change was cloned): `aka.ms` 3 (`https://aka.ms/dotnet/LTS/dotnet-runtime-linux-x64.tar.gz`). setup-dotnet then downloads from `builds.dotnet.microsoft.com`.

- `craci.sbom` **pass**: CRACI's job SBOM (CycloneDX 1.7, `urn:uuid:5dda6883-444d-4319-a554-c2d45b3d23ee`) has **0 components**. Our `deps.delta` SBOMs list 242 NuGet packages (base and head). CRACI's SBOM has nothing ours lacks: CRACI has no NuGet source type and the facts job reaches NuGet through a TLS connection rule, which CRACI does not inspect for packages. The package record is ours (`deps.delta`); CRACI's is the connections.
