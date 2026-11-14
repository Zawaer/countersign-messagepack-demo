# Review of 2129 by nemotron (nvidia/nemotron-3.5-super-vl-120b-a12b, review-v1)

_Run by `countersign review-llm` at 2026-11-14T01:56:41+02:00; raw response in `reviews/2129/raw/nemotron.response.json`. Tokens in/out: 103847/18432._

**Summary:** Change 2129 implements the feature request by adding a [GeneratedMessagePackFormatter] attribute and source-generator support: a partial formatter class for a type in another (unmodifiable) assembly gets its Serialize/Deserialize body written by the generator and is registered in the generated resolver, using contractless mode by default with an optional surrogate type for key/membership control. Four new analyzer diagnostics (MsgPack019–022) validate usage. The change addresses the root cause (no mechanism existed to format types from referenced assemblies) rather than a symptom; all new tests pass, fail on the reverted base source, and the execution tests do not compile without the fix. Documentation (README, MsgPack019–022, AnalyzerReleases.Unshipped.md, index.md) describes the feature and its limitations.

| Req | Verdict | Basis |
|---|---|---|
| REQ-2129-F1 | met | The branch adds the [GeneratedMessagePackFormatter] attribute (Attributes.cs:166), generator discovery of such formatters (MessagePackGenerator.cs:30) and their collection into the resolver model (GeneratedFormatterCollector.cs:72), with contractless and surrogate member selection; execution tests round-trip types from ExternalTypes, an assembly without any MessagePack reference, and pass, while the same tests fail on base source and the execution tests do not compile without the fix. |

## Findings

- **N1** [minor, build] New ExternalTypes test project is not added to the solution file: The new project tests/MessagePack.SourceGenerator.ExternalTypes/MessagePack.SourceGenerator.ExternalTypes.csproj is not added to MessagePack.sln; it is only referenced from ExecutionTests.csproj, so solution-level builds may not include or build it consistently.
- **N2** [major, build] Execution tests require SDK 9 / Roslyn 4.12 but the repo pins SDK 8.0.402: Building tests/MessagePack.SourceGenerator.ExecutionTests with SDK 8.0.402 fails with CS9057 because the source generator references Microsoft.CodeAnalysis 4.12 while SDK 8 ships Roslyn 4.11; the SDK 9 override existed only in the scratch worktree, so builds on the pinned SDK cannot compile these new tests (the targeted run passes only under SDK 9).
- **N3** [minor, maintainability] New public API added without PublicAPI tracking in MessagePack.Annotations: MessagePack.Annotations gains public class GeneratedMessagePackFormatterAttribute with public Type? SurrogateType, and the analyzer gains four public DiagnosticDescriptors (MsgPack019–022), but MessagePack.Annotations has no PublicAPI.*.txt so PublicApiAnalyzers did not flag the addition; future breaking changes to this surface will not be caught by that analyzer.
- **N4** [minor, maintainability] New StyleCop SA1203 warning in GeneratedMessagePackFormatterTests.cs: A new warning SA1203 (constant fields should appear before non-constant fields) appears versus base, because the const string Members is declared after the non-constant testOutputHelper field.

## Refusals

- Generated output of FormatterTemplate.cs and StringKeyFormatterTemplate.cs: The two generated template .cs files were listed as changed but their contents/diffs were not provided, so the exact generated formatter class text could not be inspected directly; behavior was verified through the passing execution tests instead. (decide: area owner (or re-run this review with the generated file contents))
- Security review of serializing externally defined types via generated formatters: No runtime deserialization code was changed by this branch, but the library deserializes untrusted input and this feature lets formats be generated for types the reviewer cannot inspect; a formal security judgement is beyond the provided evidence. (decide: area owner / security reviewer)

## Not given to the model

- the contents and diffs of 2 generated files (listed above by name only)
- src/MessagePack.SourceGenerator/CodeAnalysis/ObjectSerializationInfo.cs at base: not provided (did not fit the context budget)
- src/MessagePack.SourceGenerator/GeneratorUtilities.cs at base: not provided (did not fit the context budget)
- src/MessagePack.SourceGenerator/MessagePackGenerator.cs at base: not provided (did not fit the context budget)
- src/MessagePack.SourceGenerator/Transforms/StringKey/StringKeyFormatterTemplate.tt at base: not provided (did not fit the context budget)
- src/MessagePack.SourceGenerator/Utils/Constants.cs at base: not provided (did not fit the context budget)
- src/MessagePack.Annotations/Attributes.cs at head: only ±30 lines around the changes (the full file did not fit the budget)
- src/MessagePack.SourceGenerator/Analyzers/MsgPack00xMessagePackAnalyzer.cs at head: only ±30 lines around the changes (the full file did not fit the budget)
- src/MessagePack.SourceGenerator/CodeAnalysis/ObjectSerializationInfo.cs at head: only ±30 lines around the changes (the full file did not fit the budget)
- src/MessagePack.SourceGenerator/MessagePackGenerator.cs at head: only ±30 lines around the changes (the full file did not fit the budget)
- src/MessagePack.SourceGenerator/Transforms/FormatterTemplate.tt at head: only ±30 lines around the changes (the full file did not fit the budget)
- src/MessagePack.SourceGenerator/Transforms/StringKey/StringKeyFormatterTemplate.tt at head: only ±30 lines around the changes (the full file did not fit the budget)
- src/MessagePack.Annotations/Attributes.cs at base: only ±30 lines around the changes (the full file did not fit the budget)
- src/MessagePack.SourceGenerator/Analyzers/MsgPack00xMessagePackAnalyzer.cs at base: only ±30 lines around the changes (the full file did not fit the budget)
- src/MessagePack.SourceGenerator/Transforms/FormatterTemplate.tt at base: only ±30 lines around the changes (the full file did not fit the budget)
- README.md: diff only, full file not provided (doc)
- doc/analyzers/MsgPack019.md: diff only, full file not provided (doc)
- doc/analyzers/MsgPack020.md: diff only, full file not provided (doc)
- doc/analyzers/MsgPack021.md: diff only, full file not provided (doc)
- doc/analyzers/MsgPack022.md: diff only, full file not provided (doc)
- doc/analyzers/index.md: diff only, full file not provided (doc)
- src/MessagePack.SourceGenerator/AnalyzerReleases.Unshipped.md: diff only, full file not provided (build)
- tests/MessagePack.SourceGenerator.ExecutionTests/MessagePack.SourceGenerator.ExecutionTests.csproj: diff only, full file not provided (build)
- tests/MessagePack.SourceGenerator.ExternalTypes/MessagePack.SourceGenerator.ExternalTypes.csproj: diff only, full file not provided (build)
- tests/MessagePack.SourceGenerator.MapModeExecutionTests/MessagePack.SourceGenerator.MapModeExecutionTests.csproj: diff only, full file not provided (build)
- the upstream issue page itself (only its URL); other files of the repository; build and test logs (only the facts.json summaries)
