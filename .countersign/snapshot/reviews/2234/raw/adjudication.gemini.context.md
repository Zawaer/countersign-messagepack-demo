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
# Change 2234: disputes to adjudicate (2)

Requirement clauses and their engine status:
```json
[
 {
  "id": "REQ-2234-F1",
  "text": "The analyzer must report contract diagnostics (e.g. missing [Key], duplicate keys, mixed key kinds) for [MessagePackObject(SuppressSourceGeneration = true)] types, as it did in version 3.1.0.",
  "status": "held_before"
 },
 {
  "id": "REQ-2234-F2",
  "text": "Diagnostics that only apply when a formatter is generated (partial-class requirement, AOT-only checks) must not be reported for types with SuppressSourceGeneration = true.",
  "status": "held_before"
 },
 {
  "id": "REQ-2234-N1",
  "text": "The analyzer and generator must not crash on invalid contracts (e.g. duplicate keys) in such types.",
  "status": "refused"
 },
 {
  "id": "REQ-2234-N2",
  "text": "The fix is covered by automated tests that fail without it; no regressions in the existing test suite.",
  "status": "refused"
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
  "summary": "8 passed, 0 failed, 0 skipped (8 new tests in run)"
 },
 {
  "id": "tests.fail_without_fix",
  "status": "pass",
  "summary": "new tests fail on base source: 4/8 failed -> tests do cover the change (4 new tests pass without the fix)"
 },
 {
  "id": "tests.full_suite",
  "status": "pass",
  "summary": "tests/MessagePack.SourceGenerator.Tests: 175 tests, 175 passed, 0 failed (0 not failing on base, 0 also failing on base)"
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
  "id": "tests.targeted.execution",
  "status": "pass",
  "summary": "SuppressedSourceGenerationTests: 4 passed, 0 failed (4 new test results; runtime: generator runs inside csc, no CS9057)"
 },
 {
  "id": "tests.execution_fail_without_fix",
  "status": "fail",
  "summary": "new runtime tests pass on base source: 0/4 failed -> these runtime tests do NOT demonstrate the change (runtime behaviour they check is identical with and without the fix)"
 },
 {
  "id": "tests.execution_full_suite",
  "status": "pass",
  "summary": "tests/MessagePack.SourceGenerator.ExecutionTests: 16/16 passed (base 14/14), 0 failures not on base; tests/MessagePack.SourceGenerator.MapModeExecutionTests: 22/22 passed (base 20/20), 0 failures not on base"
 },
 {
  "id": "repro.claude.C2",
  "status": "pass",
  "summary": "reproduced by the pipeline: failed on head (claim: failed), failed on base (claim: failed), passed on control (claim: passed)"
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
  "summary": "built on CRACI under a deny-by-default policy: only 13 TLS host patterns on ports 443 (github.com, codeload.github.com, objects.githubusercontent.com, api.nuget.org, *.nuget.org, pkgs.dev.azure.com, ...); presets ['github']; no blocked connection in 40 logs; every NuGet feed the head declares is inside the policy"
 }
]
```
Disputed items:
```json
[
 {
  "id": "REQ-2234-N1",
  "kind": "clause",
  "text": "The analyzer and generator must not crash on invalid contracts (e.g. duplicate keys) in such types.",
  "sides": [
   {
    "reviewer": "claude",
    "verdict": "not_met",
    "basis": "The duplicate-key and mixed-kind crashes are fixed, and the full suite passes (175/175). But not every invalid contract in such a type is crash-free. The hard cast at line 985 is untouched, and my probe (scratch worktree, SDK 8, not in facts.json) of '[MessagePackObject(SuppressSourceGeneration = true)] public record Cmd([property: Key(null)] string Scope)' still gives AD0001 InvalidCastException (ParameterSyntax to PropertyDeclarationSyntax) at this head. The generator side of the duplicate-key fix has no test in facts.json (the new analyzer tests use CSharpCodeFixVerifier, analyzer only), though my probe showed no CS8785 for duplicate keys at head.",
    "evidence": [
     {
      "kind": "code",
      "file": "src/MessagePack.SourceGenerator/CodeAnalysis/TypeCollector.cs",
      "line": 985,
      "rev": "head",
      "quote": "((PropertyDeclarationSyntax)item.DeclaringSyntaxReferences[0].GetSyntax()).Identifier.GetLocation()",
      "substantive": false,
      "context": "line 985 of src/MessagePack.SourceGenerator/CodeAnalysis/TypeCollector.cs is not a line this change touched (added at head)",
      "engine_verified": true,
      "engine_note": "quote matches src/MessagePack.SourceGenerator/CodeAnalysis/TypeCollector.cs:985 at head 9007cee1; context only, not counted: line 985 of src/MessagePack.SourceGenerator/CodeAnalysis/TypeCollector.cs is not a line this change touched (added at head)",
      "code_around_cited_line": "  ... lines 1-976 not shown ...\n  977|                     {\n  978|                         nestedFormatterRequiredIfPropertyIsNotSetByDeserializingCtor.Add(item);\n  979|                     }\n  980| \n  981|                     var intKey = key is { Value: int intKeyValue } ? intKeyValue : default(int?);\n  982|                     var stringKey = key is { Value: string stringKeyValue } ? stringKeyValue : default;\n  983|                     if (intKey == null && stringKey == null)\n  984|                     {\n  985|                         this.reportDiagnostic?.Invoke(Diagnostic.Create(MsgPack00xMessagePackAnalyzer.BothStringAndIntKeyAreNull, ((PropertyDeclarationSyntax)item.DeclaringSyntaxReferences[0].GetSyntax()).Identifier.GetLocation(), formattedType.ToDisplayString(SymbolDisplayFormat.FullyQualifiedFormat), item.Name));\n  986|                     }\n  987| \n  988|                     // A property with an init accessor and an initializer has a default that will be discarded by the deserializer.\n  989|                     if (suppressSourceGeneration is not true && isInitOnly)\n  990|                     {\n  991|                         EqualsValueClauseSyntax? initializer = item.DeclaringSyntaxReferences.Select(s => (s.GetSyntax(this.cancellationToken) as PropertyDeclarationSyntax)?.Initializer).FirstOrDefault(i => i is not null);\n  992|                         if (initializer is not null)\n  993|                         {\n  ... lines 994-1505 not shown ..."
     },
     {
      "kind": "check",
      "id": "tests.full_suite",
      "substantive": false,
      "engine_verified": true,
      "engine_note": "facts.json: tests.full_suite pass: tests/MessagePack.SourceGenerator.Tests: 175 tests, 175 passed, 0 failed (0 not failing on base, 0 also failing on base)"
     },
     {
      "kind": "test",
      "name": "SuppressSourceGenerationAnalyzerTests.DuplicateStringKeysAreReportedWithoutAnalyzerFailure",
      "outcome": "passed",
      "substantive": true,
      "engine_verified": true,
      "engine_note": "facts.json tests.targeted: passed (new test)"
     },
     {
      "kind": "requirement",
      "req": "REQ-2234-N1",
      "quote": "must not crash on invalid contracts (e.g. duplicate keys) in such types",
      "substantive": false,
      "engine_verified": true,
      "engine_note": "REQ-2234-N1 text contains the quote"
     }
    ]
   },
   {
    "reviewer": "codex",
    "verdict": "met",
    "basis": "The full source-generator suite passes, and duplicate-key tests demonstrate that invalid contracts no longer trigger analyzer failure.",
    "evidence": [
     {
      "kind": "check",
      "id": "tests.full_suite",
      "substantive": false,
      "engine_verified": true,
      "engine_note": "facts.json: tests.full_suite pass: tests/MessagePack.SourceGenerator.Tests: 175 tests, 175 passed, 0 failed (0 not failing on base, 0 also failing on base)"
     },
     {
      "kind": "test",
      "name": "SuppressSourceGenerationAnalyzerTests.DuplicateStringKeysAreReportedWithoutAnalyzerFailure",
      "outcome": "passed",
      "substantive": true,
      "engine_verified": true,
      "engine_note": "facts.json tests.targeted: passed (new test)"
     }
    ]
   },
   {
    "reviewer": "nemotron",
    "verdict": "not_met",
    "basis": "The duplicate-key analyzer crash is fixed on head, but the repro test PositionalRecordWithNullKeyDoesNotCrashAnalyzerForSuppressedType still fails on head with analyzer crash AD0001 InvalidCastException (ParameterSyntax cast to PropertyDeclarationSyntax) and no diagnostics; it also fails on base (pre-existing, not a regression) and passes on control branch origin/ju26-issue-2283, so a crash path for invalid contracts in suppressed types remains.",
    "evidence": [
     {
      "kind": "check",
      "id": "repro.claude.C2",
      "status": "pass",
      "substantive": true,
      "engine_verified": true,
      "engine_note": "facts.json: repro.claude.C2 pass: reproduced by the pipeline: failed on head (claim: failed), failed on base (claim: failed), passed on control (claim: passed)"
     },
     {
      "kind": "test",
      "name": "ReproClaude2234C2Tests.PositionalRecordWithNullKeyDoesNotCrashAnalyzerForSuppressedType",
      "outcome": "failed",
      "check": "repro.claude.C2",
      "substantive": false,
      "engine_verified": false,
      "engine_note": "test 'ReproClaude2234C2Tests.PositionalRecordWithNullKeyDoesNotCrashAnalyzerForSuppressedType' is not in facts.json"
     },
     {
      "kind": "test",
      "name": "SuppressSourceGenerationAnalyzerTests.DuplicateIntKeysAreReportedWithoutAnalyzerFailure",
      "outcome": "passed",
      "substantive": true,
      "engine_verified": true,
      "engine_note": "facts.json tests.targeted: passed (new test)"
     },
     {
      "kind": "test",
      "name": "SuppressSourceGenerationAnalyzerTests.DuplicateIntKeysAreReportedWithoutAnalyzerFailure",
      "outcome": "failed",
      "check": "tests.fail_without_fix",
      "substantive": true,
      "engine_verified": true,
      "engine_note": "facts.json tests.fail_without_fix: failed (new test)"
     }
    ]
   }
  ]
 },
 {
  "id": "finding:nemotron:N1-crash-remains",
  "kind": "finding",
  "text": "Analyzer still crashes on an invalid contract in a suppressed type: REQ-2234-N1 is not met on head: PositionalRecordWithNullKeyDoesNotCrashAnalyzerForSuppressedType fails on head with analyzer crash AD0001 (InvalidCastException: Unable to cast object of type 'ParameterSyntax' to type 'PropertyDeclarationSyntax') and no diagnostics. The same test fails on base (pre-existing, not a regression) and passes on control branch origin/ju26-issue-2283, which replaced the hard cast with a null-safe location lookup, so a crash path for invalid contracts in SuppressSourceGeneration types remains. The duplicate-key crashes from the issue are fixed on head (those tests pass on head and failed on base), but N1 requires no crash on invalid contracts generally.",
  "sides": [
   {
    "reviewer": "nemotron",
    "verdict": "blocker finding (verified)",
    "basis": "REQ-2234-N1 is not met on head: PositionalRecordWithNullKeyDoesNotCrashAnalyzerForSuppressedType fails on head with analyzer crash AD0001 (InvalidCastException: Unable to cast object of type 'ParameterSyntax' to type 'PropertyDeclarationSyntax') and no diagnostics. The same test fails on base (pre-existing, not a regression) and passes on control branch origin/ju26-issue-2283, which replaced the hard cast with a null-safe location lookup, so a crash path for invalid contracts in SuppressSourceGeneration types remains. The duplicate-key crashes from the issue are fixed on head (those tests pass on head and failed on base), but N1 requires no crash on invalid contracts generally.",
    "evidence": [
     {
      "kind": "check",
      "id": "repro.claude.C2",
      "status": "pass",
      "substantive": true,
      "engine_verified": true,
      "engine_note": "facts.json: repro.claude.C2 pass: reproduced by the pipeline: failed on head (claim: failed), failed on base (claim: failed), passed on control (claim: passed)"
     },
     {
      "kind": "test",
      "name": "ReproClaude2234C2Tests.PositionalRecordWithNullKeyDoesNotCrashAnalyzerForSuppressedType",
      "outcome": "failed",
      "check": "repro.claude.C2",
      "substantive": false,
      "engine_verified": false,
      "engine_note": "test 'ReproClaude2234C2Tests.PositionalRecordWithNullKeyDoesNotCrashAnalyzerForSuppressedType' is not in facts.json"
     },
     {
      "kind": "test",
      "name": "SuppressSourceGenerationAnalyzerTests.DuplicateIntKeysAreReportedWithoutAnalyzerFailure",
      "outcome": "passed",
      "substantive": true,
      "engine_verified": true,
      "engine_note": "facts.json tests.targeted: passed (new test)"
     },
     {
      "kind": "test",
      "name": "SuppressSourceGenerationAnalyzerTests.DuplicateIntKeysAreReportedWithoutAnalyzerFailure",
      "outcome": "failed",
      "check": "tests.fail_without_fix",
      "substantive": true,
      "engine_verified": true,
      "engine_note": "facts.json tests.fail_without_fix: failed (new test)"
     }
    ]
   }
  ],
  "not_raised_by": [
   "claude"
  ]
 }
]
```
Return only the JSON object described in the brief, one ruling per disputed item.