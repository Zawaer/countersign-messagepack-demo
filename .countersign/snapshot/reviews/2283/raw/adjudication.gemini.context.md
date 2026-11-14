<!-- system prompt -->
# Countersign adjudicator brief, adjudicate-v1

<!-- prompt_version: adjudicate-v1. Given to the adjudicator (Gemini) only when reviewers disagree. -->

You are the **adjudicator** for a code review in which independent AI reviewers disagree. You are an evidence
auditor, not a judge of the code and not an approver: **nothing you say can clear a change or a requirement**. The
decision engine will only use your ruling to add reasons and to route the item to a named human owner. Your job is
to make that human's reading fast: say which side's claims are actually supported by the evidence each side cited,
which are not, and what evidence would settle the question.

## What you get, per disputed item

- `id`: the requirement clause (`REQ-…`) or the finding (`finding:<reviewer>:<id>`) in dispute, with its text.
- `sides`: each reviewer's verdict, its stated basis, and the evidence it cited. Each evidence item carries the
  engine's own verification result: `verified` (true/false) and a `note` saying exactly what was checked (e.g. "quote
  matches file:line at head", "test is not in facts.json", "issue text cannot be verified offline").
- For `code` evidence, the surrounding lines of that file at that revision, with line numbers.
- The deterministic checks (facts.json summary) for the change.

## Rules

- Judge **only** from what is in front of you. A verified quote proves that the line exists, not that it means what
  the reviewer says; decide whether the cited lines actually support the claim.
- Unverified evidence supports nothing. Say so.
- If neither side's evidence settles the item, say that, and name the concrete evidence that would: a specific
  test (and what it must assert), a file/line to read, a check to run.
- Do not introduce new claims about the code that nobody cited. Do not say "met", "proven", "approve" or "safe to
  merge": that is not your role.

## Output

Return **only** one JSON object, no prose, no Markdown fences:

```json
{
  "rulings": [
    {"dispute": "<id exactly as given>",
     "supported": [{"reviewer": "name", "claim": "the claim, briefly", "why": "which cited evidence supports it"}],
     "unsupported": [{"reviewer": "name", "claim": "the claim, briefly", "why": "what is missing or contradicts it"}],
     "evidence_that_would_settle": ["concrete evidence, e.g. a test that …"],
     "route_to": "who should decide, e.g. area owner",
     "note": "optional, one sentence"}
  ]
}
```

One ruling per disputed item, using the `dispute` id exactly as given.


<!-- user message -->
# Change 2283: disputes to adjudicate (2)

Requirement clauses and their engine status:
```json
[
 {
  "id": "REQ-2283-F1",
  "text": "Building a project whose [MessagePackObject] type has a member of a closed generic value type defined in a referenced assembly must not crash the source generator (no CS8785) and must produce a generated resolver.",
  "status": "proven"
 },
 {
  "id": "REQ-2283-F2",
  "text": "The MsgPack00x analyzer must not throw (no AD0001) for the same input.",
  "status": "proven"
 },
 {
  "id": "REQ-2283-F3",
  "text": "Diagnostics about members of a type declared in a referenced assembly must not be reported at locations outside the compilation being analyzed.",
  "status": "proven"
 },
 {
  "id": "REQ-2283-N1",
  "text": "Existing analyzer diagnostics for types declared in the current compilation keep working unchanged (no regressions in the existing test suite).",
  "status": "refused"
 },
 {
  "id": "REQ-2283-N2",
  "text": "The fix is covered by automated tests that fail without it.",
  "status": "proven"
 }
]
```
Deterministic checks (facts.json):
```json
[
 {
  "id": "build",
  "status": "pass",
  "summary": "0 errors, 1 unique warnings"
 },
 {
  "id": "tests.targeted",
  "status": "pass",
  "summary": "19 passed, 0 failed, 0 skipped (3 new tests in run)"
 },
 {
  "id": "tests.fail_without_fix",
  "status": "pass",
  "summary": "new tests fail on base source: 3/3 failed -> tests do cover the change"
 },
 {
  "id": "tests.full_suite",
  "status": "pass",
  "summary": "tests/MessagePack.SourceGenerator.Tests: 170 tests, 170 passed, 0 failed (0 not failing on base, 0 also failing on base)"
 },
 {
  "id": "public_api",
  "status": "pass",
  "summary": "no public API changes: no PublicAPI.Shipped/Unshipped.txt changed, no public/protected declarations added or removed in src/"
 },
 {
  "id": "analyzers",
  "status": "pass",
  "summary": "no new warnings"
 },
 {
  "id": "repro.claude.C1",
  "status": "pass",
  "summary": "reproduced by the pipeline: failed on head (claim: failed), passed on base (claim: passed)"
 },
 {
  "id": "injection_scan",
  "status": "pass",
  "summary": "no text addressed to automated reviewers in the added lines, commit message or PR text"
 },
 {
  "id": "deps.delta",
  "status": "pass",
  "summary": "238 packages on head (238 on base) across 30 projects; 0 added, 0 version changes, 0 removed; 0 new vulnerability hits (6 already on base)"
 },
 {
  "id": "build.egress",
  "status": "pass",
  "summary": "built on CRACI under a deny-by-default policy: only 13 TLS host patterns on ports 443 (github.com, codeload.github.com, objects.githubusercontent.com, api.nuget.org, *.nuget.org, pkgs.dev.azure.com, ...); presets ['github']; no blocked connection in 19 logs; every NuGet feed the head declares is inside the policy"
 }
]
```
Disputed items:
```json
[
 {
  "id": "REQ-2283-N1",
  "kind": "clause",
  "text": "Existing analyzer diagnostics for types declared in the current compilation keep working unchanged (no regressions in the existing test suite).",
  "sides": [
   {
    "reviewer": "claude",
    "verdict": "not_met",
    "basis": "The existing suite passes (170/170, no new failures), so the parenthetical part holds, but the clause's main statement does not: the location filter also drops diagnostics about types declared in the current compilation when the reporting location is a metadata member. My probe (scratch worktree, SDK 8, not in facts.json): metadata generic class Lib.Item<T> with [Key(0)] T Content, used as Item<Foo> where App.Foo lacks [MessagePackObject]; base reports MsgPack003 'Type must be marked with MessagePackObjectAttribute: Item.Content', head reports nothing. Item<T> as a class did not crash on base (issue table: 'class Item<T> | ok'), so this is a regression in a configuration that worked before. The existing suite does not cover it.",
    "evidence": [
     {
      "kind": "code",
      "file": "src/MessagePack.SourceGenerator/CodeAnalysis/TypeCollector.cs",
      "line": 1341,
      "rev": "head",
      "quote": "Location location = callerSymbol is not null ? callerSymbol.Locations[0] : formattedType.Locations[0];",
      "substantive": false,
      "context": "line 1341 of src/MessagePack.SourceGenerator/CodeAnalysis/TypeCollector.cs is not a line this change touched (added at head)",
      "engine_verified": true,
      "engine_note": "quote matches src/MessagePack.SourceGenerator/CodeAnalysis/TypeCollector.cs:1341 at head 9df83c38; context only, not counted: line 1341 of src/MessagePack.SourceGenerator/CodeAnalysis/TypeCollector.cs is not a line this change touched (added at head)",
      "code_around_cited_line": "  ... lines 1-1332 not shown ...\n 1333|             needsCastOnBefore = !formattedType.GetMembers(\"OnBeforeSerialize\").Any();\n 1334|             needsCastOnAfter = !formattedType.GetMembers(\"OnAfterDeserialize\").Any();\n 1335|         }\n 1336| \n 1337|         if (contractAttr is null)\n 1338|         {\n 1339|             if (formattedType.IsDefinition)\n 1340|             {\n 1341|                 Location location = callerSymbol is not null ? callerSymbol.Locations[0] : formattedType.Locations[0];\n 1342|                 var targetName = callerSymbol is not null ? callerSymbol.ContainingType.Name + \".\" + callerSymbol.Name : formattedType.Name;\n 1343| \n 1344|                 ImmutableDictionary<string, string?> typeInfo = ImmutableDictionary.Create<string, string?>().Add(\"type\", formattedType.ToDisplayString(SymbolDisplayFormat.FullyQualifiedFormat));\n 1345|                 this.reportDiagnostic?.Invoke(Diagnostic.Create(MsgPack00xMessagePackAnalyzer.TypeMustBeMessagePackObject, location, typeInfo, targetName));\n 1346|             }\n 1347| \n 1348|             // Indicate to our caller that we don't have a valid object.\n 1349|             return null;\n  ... lines 1350-1514 not shown ..."
     },
     {
      "kind": "code",
      "file": "src/MessagePack.SourceGenerator/CodeAnalysis/TypeCollector.cs",
      "line": 1446,
      "rev": "head",
      "quote": "diagnostic.Location.IsInSource",
      "substantive": true,
      "engine_verified": true,
      "engine_note": "quote matches src/MessagePack.SourceGenerator/CodeAnalysis/TypeCollector.cs:1446 at head 9df83c38",
      "code_around_cited_line": "  ... lines 1-1437 not shown ...\n 1438|     /// </summary>\n 1439|     /// <remarks>\n 1440|     /// Types and members that come from metadata (or from another compilation) have no location in the compilation being analyzed.\n 1441|     /// Their problems are reported by the compilation that defines them, so they are dropped here rather than being reported\n 1442|     /// against a location that does not exist, which analyzers are not permitted to do.\n 1443|     /// </remarks>\n 1444|     private void ReportIfLocatedInCompilation(Action<Diagnostic> report, Diagnostic diagnostic)\n 1445|     {\n 1446|         if (diagnostic.Location.IsInSource && this.compilation.ContainsSyntaxTree(diagnostic.Location.SourceTree))\n 1447|         {\n 1448|             report(diagnostic);\n 1449|         }\n 1450|     }\n 1451| \n 1452|     private static Location? GetLocation(IParameterSymbol parameter) => parameter.DeclaringSyntaxReferences.FirstOrDefault()?.GetSyntax().GetLocation();\n 1453| \n 1454|     private static Location? GetParameterListLocation(IMethodSymbol? method) => ((BaseMethodDeclarationSyntax?)method?.DeclaringSyntaxReferences.FirstOrDefault()?.GetSyntax())?.ParameterList.GetLocation();\n  ... lines 1455-1514 not shown ..."
     },
     {
      "kind": "check",
      "id": "tests.full_suite",
      "substantive": false,
      "engine_verified": true,
      "engine_note": "facts.json: tests.full_suite pass: tests/MessagePack.SourceGenerator.Tests: 170 tests, 170 passed, 0 failed (0 not failing on base, 0 also failing on base)"
     },
     {
      "kind": "requirement",
      "req": "REQ-2283-N1",
      "quote": "Existing analyzer diagnostics for types declared in the current compilation keep working unchanged",
      "substantive": false,
      "engine_verified": true,
      "engine_note": "REQ-2283-N1 text contains the quote"
     },
     {
      "kind": "issue",
      "url": "https://github.com/MessagePack-CSharp/MessagePack-CSharp/issues/2283",
      "quote": "| `class Item<T>` | ok |",
      "substantive": false,
      "engine_verified": false,
      "engine_note": "issue text cannot be verified offline (not counted as evidence)"
     }
    ]
   },
   {
    "reviewer": "codex",
    "verdict": "met",
    "basis": "The source-generator test suite passes in full after the change.",
    "evidence": [
     {
      "kind": "check",
      "id": "tests.full_suite",
      "substantive": false,
      "engine_verified": true,
      "engine_note": "facts.json: tests.full_suite pass: tests/MessagePack.SourceGenerator.Tests: 170 tests, 170 passed, 0 failed (0 not failing on base, 0 also failing on base)"
     }
    ]
   },
   {
    "reviewer": "nemotron",
    "verdict": "met",
    "basis": "The full source-generator suite passes on head: 170 passed, 0 failed, with no test newly failing (failures_not_on_base empty, failures_also_on_base empty).",
    "evidence": [
     {
      "kind": "check",
      "id": "tests.full_suite",
      "status": "pass",
      "substantive": true,
      "engine_verified": true,
      "engine_note": "facts.json: tests.full_suite pass: tests/MessagePack.SourceGenerator.Tests: 170 tests, 170 passed, 0 failed (0 not failing on base, 0 also failing on base)"
     }
    ]
   }
  ]
 },
 {
  "id": "finding:claude:C1",
  "kind": "finding",
  "text": "Location filter silently drops MsgPack003 about an in-compilation type reached through a metadata generic: ReportIfLocatedInCompilation drops every diagnostic whose location is not a source location in this compilation, including Location.None and metadata locations, which Roslyn does allow analyzers to report. TypeMustBeMessagePackObject (MsgPack003) is located at callerSymbol.Locations[0]; when the caller is a member of a referenced generic (Lib.Item<T>.Content) and T is an app type without [MessagePackObject] (Item<Foo>), the diagnostic is about App.Foo but is now discarded. My probe: base reports MsgPack003 (metadata location), head reports nothing, while the generator still emits App.R.g.cs and a formatter for Lib.Item`1, so the missing Foo formatter would only surface at run time. This configuration (a generic class from another assembly) did not crash on base, so it is a regression. The XML doc comment's justification ('which analyzers are not permitted to do') is only true for source locations in other compilations.",
  "sides": [
   {
    "reviewer": "claude",
    "verdict": "major finding (verified)",
    "basis": "ReportIfLocatedInCompilation drops every diagnostic whose location is not a source location in this compilation, including Location.None and metadata locations, which Roslyn does allow analyzers to report. TypeMustBeMessagePackObject (MsgPack003) is located at callerSymbol.Locations[0]; when the caller is a member of a referenced generic (Lib.Item<T>.Content) and T is an app type without [MessagePackObject] (Item<Foo>), the diagnostic is about App.Foo but is now discarded. My probe: base reports MsgPack003 (metadata location), head reports nothing, while the generator still emits App.R.g.cs and a formatter for Lib.Item`1, so the missing Foo formatter would only surface at run time. This configuration (a generic class from another assembly) did not crash on base, so it is a regression. The XML doc comment's justification ('which analyzers are not permitted to do') is only true for source locations in other compilations.",
    "evidence": [
     {
      "kind": "code",
      "file": "src/MessagePack.SourceGenerator/CodeAnalysis/TypeCollector.cs",
      "line": 1446,
      "rev": "head",
      "quote": "if (diagnostic.Location.IsInSource && this.compilation.ContainsSyntaxTree(diagnostic.Location.SourceTree))",
      "substantive": true,
      "engine_verified": true,
      "engine_note": "quote matches src/MessagePack.SourceGenerator/CodeAnalysis/TypeCollector.cs:1446 at head 9df83c38",
      "code_around_cited_line": "  ... lines 1-1437 not shown ...\n 1438|     /// </summary>\n 1439|     /// <remarks>\n 1440|     /// Types and members that come from metadata (or from another compilation) have no location in the compilation being analyzed.\n 1441|     /// Their problems are reported by the compilation that defines them, so they are dropped here rather than being reported\n 1442|     /// against a location that does not exist, which analyzers are not permitted to do.\n 1443|     /// </remarks>\n 1444|     private void ReportIfLocatedInCompilation(Action<Diagnostic> report, Diagnostic diagnostic)\n 1445|     {\n 1446|         if (diagnostic.Location.IsInSource && this.compilation.ContainsSyntaxTree(diagnostic.Location.SourceTree))\n 1447|         {\n 1448|             report(diagnostic);\n 1449|         }\n 1450|     }\n 1451| \n 1452|     private static Location? GetLocation(IParameterSymbol parameter) => parameter.DeclaringSyntaxReferences.FirstOrDefault()?.GetSyntax().GetLocation();\n 1453| \n 1454|     private static Location? GetParameterListLocation(IMethodSymbol? method) => ((BaseMethodDeclarationSyntax?)method?.DeclaringSyntaxReferences.FirstOrDefault()?.GetSyntax())?.ParameterList.GetLocation();\n  ... lines 1455-1514 not shown ..."
     },
     {
      "kind": "code",
      "file": "src/MessagePack.SourceGenerator/CodeAnalysis/TypeCollector.cs",
      "line": 1341,
      "rev": "head",
      "quote": "callerSymbol.Locations[0]",
      "substantive": true,
      "engine_verified": true,
      "engine_note": "quote matches src/MessagePack.SourceGenerator/CodeAnalysis/TypeCollector.cs:1341 at head 9df83c38",
      "code_around_cited_line": "  ... lines 1-1332 not shown ...\n 1333|             needsCastOnBefore = !formattedType.GetMembers(\"OnBeforeSerialize\").Any();\n 1334|             needsCastOnAfter = !formattedType.GetMembers(\"OnAfterDeserialize\").Any();\n 1335|         }\n 1336| \n 1337|         if (contractAttr is null)\n 1338|         {\n 1339|             if (formattedType.IsDefinition)\n 1340|             {\n 1341|                 Location location = callerSymbol is not null ? callerSymbol.Locations[0] : formattedType.Locations[0];\n 1342|                 var targetName = callerSymbol is not null ? callerSymbol.ContainingType.Name + \".\" + callerSymbol.Name : formattedType.Name;\n 1343| \n 1344|                 ImmutableDictionary<string, string?> typeInfo = ImmutableDictionary.Create<string, string?>().Add(\"type\", formattedType.ToDisplayString(SymbolDisplayFormat.FullyQualifiedFormat));\n 1345|                 this.reportDiagnostic?.Invoke(Diagnostic.Create(MsgPack00xMessagePackAnalyzer.TypeMustBeMessagePackObject, location, typeInfo, targetName));\n 1346|             }\n 1347| \n 1348|             // Indicate to our caller that we don't have a valid object.\n 1349|             return null;\n  ... lines 1350-1514 not shown ..."
     },
     {
      "kind": "code",
      "file": "src/MessagePack.SourceGenerator/CodeAnalysis/TypeCollector.cs",
      "line": 1442,
      "rev": "head",
      "quote": "which analyzers are not permitted to do",
      "substantive": true,
      "engine_verified": true,
      "engine_note": "quote matches src/MessagePack.SourceGenerator/CodeAnalysis/TypeCollector.cs:1442 at head 9df83c38",
      "code_around_cited_line": "  ... lines 1-1433 not shown ...\n 1434|     private static Location? GetPropertyIdentifierLocation(IPropertySymbol property) => (property.DeclaringSyntaxReferences.FirstOrDefault()?.GetSyntax() as PropertyDeclarationSyntax)?.Identifier.GetLocation();\n 1435| \n 1436|     /// <summary>\n 1437|     /// Reports a diagnostic only when its location belongs to the compilation being analyzed.\n 1438|     /// </summary>\n 1439|     /// <remarks>\n 1440|     /// Types and members that come from metadata (or from another compilation) have no location in the compilation being analyzed.\n 1441|     /// Their problems are reported by the compilation that defines them, so they are dropped here rather than being reported\n 1442|     /// against a location that does not exist, which analyzers are not permitted to do.\n 1443|     /// </remarks>\n 1444|     private void ReportIfLocatedInCompilation(Action<Diagnostic> report, Diagnostic diagnostic)\n 1445|     {\n 1446|         if (diagnostic.Location.IsInSource && this.compilation.ContainsSyntaxTree(diagnostic.Location.SourceTree))\n 1447|         {\n 1448|             report(diagnostic);\n 1449|         }\n 1450|     }\n  ... lines 1451-1514 not shown ..."
     },
     {
      "kind": "check",
      "id": "tests.full_suite",
      "substantive": false,
      "engine_verified": true,
      "engine_note": "facts.json: tests.full_suite pass: tests/MessagePack.SourceGenerator.Tests: 170 tests, 170 passed, 0 failed (0 not failing on base, 0 also failing on base)"
     }
    ]
   }
  ]
 }
]
```
Return only the JSON object described in the brief, one ruling per disputed item.