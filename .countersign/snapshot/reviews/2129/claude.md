# Review of #2129 by claude (claude-opus-5-5, review-v1, second pass, scoped)

**Verdict:** The feature works for the issue's core scenario, verified by execution tests under SDK 9 that can't exist without the change. Three deterministic checks fail: public_api, solution_membership and analyzers.

| Req | Verdict | Basis |
|---|---|---|
| F1 | met | 7 execution tests pass (external types from an assembly that does not reference MessagePack round-trip and register in the resolver); they do not compile on base |

## Findings
- **C1 (major):** New public `GeneratedMessagePackFormatterAttribute` (+ `SurrogateType`) in the untracked MessagePack.Annotations, plus MsgPack019-022 descriptors. Needs explicit maintainer API sign-off.
- **C2 (minor):** The new ExternalTypes project is not in MessagePack.sln.
- **C3 (minor):** New SA1203 warning in GeneratedMessagePackFormatterTests.cs:22.
- **C4 (info):** External-type tests are excluded from MapModeExecutionTests.

## Refused (scoped review)
- Line-by-line correctness of GeneratedFormatterCollector.cs and the generator pipeline beyond the tested paths.
- API design versus the issue's Union and attribute alternatives.
- Security implications of generated member access on external types.

## Changes from v1
- F1: `cannot_determine` became `met`, because the SDK 9 execution tests now exist in facts.json and fail without the fix (compile failure).
- The API finding moved from info to major, backed by the failing public_api check. Solution-membership and SA1203 findings come from the new checks. I did not re-verify v1's C1-C3 (diagnostics placed in the generator, contractless mode ignoring attributes, generator-level happy-path test) in this scoped pass, so I dropped them rather than re-assert them.
