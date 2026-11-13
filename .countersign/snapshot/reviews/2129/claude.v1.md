# Review of #2129 by claude (claude-opus-5-5, review-v1), scoped

**Verdict:** A plausible implementation of the surrogate-type design the maintainer floated. The successful path is unverified here (no snapshot test, and the execution tests would not build in my environment), so REQ-2129-F1 is `cannot_determine`.

## Scope covered
I read GeneratedFormatterCollector.cs, the MessagePackGenerator.cs pipeline, GeneratorUtilities.cs, Attributes.cs, the analyzer descriptor additions, the template (.tt) changes, the README section and all new tests. I did not verify the regenerated template .cs files, the MsgPack019-022 doc pages or the test-project wiring in depth.

Ran: `MessagePack.SourceGenerator.Tests` net8.0 on head, 173/173 pass (6 new diagnostic tests).

## Findings
- **C1 (minor, maintainability):** MsgPack019-022 are declared on the analyzer but only reported by a new generator pipeline (`RegisterSourceOutput(generatedFormatterDiagnostics, ...)`). This goes against the repo's convention that the generator does not report diagnostics. The generator also reuses MsgPack004/005/010 descriptors.
- **C2 (minor, correctness):** Contractless mode ignores any attributes on T (`[IgnoreMember]`, `[IgnoreDataMember]`, `[Key]`, `[MessagePackObject]`). The maintainer's comment was "If there are attributes on it, fine, we'll use them." This can produce a wire contract that differs from the dynamic resolver's.
- **C3 (minor, tests):** No generator snapshot test of the emitted `partial class` formatter. The successful path is covered only by ExecutionTests (plus a new ExternalTypes project).
- **C4 (info, scope):** New public API, `GeneratedMessagePackFormatterAttribute.SurrogateType`, in MessagePack.Annotations. It needs API review.

## Refused
- Correctness of the generated formatter code (structs, init and required members, callbacks): needs execution tests.
- Interaction with TypeCollector and the analyzer (MsgPack003, double registration): needs a build.
- API and feature design: maintainer decision.
- The unreviewed remainder of the 28 files.
