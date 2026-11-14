# Review of 2297 by nemotron (nvidia/nemotron-3.5-super-vl-120b-a12b, review-v1)

_Run by `countersign review-llm` at 2026-11-14T01:59:11+02:00; raw response in `reviews/2297/raw/nemotron.response.json`. Tokens in/out: 53120/12657._

**Summary:** The change adds [ExcludeFromCodeCoverage] to every type emitted by the MessagePack source generator (formatters, resolvers, enum and union formatters, composite resolvers), guarded by #if !NETSTANDARD2_0 && !NETFRAMEWORK so netstandard2.0/.NET Framework consumers still compile. All six T4 templates and their checked-in generated outputs emit the attribute; the two new tests pass on head and fail on base source, and the full 169-test generator suite passes on head. One unrelated formatting change in TransformUtilities.cs is out of scope.

| Req | Verdict | Basis |
|---|---|---|
| REQ-2297-F1 | met | All six source-generator templates emit [global::System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverage] behind the #if !NETSTANDARD2_0 && !NETFRAMEWORK guard (e.g. ResolverTemplate.tt lines 14-16 and FormatterTemplate.tt lines 14-16; the same pattern appears in CompositeResolverTemplate, EnumTemplate, StringKeyFormatterTemplate and UnionTemplate), the checked-in generated outputs were regenerated accordingly, the new test CodeCoverageExclusionTests.AllGeneratedTypesAreExcludedFromCodeCoverage passes on head and failed on base source, and the full 169-test generator suite passes on head. |

## Findings

- **N1** [minor, scope] Unrelated formatting change in TransformUtilities.cs outside the requirement scope: TransformUtilities.cs line 58 changed the brace emission for nested types that carry type constraints from emitting just "{" to emitting "{\r\n", adding a newline after the opening brace in generated code. This is unrelated to REQ-2297-F1 (ExcludeFromCodeCoverage) and changes generated output beyond the requirement's scope.

## Refusals

- netstandard2.0 and .NET Framework compilation of generated output: build.net472/netstandard was not run (Linux container, only net8.0 built), so the #if guard's effect for those targets was not compile-verified; only the template text was inspected. (decide: area owner / maintainer with a multi-target build)
- runtime execution of generated formatters/resolvers (execution tests): tests.execution was not run: SDK 8.0.402 ships Roslyn 4.11 while the generator references Microsoft.CodeAnalysis 4.12.0, so execution test projects fail to compile (CS9057/CS0117); this mismatch exists on base too and is environmental, not caused by the change. (decide: area owner / maintainer, after moving to an SDK with Roslyn >= 4.12)

## Not given to the model

- the contents and diffs of 228 generated files (listed above by name only)
- src/MessagePack.SourceGenerator/Transforms/TransformUtilities.cs at base: only ±30 lines around the changes (the full file did not fit the budget)
- src/MessagePack.SourceGenerator/Transforms/UnionTemplate.tt at base: only ±30 lines around the changes (the full file did not fit the budget)
- README.md: diff only, full file not provided (doc)
- the upstream issue page itself (only its URL); other files of the repository; build and test logs (only the facts.json summaries)
