# Review of #2283 by claude (claude-opus-5-5, review-v1)

**Verdict:** This fixes the root cause. Two of the five requirements are not fully proven: the full suite was not run, and one cross-compilation case is untested.

## What the change does
- `TypeCollector.GetObjectInfo` indexed `DeclaringSyntaxReferences[0]` in two places in the base: line 985 (`BothStringAndIntKeyAreNull`) and line 1077 (`MemberNeedsKey`). The `MemberNeedsKey` site runs even in the generator, because the `Diagnostic.Create` is evaluated outside the `?.Invoke`. A closed generic **struct** from metadata exposes its private backing fields, which have no syntax, so the index throws. That matches the issue's "generic + value type + referenced assembly" triad. Both sites now use `FirstOrDefault`.
- All analyzer diagnostics are now routed through `ReportIfLocatedInCompilation`, which drops any diagnostic whose location is not in a syntax tree of the analyzed compilation (REQ-F3).

## Verified by running (net8.0, my worktree /tmp/claude-review-2283)
- `MessagePack.SourceGenerator.Tests`: 170/170 pass on head.
- The 3 new tests, with base `TypeCollector.cs` restored: all 3 fail with AD0001 (IndexOutOfRangeException) and CS8785. So the tests do cover the fix.

## Requirement verdicts
| Req | Verdict | Basis |
|---|---|---|
| F1 | met | Both `[0]` sites fixed; the test asserts the resolver hint name is generated |
| F2 | met | The harness runs all analyzers; no AD0001 on head |
| F3 | met | Filter at TypeCollector.cs:1446 (code reading; see C1 for the test gap) |
| N1 | cannot_determine | Execution tests did not build in my environment; see C2 |
| N2 | met | New tests fail on base source |

## Findings
- **C1 (minor, tests):** The tests use only `MetadataReference.CreateFromImage`. The case of a source-backed symbol from another compilation (the IDE's project-to-project `CompilationReference`), which F3 is really about, is not tested.
- **C2 (minor, correctness):** The filter drops *all* diagnostics whose location is not in source, including `Location.None` ones about current-compilation types. Example: MsgPack018 computes `location = null` when the colliding member has no syntax. Before, it was reported without a location; now it is silently dropped. I have not confirmed this path is reachable.
- **C3 (info, docs):** README and MsgPack004.md say the defining project reports these problems. That is only true if the defining project runs the MessagePack analyzer.

## Refused
- Full-suite regressions: ExecutionTests and MapModeExecutionTests failed to compile in my environment (CS0117 in a pre-existing file), and I did not run net472.
- IDE behaviour with project references.
- Whether the C2 path is reachable.
