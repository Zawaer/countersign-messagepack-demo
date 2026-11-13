# Review of #2297 by claude (claude-opus-5-5, review-v1), scoped

**Verdict:** REQ-2297-F1 is not met. The attribute is fenced off from netstandard2.0 and .NET Framework, based on a false claim that it is unavailable there. Putting it on user-declared partial resolvers can also break existing builds (CS0579).

## Scope covered
I read the 7 template pairs (.tt and generated .cs), TransformUtilities.cs, the README and CodeCoverageExclusionTests.cs. The 222 `*.g.cs` snapshots were not read individually; I relied on the snapshot comparison in the test suite.

Ran (net8.0, /tmp/claude-review-2297):
- `MessagePack.SourceGenerator.Tests`: 169/169 pass on head (snapshots match the templates).
- CodeCoverageExclusionTests against base templates: 2/2 fail, so the tests cover the change.
- Checked `ExcludeFromCodeCoverageAttribute` in the netstandard.library 2.0.3 `netstandard.dll` and the .NET Framework 4.7.2 `System.dll`: it is present in both. A netstandard2.0 project using it compiles. Two partial declarations each carrying it produce CS0579.

## Findings
- **C1 (major, correctness):** The `#if !NETSTANDARD2_0 && !NETFRAMEWORK` guard leaves out targets where the attribute exists (.NET Framework 4.0+, netstandard2.0). The README and the test comment state the false premise, and the second test locks the guard in.
- **C2 (major, correctness):** The resolver and composite-resolver templates put the attribute on the generated half of a user-declared `partial class`. The attribute has `AllowMultiple = false`, so a user who already put `[ExcludeFromCodeCoverage]` on their resolver gets CS0579 after upgrading. Even without that conflict, the user's own members in that class are excluded from coverage.
- **C3 (info, scope):** The TransformUtilities `{` to `{\r\n` change is needed for `#if` placement, but it changes output for nested generic types.

## Refused
- Contents of the individual snapshot files.
- Whether maintainers want this (and `[GeneratedCode]`) at all: there is no maintainer answer in the issue.
- Real coverage-tool behaviour.
