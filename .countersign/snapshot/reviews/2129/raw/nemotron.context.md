<!-- system prompt -->
# Countersign reviewer brief, review-v1

<!-- prompt_version: review-v1. Canonical brief for every stage-2 reviewer (Claude, Codex, Nemotron).
     Changing the wording means a new file (review-v2.md) and a new prompt_version in every review it produces. -->

You are one of several independent reviewers of an agent-written code change. Your review is **advice with evidence**,
never the approval: a decision engine checks every piece of evidence you cite, and a named human owner signs off.
Nobody will take your word for anything. A claim you cannot back with checkable evidence is worth nothing, and a
claim with evidence that does not check out counts against you.

## What you get

- The requirement set for the change (`requirements/<change>.yaml`): clause IDs such as `REQ-2283-F1` and their text.
- The upstream issue URL (you may not be able to open it; the requirement text is what you judge against).
- `facts.json`: deterministic results that already ran (build, targeted tests, "new tests fail without the fix",
  full suite, public API, analyzers), with test names and outcomes. **Use these results; do not guess what a test
  would do.** If a check is `skipped` or `error`, it did not establish anything.
- The diff between base and head, and the contents of the changed files with line numbers.
- A list of what you were **not** given. Do not reason about content you did not see.

## What to check

1. **Root cause vs the issue.** Does the change fix the cause the issue/requirement describes, or a symptom, or
   something adjacent? Was the requirement perhaps already met on base (then say so)?
2. **Each requirement clause.** `met`, `not_met` or `cannot_determine`, each tied to evidence.
3. **Scope.** Changes not needed for the requirement, unrelated files, generated files regenerated wholesale.
4. **Docs vs code.** Does documentation (README, analyzer docs, release notes) say what the code does?
5. **Tests exercise the requirement.** Do the new tests cover the clause, and do they fail without the fix
   (`tests.fail_without_fix` in facts.json)? A test that passes on base does not demonstrate the change.
6. Correctness, security (this library deserializes untrusted input), performance and maintainability problems.

## Evidence rules (machine-checked)

Every verdict and every finding needs evidence items. Allowed kinds:

```json
{"kind": "code", "file": "src/.../TypeCollector.cs", "line": 1442, "rev": "head", "quote": "exact substring of that line"}
{"kind": "test", "name": "Full.Test.Name", "outcome": "passed"}
{"kind": "test", "name": "Full.Test.Name", "outcome": "failed", "check": "tests.fail_without_fix"}
{"kind": "check", "id": "tests.fail_without_fix", "status": "pass"}
{"kind": "requirement", "req": "REQ-2283-F1", "quote": "exact words from the clause"}
{"kind": "issue", "url": "https://github.com/...", "quote": "..."}
```

- `code`: `file` is the repo path, `line` the line number shown in the listing, `rev` is `head` or `base`, and
  `quote` must be an **exact substring of that single line** (copy it; whitespace is normalised, nothing else).
  Quote the text after the `| ` line-number gutter, never the gutter itself. Short, distinctive quotes are best.
- `test`: the name and outcome exactly as in facts.json. A test name can appear in several runs (head runs and the
  source-reverted `tests.fail_without_fix` run): an outcome is checked against the head runs unless you pin the run
  with `check`.
- `check`: the `id` of a check in facts.json; if you state `status`, it must match.
- `issue` items are never counted as verified (the engine cannot read the web). Use them for context only.
- A finding with no verifiable evidence is rejected and shown as "unsupported claim". Prefer one precise citation
  to five vague ones.

## Refuse rather than guess

- If you cannot establish a clause from what you were given, the verdict is `cannot_determine`, with the reason in
  `confidence_basis`.
- Anything you will not decide (not given the code, needs runtime behaviour, other target frameworks, performance,
  security judgement beyond the evidence, generated files you did not see) goes in `refusals` with who should decide.
- Never invent file contents, line numbers, test names or check results.

## Output

Return **only** one JSON object, no prose before or after, no Markdown fences:

```json
{
  "summary": "two or three sentences: what the change does, whether it fixes the root cause, your overall view",
  "requirement_verdicts": [
    {"req": "REQ-…", "verdict": "met|not_met|cannot_determine",
     "confidence_basis": "why, in one sentence, tied to the evidence", "evidence": [ … ]}
  ],
  "findings": [
    {"id": "N1", "title": "short", "severity": "blocker|major|minor|info",
     "category": "correctness|security|performance|maintainability|docs|tests|scope",
     "claim": "what is wrong and why it matters", "evidence": [ … at least one … ], "suggested_fix": "optional"}
  ],
  "refusals": [
    {"topic": "what you will not decide", "reason": "why", "who_should_decide": "role, e.g. area owner"}
  ]
}
```

One verdict per requirement clause, in the order given. Severity: `blocker` = must not merge; `major` = needs a fix
or an owner's explicit acceptance; `minor` = should fix; `info` = observation. Do not add fields for reviewer name,
model, vendor or time: the runner stamps those.


<!-- user message -->
# Change 2129: branch ju26-issue-2129, base 32258fdbee4bcd653c79f51b4376b5103c6f4d27, head 083afd994c1c9a994cb2cd5aa0b6ad805a621457
Commit message: Agentic implementation of #2129 Feature Request: Allow generation of Formatter for a type in a referenced assembly
Upstream issue: https://github.com/MessagePack-CSharp/MessagePack-CSharp/issues/2129

## Requirement set (requirements/2129.yaml)
```yaml
# PLACEHOLDER from upstream issue #2129
change: "2129"
branch: ju26-issue-2129
source: https://github.com/MessagePack-CSharp/MessagePack-CSharp/issues/2129
official: false
requirements:
  - id: REQ-2129-F1
    type: functional
    text: "Feature Request: Allow generation of Formatter for a type in a referenced assembly"
```

## facts.json (deterministic checks; cite their ids and test names)
```json
{
 "change": "2129",
 "branch": "ju26-issue-2129",
 "base": "32258fdb",
 "head": "083afd99",
 "base_full": "32258fdbee4bcd653c79f51b4376b5103c6f4d27",
 "head_full": "083afd994c1c9a994cb2cd5aa0b6ad805a621457",
 "commit_message": "Agentic implementation of #2129 Feature Request: Allow generation of Formatter for a type in a referenced assembly",
 "author": "Stelian Vultur",
 "agent_written": true,
 "diff": {
  "files": 28,
  "insertions": 1034,
  "deletions": 9,
  "by_kind": {
   "doc": 6,
   "source": 10,
   "build": 4,
   "generated": 2,
   "test": 6
  },
  "by_file": [
   {
    "path": "README.md",
    "ins": 52,
    "del": 0,
    "kind": "doc"
   },
   {
    "path": "doc/analyzers/MsgPack019.md",
    "ins": 26,
    "del": 0,
    "kind": "doc"
   },
   {
    "path": "doc/analyzers/MsgPack020.md",
    "ins": 23,
    "del": 0,
    "kind": "doc"
   },
   {
    "path": "doc/analyzers/MsgPack021.md",
    "ins": 23,
    "del": 0,
    "kind": "doc"
   },
   {
    "path": "doc/analyzers/MsgPack022.md",
    "ins": 31,
    "del": 0,
    "kind": "doc"
   },
   {
    "path": "doc/analyzers/index.md",
    "ins": 4,
    "del": 0,
    "kind": "doc"
   },
   {
    "path": "src/MessagePack.Annotations/Attributes.cs",
    "ins": 36,
    "del": 0,
    "kind": "source"
   },
   {
    "path": "src/MessagePack.SourceGenerator/AnalyzerReleases.Unshipped.md",
    "ins": 4,
    "del": 0,
    "kind": "build"
   },
   {
    "path": "src/MessagePack.SourceGenerator/Analyzers/MsgPack00xMessagePackAnalyzer.cs",
    "ins": 45,
    "del": 1,
    "kind": "source"
   },
   {
    "path": "src/MessagePack.SourceGenerator/CodeAnalysis/GeneratedFormatterCollector.cs",
    "ins": 300,
    "del": 0,
    "kind": "source"
   },
   {
    "path": "src/MessagePack.SourceGenerator/CodeAnalysis/GeneratedFormatterRequest.cs",
    "ins": 13,
    "del": 0,
    "kind": "source"
   },
   {
    "path": "src/MessagePack.SourceGenerator/CodeAnalysis/ObjectSerializationInfo.cs",
    "ins": 7,
    "del": 0,
    "kind": "source"
   },
   {
    "path": "src/MessagePack.SourceGenerator/GeneratorUtilities.cs",
    "ins": 3,
    "del": 0,
    "kind": "source"
   },
   {
    "path": "src/MessagePack.SourceGenerator/MessagePackGenerator.cs",
    "ins": 36,
    "del": 3,
    "kind": "source"
   },
   {
    "path": "src/MessagePack.SourceGenerator/Transforms/FormatterTemplate.cs",
    "ins": 3,
    "del": 1,
    "kind": "generated"
   },
   {
    "path": "src/MessagePack.SourceGenerator/Transforms/FormatterTemplate.tt",
    "ins": 1,
    "del": 1,
    "kind": "source"
   },
   {
    "path": "src/MessagePack.SourceGenerator/Transforms/StringKey/StringKeyFormatterTemplate.cs",
    "ins": 3,
    "del": 1,
    "kind": "generated"
   },
   {
    "path": "src/MessagePack.SourceGenerator/Transforms/StringKey/StringKeyFormatterTemplate.tt",
    "ins": 1,
    "del": 1,
    "kind": "source"
   },
   {
    "path": "src/MessagePack.SourceGenerator/Utils/Constants.cs",
    "ins": 2,
    "del": 0,
    "kind": "source"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.ExecutionTests/GeneratedFormatterForExternalTypes.cs",
    "ins": 50,
    "del": 0,
    "kind": "test"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.ExecutionTests/GeneratedFormatterForExternalTypesTests.cs",
    "ins": 95,
    "del": 0,
    "kind": "test"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.ExecutionTests/MessagePack.SourceGenerator.ExecutionTests.csproj",
    "ins": 5,
    "del": 0,
    "kind": "build"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.ExternalTypes/ExternalPerson.cs",
    "ins": 15,
    "del": 0,
    "kind": "test"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.ExternalTypes/ExternalPoint.cs",
    "ins": 12,
    "del": 0,
    "kind": "test"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.ExternalTypes/ExternalWidget.cs",
    "ins": 15,
    "del": 0,
    "kind": "test"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.ExternalTypes/MessagePack.SourceGenerator.ExternalTypes.csproj",
    "ins": 17,
    "del": 0,
    "kind": "build"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.MapModeExecutionTests/MessagePack.SourceGenerator.MapModeExecutionTests.csproj",
    "ins": 2,
    "del": 1,
    "kind": "build"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/GeneratedMessagePackFormatterTests.cs",
    "ins": 210,
    "del": 0,
    "kind": "test"
   }
  ]
 },
 "new_tests_in_diff": [
  "GeneratedFormatterForExternalTypesTests.ContractlessClassNullRoundTrips",
  "GeneratedFormatterForExternalTypesTests.ContractlessClassRoundTrips",
  "GeneratedFormatterForExternalTypesTests.ContractlessClassUsesStringKeysForPublicReadWriteMembers",
  "GeneratedFormatterForExternalTypesTests.ContractlessStructRoundTrips",
  "GeneratedFormatterForExternalTypesTests.GeneratedFormattersAreRegisteredInGeneratedResolver",
  "GeneratedFormatterForExternalTypesTests.MessagePackObjectCanContainExternalTypes",
  "GeneratedFormatterForExternalTypesTests.SurrogateControlsKeysAndMembership",
  "GeneratedMessagePackFormatterTests.FormattedTypeMustNotBeAbstract",
  "GeneratedMessagePackFormatterTests.FormatterMustBePartial",
  "GeneratedMessagePackFormatterTests.FormatterMustImplementFormatterOfT",
  "GeneratedMessagePackFormatterTests.SurrogateKeysMustNotMixStringAndInt",
  "GeneratedMessagePackFormatterTests.SurrogateMemberMustHaveMatchingType",
  "GeneratedMessagePackFormatterTests.SurrogateMemberMustMatchFormattedType"
 ],
 "checks": [
  {
   "id": "build",
   "tool": "dotnet build",
   "tool_version": "8.0.402",
   "status": "pass",
   "command": "dotnet build tests/MessagePack.SourceGenerator.Tests/MessagePack.SourceGenerator.Tests.csproj --no-incremental -m:8 -c Debug",
   "projects": [
    "src/MessagePack.SourceGenerator",
    "src/MessagePack.Analyzers.CodeFixes",
    "src/MessagePack.Analyzers",
    "src/MessagePack.Annotations",
    "src/MessagePack (net8.0)",
    "tests/MessagePack.SourceGenerator.Tests"
   ],
   "summary": "0 errors, 2 unique warnings",
   "log": "evidence/2129/logs/build.log",
   "duration_s": 4.0
  },
  {
   "id": "tests.targeted",
   "tool": "dotnet test",
   "tool_version": "8.0.402",
   "status": "pass",
   "summary": "6 passed, 0 failed, 0 skipped (6 new tests in run)",
   "tests": [
    {
     "name": "GeneratedMessagePackFormatterTests.FormattedTypeMustNotBeAbstract",
     "outcome": "passed",
     "new": true
    },
    {
     "name": "GeneratedMessagePackFormatterTests.FormatterMustBePartial",
     "outcome": "passed",
     "new": true
    },
    {
     "name": "GeneratedMessagePackFormatterTests.FormatterMustImplementFormatterOfT",
     "outcome": "passed",
     "new": true
    },
    {
     "name": "GeneratedMessagePackFormatterTests.SurrogateKeysMustNotMixStringAndInt",
     "outcome": "passed",
     "new": true
    },
    {
     "name": "GeneratedMessagePackFormatterTests.SurrogateMemberMustHaveMatchingType",
     "outcome": "passed",
     "new": true
    },
    {
     "name": "GeneratedMessagePackFormatterTests.SurrogateMemberMustMatchFormattedType",
     "outcome": "passed",
     "new": true
    }
   ],
   "log": "evidence/2129/logs/tests_targeted.1.log",
   "duration_s": 3.0,
   "filter": [
    "FullyQualifiedName~GeneratedMessagePackFormatterTests."
   ],
   "project": "tests/MessagePack.SourceGenerator.Tests"
  },
  {
   "id": "tests.fail_without_fix",
   "tool": "dotnet test (source reverted, tests kept)",
   "tool_version": "8.0.402",
   "status": "pass",
   "summary": "new tests fail on base source: 6/6 failed -> tests do cover the change",
   "tests": [
    {
     "name": "GeneratedMessagePackFormatterTests.FormattedTypeMustNotBeAbstract",
     "outcome": "failed",
     "new": true,
     "error": "System.InvalidOperationException : Context: Source generator application\nContext: Verifying source generated files\nExpected source file list to match\n+MessagePack.SourceGenerator/MessagePack.SourceGenerator.MessagePackGenerator/MessagePack.GeneratedMessagePackResolver.g.cs\n"
    },
    {
     "name": "GeneratedMessagePackFormatterTests.FormatterMustBePartial",
     "outcome": "failed",
     "new": true,
     "error": "System.InvalidOperationException : Context: Source generator application\nContext: Verifying source generated files\nExpected source file list to match\n+MessagePack.SourceGenerator/MessagePack.SourceGenerator.MessagePackGenerator/MessagePack.GeneratedMessagePackResolver.g.cs\n"
    },
    {
     "name": "GeneratedMessagePackFormatterTests.FormatterMustImplementFormatterOfT",
     "outcome": "failed",
     "new": true,
     "error": "System.InvalidOperationException : Mismatch between number of diagnostics returned, expected \"1\" actual \"2\"\r\n\r\nDiagnostics:\r\n// /0/Test0.cs(3,2): error CS0246: The type or namespace name 'GeneratedMessagePackFormatter' could not be found (are you missing a using directive or an assembly reference?)\nDiagnosticResult.CompilerError(\"CS0246\").WithSpan(3, 2, 3, 31).WithArguments(\"GeneratedMessagePackFo [...]"
    },
    {
     "name": "GeneratedMessagePackFormatterTests.SurrogateKeysMustNotMixStringAndInt",
     "outcome": "failed",
     "new": true,
     "error": "System.InvalidOperationException : Context: Source generator application\nContext: Verifying source generated files\nExpected source file list to match\n+MessagePack.SourceGenerator/MessagePack.SourceGenerator.MessagePackGenerator/MessagePack.GeneratedMessagePackResolver.g.cs\n"
    },
    {
     "name": "GeneratedMessagePackFormatterTests.SurrogateMemberMustHaveMatchingType",
     "outcome": "failed",
     "new": true,
     "error": "System.InvalidOperationException : Context: Source generator application\nContext: Verifying source generated files\nExpected source file list to match\n+MessagePack.SourceGenerator/MessagePack.SourceGenerator.MessagePackGenerator/MessagePack.GeneratedMessagePackResolver.g.cs\n"
    },
    {
     "name": "GeneratedMessagePackFormatterTests.SurrogateMemberMustMatchFormattedType",
     "outcome": "failed",
     "new": true,
     "error": "System.InvalidOperationException : Context: Source generator application\nContext: Verifying source generated files\nExpected source file list to match\n+MessagePack.SourceGenerator/MessagePack.SourceGenerator.MessagePackGenerator/MessagePack.GeneratedMessagePackResolver.g.cs\n"
    }
   ],
   "log": "evidence/2129/logs/tests_fail_without_fix.1.log",
   "duration_s": 2.0,
   "reverted_files": [
    "all 13 files under src/ changed by the branch (2 added files deleted, 11 restored to base), including src/MessagePack.Annotations/Attributes.cs"
   ],
   "full_suite_with_source_reverted": {
    "total": 173,
    "failed": 6,
    "failed_tests": [
     "GeneratedMessagePackFormatterTests.FormattedTypeMustNotBeAbstract",
     "GeneratedMessagePackFormatterTests.FormatterMustBePartial",
     "GeneratedMessagePackFormatterTests.FormatterMustImplementFormatterOfT",
     "GeneratedMessagePackFormatterTests.SurrogateKeysMustNotMixStringAndInt",
     "GeneratedMessagePackFormatterTests.SurrogateMemberMustHaveMatchingType",
     "GeneratedMessagePackFormatterTests.SurrogateMemberMustMatchFormattedType"
    ],
    "log": "evidence/2129/logs/fail_without_fix.full_suite.log"
   },
   "new_failed": 6,
   "new_total": 6
  },
  {
   "id": "tests.full_suite",
   "tool": "dotnet test",
   "tool_version": "8.0.402",
   "status": "pass",
   "summary": "tests/MessagePack.SourceGenerator.Tests: 173 tests, 173 passed, 0 failed (0 not failing on base, 0 also failing on base)",
   "project": "tests/MessagePack.SourceGenerator.Tests",
   "total": 173,
   "passed": 173,
   "failed": 0,
   "failures_not_on_base": [],
   "failures_also_on_base": [],
   "log": "evidence/2129/logs/tests_full_suite.log",
   "duration_s": 5.0
  },
  {
   "id": "public_api",
   "tool": "git diff of PublicAPI.*.txt + scan of added public/protected declarations in src/",
   "status": "fail",
   "summary": "public API added: new public class MessagePack.GeneratedMessagePackFormatterAttribute (with public Type? SurrogateType) in src/MessagePack.Annotations/Attributes.cs; MessagePack.Annotations has no PublicAPI.*.txt tracking so PublicApiAnalyzers did not flag it. Also 4 new public DiagnosticDescriptors MsgPack019-022 (analyzer assembly) and 4 rows added to AnalyzerReleases.Unshipped.md",
   "publicapi_files_changed": [],
   "added_public_declarations": [
    "src/MessagePack.Annotations/Attributes.cs: public class GeneratedMessagePackFormatterAttribute : Attribute",
    "src/MessagePack.Annotations/Attributes.cs: public Type? SurrogateType { get; set; }",
    "src/MessagePack.SourceGenerator/Analyzers/MsgPack00xMessagePackAnalyzer.cs: public const string / public static readonly DiagnosticDescriptor for MsgPack019, MsgPack020, MsgPack021, MsgPack022",
    "src/MessagePack.SourceGenerator/CodeAnalysis/GeneratedFormatterRequest.cs: public sealed record GeneratedFormatterRequest",
    "src/MessagePack.SourceGenerator/CodeAnalysis/ObjectSerializationInfo.cs: public bool IsUserDeclaredFormatter"
   ],
   "untracked_projects": [
    "src/MessagePack.Annotations (no PublicAPI.Shipped.txt/Unshipped.txt)"
   ]
  },
  {
   "id": "analyzers",
   "tool": "dotnet build warnings (Roslyn analyzers, StyleCop, PublicApiAnalyzers) vs base",
   "status": "fail",
   "summary": "1 new warnings vs base",
   "new_warnings": [
    "tests/MessagePack.SourceGenerator.Tests/GeneratedMessagePackFormatterTests.cs: warning SA1203: Constant fields should appear before non-constant fields (https://github.com/DotNetAnalyzers/StyleCopAnalyzers/blob/master/documentation/SA1203.md) [tests/MessagePack.SourceGenerator.Tests/MessagePack.SourceGenerator.Tests.csproj]"
   ],
   "resolved_warnings": [],
   "base_warning_count": 1
  },
  {
   "id": "tests.targeted.execution",
   "tool": "dotnet build + dotnet test (ExecutionTests, MapModeExecutionTests)",
   "tool_version": "9.0.321",
   "tool_version_note": "SDK 9 used because the generator needs Roslyn 4.12; repo pins 8.0.402 (global.json overridden to 9.0.321 in the scratch worktree only)",
   "filter": "FullyQualifiedName~GeneratedFormatterForExternalTypesTests.",
   "projects": [
    "tests/MessagePack.SourceGenerator.ExecutionTests",
    "tests/MessagePack.SourceGenerator.MapModeExecutionTests"
   ],
   "status": "pass",
   "summary": "GeneratedFormatterForExternalTypesTests: 7 passed, 0 failed (7 new test results; runtime: generator runs inside csc, no CS9057); tests/MessagePack.SourceGenerator.MapModeExecutionTests: no tests match the filter (the test file is excluded from this project)",
   "tests": [
    {
     "name": "GeneratedFormatterForExternalTypesTests.ContractlessClassNullRoundTrips",
     "project": "tests/MessagePack.SourceGenerator.ExecutionTests",
     "outcome": "passed",
     "new": true
    },
    {
     "name": "GeneratedFormatterForExternalTypesTests.ContractlessClassRoundTrips",
     "project": "tests/MessagePack.SourceGenerator.ExecutionTests",
     "outcome": "passed",
     "new": true
    },
    {
     "name": "GeneratedFormatterForExternalTypesTests.ContractlessClassUsesStringKeysForPublicReadWriteMembers",
     "project": "tests/MessagePack.SourceGenerator.ExecutionTests",
     "outcome": "passed",
     "new": true
    },
    {
     "name": "GeneratedFormatterForExternalTypesTests.ContractlessStructRoundTrips",
     "project": "tests/MessagePack.SourceGenerator.ExecutionTests",
     "outcome": "passed",
     "new": true
    },
    {
     "name": "GeneratedFormatterForExternalTypesTests.GeneratedFormattersAreRegisteredInGeneratedResolver",
     "project": "tests/MessagePack.SourceGenerator.ExecutionTests",
     "outcome": "passed",
     "new": true
    },
    {
     "name": "GeneratedFormatterForExternalTypesTests.MessagePackObjectCanContainExternalTypes",
     "project": "tests/MessagePack.SourceGenerator.ExecutionTests",
     "outcome": "passed",
     "new": true
    },
    {
     "name": "GeneratedFormatterForExternalTypesTests.SurrogateControlsKeysAndMembership",
     "project": "tests/MessagePack.SourceGenerator.ExecutionTests",
     "outcome": "passed",
     "new": true
    }
   ],
   "cs9057": false,
   "log": [
    "evidence/2129/logs/execution.ExecutionTests.build.log",
    "evidence/2129/logs/execution.ExecutionTests.targeted.log",
    "evidence/2129/logs/execution.ExecutionTests.full.log",
    "evidence/2129/logs/execution.MapModeExecutionTests.build.log",
    "evidence/2129/logs/execution.MapModeExecutionTests.targeted.log",
    "evidence/2129/logs/execution.MapModeExecutionTests.full.log"
   ],
   "duration_s": 12.0,
   "on_base": "tests do not exist on base (new in this change): tests/MessagePack.SourceGenerator.ExecutionTests built=True, 0 matching tests, tests/MessagePack.SourceGenerator.MapModeExecutionTests built=True, 0 matching tests",
   "sdk8_attempt": {
    "tool_version": "8.0.402",
    "status": "error",
    "reason": "CS9057: generator references Microsoft.CodeAnalysis 4.12, SDK 8.0.402 ships Roslyn 4.11",
    "log": "evidence/2129/logs/execution_tests.sdk8.build.log"
   }
  },
  {
   "id": "tests.execution_fail_without_fix",
   "tool": "dotnet test (source reverted, tests kept) - ExecutionTests",
   "tool_version": "9.0.321",
   "tool_version_note": "SDK 9 used because the generator needs Roslyn 4.12; repo pins 8.0.402 (global.json overridden to 9.0.321 in the scratch worktree only)",
   "filter": "FullyQualifiedName~GeneratedFormatterForExternalTypesTests.",
   "projects": [
    "tests/MessagePack.SourceGenerator.ExecutionTests",
    "tests/MessagePack.SourceGenerator.MapModeExecutionTests"
   ],
   "tests": [],
   "log": [
    "evidence/2129/logs/execution_fail_without_fix.ExecutionTests.build.log",
    "evidence/2129/logs/execution_fail_without_fix.MapModeExecutionTests.build.log",
    "evidence/2129/logs/execution_fail_without_fix.MapModeExecutionTests.targeted.log",
    "evidence/2129/logs/execution_fail_without_fix.MapModeExecutionTests.full.log"
   ],
   "compile_failure": [
    {
     "project": "tests/MessagePack.SourceGenerator.ExecutionTests",
     "errors": [
      "tests/MessagePack.SourceGenerator.ExecutionTests/GeneratedFormatterForExternalTypes.cs(10,48): error CS0535: 'ExternalPersonFormatter' does not implement interface member 'IMessagePackFormatter<ExternalPerson>.Deserialize(ref MessagePackReader, MessagePackSerializerOptions)' ",
      "tests/MessagePack.SourceGenerator.ExecutionTests/GeneratedFormatterForExternalTypes.cs(10,48): error CS0535: 'ExternalPersonFormatter' does not implement interface member 'IMessagePackFormatter<ExternalPerson>.Serialize(ref MessagePackWriter, ExternalPerson, MessagePackSerializerOptions)' ",
      "tests/MessagePack.SourceGenerator.ExecutionTests/GeneratedFormatterForExternalTypes.cs(14,2): error CS0246: The type or namespace name 'GeneratedMessagePackFormatter' could not be found (are you missing a using directive or an assembly reference?) ",
      "tests/MessagePack.SourceGenerator.ExecutionTests/GeneratedFormatterForExternalTypes.cs(14,2): error CS0246: The type or namespace name 'GeneratedMessagePackFormatterAttribute' could not be found (are you missing a using directive or an assembly reference?) ",
      "tests/MessagePack.SourceGenerator.ExecutionTests/GeneratedFormatterForExternalTypes.cs(15,47): error CS0535: 'ExternalPointFormatter' does not implement interface member 'IMessagePackFormatter<ExternalPoint>.Deserialize(ref MessagePackReader, MessagePackSerializerOptions)' ",
      "tests/MessagePack.SourceGenerator.ExecutionTests/GeneratedFormatterForExternalTypes.cs(15,47): error CS0535: 'ExternalPointFormatter' does not implement interface member 'IMessagePackFormatter<ExternalPoint>.Serialize(ref MessagePackWriter, ExternalPoint, MessagePackSerializerOptions)' ",
      "tests/MessagePack.SourceGenerator.ExecutionTests/GeneratedFormatterForExternalTypes.cs(19,2): error CS0246: The type or namespace name 'GeneratedMessagePackFormatter' could not be found (are you missing a using directive or an assembly reference?) ",
      "tests/MessagePack.SourceGenerator.ExecutionTests/GeneratedFormatterForExternalTypes.cs(19,2): error CS0246: The type or namespace name 'GeneratedMessagePackFormatterAttribute' could not be found (are you missing a using directive or an assembly reference?) ",
      "tests/MessagePack.SourceGenerator.ExecutionTests/GeneratedFormatterForExternalTypes.cs(20,48): error CS0535: 'ExternalWidgetFormatter' does not implement interface member 'IMessagePackFormatter<ExternalWidget>.Deserialize(ref MessagePackReader, MessagePackSerializerOptions)' ",
      "tests/MessagePack.SourceGenerator.ExecutionTests/GeneratedFormatterForExternalTypes.cs(20,48): error CS0535: 'ExternalWidgetFormatter' does not implement interface member 'IMessagePackFormatter<ExternalWidget>.Serialize(ref MessagePackWriter, ExternalWidget, MessagePackSerializerOptions)' ",
      "tests/MessagePack.SourceGenerator.ExecutionTests/GeneratedFormatterForExternalTypes.cs(9,2): error CS0246: The type or namespace name 'GeneratedMessagePackFormatter' could not be found (are you missing a using directive or an assembly reference?) ",
      "tests/MessagePack.SourceGenerator.ExecutionTests/GeneratedFormatterForExternalTypes.cs(9,2): error CS0246: The type or namespace name 'GeneratedMessagePackFormatterAttribute' could not be found (are you missing a using directive or an assembly reference?) "
     ]
    }
   ],
   "tests_not_compiled": [
    "GeneratedFormatterForExternalTypesTests.ContractlessClassNullRoundTrips",
    "GeneratedFormatterForExternalTypesTests.ContractlessClassRoundTrips",
    "GeneratedFormatterForExternalTypesTests.ContractlessClassUsesStringKeysForPublicReadWriteMembers",
    "GeneratedFormatterForExternalTypesTests.ContractlessStructRoundTrips",
    "GeneratedFormatterForExternalTypesTests.GeneratedFormattersAreRegisteredInGeneratedResolver",
    "GeneratedFormatterForExternalTypesTests.MessagePackObjectCanContainExternalTypes",
    "GeneratedFormatterForExternalTypesTests.SurrogateControlsKeysAndMembership"
   ],
   "status": "pass",
   "summary": "new runtime tests do not compile with the source reverted (tests/MessagePack.SourceGenerator.ExecutionTests): 7 tests cannot exist without the fix; errors are the missing feature itself (see compile_failure) -> tests depend on the change",
   "caveat": "compile-time, not a runtime comparison: the tests cannot be built, so no serialization behaviour was compared. Read compile_failure to see which part of the reverted source each error comes from (e.g. CS0246 = an attribute/type from the change is missing; CS0535 = the generator emitted no members for a partial formatter).",
   "new_failed": 0,
   "new_total": 0
  },
  {
   "id": "tests.execution_full_suite",
   "tool": "dotnet test (whole ExecutionTests, MapModeExecutionTests) vs base",
   "tool_version": "9.0.321",
   "tool_version_note": "SDK 9 used because the generator needs Roslyn 4.12; repo pins 8.0.402 (global.json overridden to 9.0.321 in the scratch worktree only)",
   "status": "pass",
   "summary": "tests/MessagePack.SourceGenerator.ExecutionTests: 21/21 passed (base 14/14), 0 failures not on base; tests/MessagePack.SourceGenerator.MapModeExecutionTests: 20/20 passed (base 20/20), 0 failures not on base",
   "projects": [
    {
     "project": "tests/MessagePack.SourceGenerator.ExecutionTests",
     "total": 21,
     "passed": 21,
     "failed": 0,
     "failures_not_on_base": [],
     "base_total": 14,
     "base_passed": 14,
     "tests_added_vs_base": [
      "GeneratedFormatterForExternalTypesTests.ContractlessClassNullRoundTrips",
      "GeneratedFormatterForExternalTypesTests.ContractlessClassRoundTrips",
      "GeneratedFormatterForExternalTypesTests.ContractlessClassUsesStringKeysForPublicReadWriteMembers",
      "GeneratedFormatterForExternalTypesTests.ContractlessStructRoundTrips",
      "GeneratedFormatterForExternalTypesTests.GeneratedFormattersAreRegisteredInGeneratedResolver",
      "GeneratedFormatterForExternalTypesTests.MessagePackObjectCanContainExternalTypes",
      "GeneratedFormatterForExternalTypesTests.SurrogateControlsKeysAndMembership"
     ],
     "tests_missing_vs_base": [],
     "new_build_warnings_vs_base": [
      "tests/MessagePack.SourceGenerator.ExecutionTests/GeneratedFormatterForExternalTypes.cs: warning CS8618: Non-nullable property 'Person' must contain a non-null value when exiting constructor. Consider adding the 'required' modifier or declaring the property as nullable.",
      "tests/MessagePack.SourceGenerator.ExecutionTests/GeneratedFormatterForExternalTypes.cs: warning CS8618: Non-nullable property 'Widget' must contain a non-null value when exiting constructor. Consider adding the 'required' modifier or declaring the property as nullable."
     ]
    },
    {
     "project": "tests/MessagePack.SourceGenerator.MapModeExecutionTests",
     "total": 20,
     "passed": 20,
     "failed": 0,
     "failures_not_on_base": [],
     "base_total": 20,
     "base_passed": 20,
     "tests_added_vs_base": [],
     "tests_missing_vs_base": [],
     "new_build_warnings_vs_base": []
    }
   ],
   "log": [
    "evidence/2129/logs/execution.ExecutionTests.full.log",
    "evidence/2129/logs/execution.MapModeExecutionTests.full.log"
   ],
   "duration_s": 0.0
  },
  {
   "id": "solution_membership",
   "tool": "grep MessagePack.sln",
   "status": "fail",
   "summary": "new project tests/MessagePack.SourceGenerator.ExternalTypes/MessagePack.SourceGenerator.ExternalTypes.csproj is not added to MessagePack.sln (only referenced from ExecutionTests.csproj)"
  }
 ],
 "not_run": [
  {
   "id": "tests.MessagePack.Tests",
   "reason": "runtime library src/MessagePack not modified by the change; suite not run"
  },
  {
   "id": "build.net472/netstandard",
   "reason": "only the net8.0 slice of src/MessagePack was built (Linux container, Debug)"
  },
  {
   "id": "benchmarks",
   "reason": "no runtime serialization hot path touched (generator/analyzer only)"
  }
 ],
 "environment": {
  "sdk": "8.0.402",
  "sdk_execution_tests": "9.0.321",
  "sdk_note": "SDK 9 used because the generator needs Roslyn 4.12; repo pins 8.0.402 (global.json overridden to 9.0.321 in the scratch worktree only)",
  "os": "linux-x64 (container)",
  "configuration": "Debug",
  "max_cpu": 8
 }
}
```

## Files changed (28: 26 non-generated, 2 generated)
- README.md (+52 -0, doc)
- doc/analyzers/MsgPack019.md (+26 -0, doc)
- doc/analyzers/MsgPack020.md (+23 -0, doc)
- doc/analyzers/MsgPack021.md (+23 -0, doc)
- doc/analyzers/MsgPack022.md (+31 -0, doc)
- doc/analyzers/index.md (+4 -0, doc)
- src/MessagePack.Annotations/Attributes.cs (+36 -0, source)
- src/MessagePack.SourceGenerator/AnalyzerReleases.Unshipped.md (+4 -0, build)
- src/MessagePack.SourceGenerator/Analyzers/MsgPack00xMessagePackAnalyzer.cs (+45 -1, source)
- src/MessagePack.SourceGenerator/CodeAnalysis/GeneratedFormatterCollector.cs (+300 -0, source)
- src/MessagePack.SourceGenerator/CodeAnalysis/GeneratedFormatterRequest.cs (+13 -0, source)
- src/MessagePack.SourceGenerator/CodeAnalysis/ObjectSerializationInfo.cs (+7 -0, source)
- src/MessagePack.SourceGenerator/GeneratorUtilities.cs (+3 -0, source)
- src/MessagePack.SourceGenerator/MessagePackGenerator.cs (+36 -3, source)
- src/MessagePack.SourceGenerator/Transforms/FormatterTemplate.tt (+1 -1, source)
- src/MessagePack.SourceGenerator/Transforms/StringKey/StringKeyFormatterTemplate.tt (+1 -1, source)
- src/MessagePack.SourceGenerator/Utils/Constants.cs (+2 -0, source)
- tests/MessagePack.SourceGenerator.ExecutionTests/GeneratedFormatterForExternalTypes.cs (+50 -0, test)
- tests/MessagePack.SourceGenerator.ExecutionTests/GeneratedFormatterForExternalTypesTests.cs (+95 -0, test)
- tests/MessagePack.SourceGenerator.ExecutionTests/MessagePack.SourceGenerator.ExecutionTests.csproj (+5 -0, build)
- tests/MessagePack.SourceGenerator.ExternalTypes/ExternalPerson.cs (+15 -0, test)
- tests/MessagePack.SourceGenerator.ExternalTypes/ExternalPoint.cs (+12 -0, test)
- tests/MessagePack.SourceGenerator.ExternalTypes/ExternalWidget.cs (+15 -0, test)
- tests/MessagePack.SourceGenerator.ExternalTypes/MessagePack.SourceGenerator.ExternalTypes.csproj (+17 -0, build)
- tests/MessagePack.SourceGenerator.MapModeExecutionTests/MessagePack.SourceGenerator.MapModeExecutionTests.csproj (+2 -1, build)
- tests/MessagePack.SourceGenerator.Tests/GeneratedMessagePackFormatterTests.cs (+210 -0, test)

Generated files (2; contents and diffs NOT provided):
- src/MessagePack.SourceGenerator/Transforms/FormatterTemplate.cs (+3 -1)
- src/MessagePack.SourceGenerator/Transforms/StringKey/StringKeyFormatterTemplate.cs (+3 -1)

## Diff (non-generated files)
```diff
diff --git a/README.md b/README.md
index c52f1088..89dffba9 100644
--- a/README.md
+++ b/README.md
@@ -1636,6 +1636,58 @@ Two assembly-level attributes exist to help with mixing in your own custom forma
 
 Learn more about using a mix of your own custom formatters and automatically generated ones in [the Analyzer section](#analyzer).
 
+### Formatters for types from other assemblies
+
+A type that comes from an assembly you cannot change, such as a dependency-free library, may have no MessagePack attributes at all.
+You can still get a source-generated formatter for it by declaring a `partial` formatter class in your own project and marking it with `[GeneratedMessagePackFormatter]`:
+
+```cs
+// ProjectA.MyObject lives in a library that does not reference MessagePack.
+[GeneratedMessagePackFormatter]
+public partial class MyObjectFormatter : IMessagePackFormatter<ProjectA.MyObject>
+{
+}
+```
+
+The source generator writes the body of `MyObjectFormatter`, and the generated `GeneratedMessagePackResolver` registers it automatically.
+Nothing needs to be added to `ProjectA`.
+
+By default the formatter serializes the type in *contractless* mode: every public, read-write instance property and field is serialized under its name as a string key.
+Read-only members are skipped because they cannot be deserialized.
+
+To control keys and membership without touching the type, name a *surrogate* type in the attribute.
+The surrogate's `[Key]` and `[IgnoreMember]` attributes describe the wire contract, and its members are matched to members of the formatted type by name and type.
+The surrogate is only read at compile time and is never instantiated.
+
+```cs
+public class MyObjectSurrogate
+{
+    [Key(0)]
+    public int Id { get; set; }
+
+    [Key(1)]
+    public string Label { get; set; }
+
+    [IgnoreMember]
+    public string Secret { get; set; }
+}
+
+[GeneratedMessagePackFormatter(SurrogateType = typeof(MyObjectSurrogate))]
+public partial class MyObjectFormatter : IMessagePackFormatter<ProjectA.MyObject>
+{
+}
+```
+
+When a surrogate is used, only the members it lists are serialized.
+All of its keys must be integers or all must be strings.
+
+Limitations of this feature:
+- Only classes and structs are supported. Generic types, abstract types, and unions from other assemblies are not.
+- Deserialization uses an accessible parameterless constructor (any struct can be created without one). Constructor parameters are not matched, so types that only have a parameterized constructor are not supported yet.
+- Nested member types are not generated from the formatter. They are resolved through the other resolvers in your composite resolver, as usual.
+- Formatter diagnostics are reported as `MsgPack019` through `MsgPack022`, listed in the [analyzers](doc/analyzers/index.md).
+
+
 ### MagicOnion
 
 [MagicOnion](https://github.com/Cysharp/MagicOnion) is a code-first gRPC framework based on grpc-dotnet and MessagePack. gRPC usually communicates with Protocol Buffers using IDL. But MagicOnion uses MessagePack for C# and does not need IDL. When communicating C# to C#, schemaless (or rather C# classes as schema) is better than using IDL.

diff --git a/doc/analyzers/MsgPack019.md b/doc/analyzers/MsgPack019.md
new file mode 100644
index 00000000..7ce39cef
--- /dev/null
+++ b/doc/analyzers/MsgPack019.md
@@ -0,0 +1,26 @@
+# MsgPack019 Generated formatter must be partial
+
+A class marked with `[GeneratedMessagePackFormatter]` is the target of source generation. The generator writes the body of the formatter into the class, so the class must be declared `partial`.
+
+## Examples of patterns that are flagged by this analyzer
+
+```cs
+[GeneratedMessagePackFormatter]
+public class MyObjectFormatter : IMessagePackFormatter<ProjectA.MyObject> // Diagnostic reported here: not partial
+{
+    // ...
+}
+```
+
+## Typical fix
+
+Declare the class `partial` and leave its body empty:
+
+```cs
+[GeneratedMessagePackFormatter]
+public partial class MyObjectFormatter : IMessagePackFormatter<ProjectA.MyObject>
+{
+}
+```
+
+Any nesting types that contain the formatter must also be declared `partial`.

diff --git a/doc/analyzers/MsgPack020.md b/doc/analyzers/MsgPack020.md
new file mode 100644
index 00000000..b30062a8
--- /dev/null
+++ b/doc/analyzers/MsgPack020.md
@@ -0,0 +1,23 @@
+# MsgPack020 Generated formatter must implement IMessagePackFormatter<T>
+
+A class marked with `[GeneratedMessagePackFormatter]` identifies the data type to serialize by its `IMessagePackFormatter<T>` interface. The class must implement exactly one such interface.
+
+## Examples of patterns that are flagged by this analyzer
+
+```cs
+[GeneratedMessagePackFormatter]
+public partial class MyObjectFormatter // Diagnostic reported here: no IMessagePackFormatter<T>
+{
+}
+```
+
+## Typical fix
+
+Implement `IMessagePackFormatter<T>` for the type to be serialized:
+
+```cs
+[GeneratedMessagePackFormatter]
+public partial class MyObjectFormatter : IMessagePackFormatter<ProjectA.MyObject>
+{
+}
+```

diff --git a/doc/analyzers/MsgPack021.md b/doc/analyzers/MsgPack021.md
new file mode 100644
index 00000000..1117c328
--- /dev/null
+++ b/doc/analyzers/MsgPack021.md
@@ -0,0 +1,23 @@
+# MsgPack021 Generated formatter data type not supported
+
+The source generator writes formatters for non-generic, non-abstract classes and structs that the formatter can access. The data type named by the formatter's `IMessagePackFormatter<T>` interface must meet these requirements.
+
+## Examples of patterns that are flagged by this analyzer
+
+```cs
+public abstract class MyBase { }
+
+[GeneratedMessagePackFormatter]
+public partial class MyBaseFormatter : IMessagePackFormatter<MyBase> // Diagnostic reported here: abstract
+{
+}
+
+[GeneratedMessagePackFormatter]
+public partial class ListFormatter : IMessagePackFormatter<List<int>> // Diagnostic reported here: generic
+{
+}
+```
+
+## Typical fix
+
+Use a concrete, non-generic class or struct as the data type. For an abstract base type, use [`[Union]`](../../README.md#union) with the derived types instead.

diff --git a/doc/analyzers/MsgPack022.md b/doc/analyzers/MsgPack022.md
new file mode 100644
index 00000000..04142297
--- /dev/null
+++ b/doc/analyzers/MsgPack022.md
@@ -0,0 +1,31 @@
+# MsgPack022 Surrogate member does not match the formatted type
+
+When `[GeneratedMessagePackFormatter(SurrogateType = typeof(...))]` is used, each keyed member of the surrogate must match a public, read-write instance member of the formatted type, with the same name and type.
+
+## Examples of patterns that are flagged by this analyzer
+
+```cs
+// ProjectA.MyObject has `public int Id { get; set; }` and no `Missing` member.
+public class MyObjectSurrogate
+{
+    [Key(0)]
+    public int Missing { get; set; } // Diagnostic reported here
+}
+
+[GeneratedMessagePackFormatter(SurrogateType = typeof(MyObjectSurrogate))]
+public partial class MyObjectFormatter : IMessagePackFormatter<ProjectA.MyObject>
+{
+}
+```
+
+## Typical fix
+
+Rename the surrogate member to match a public, read-write member of the formatted type, and make sure the types are identical:
+
+```cs
+public class MyObjectSurrogate
+{
+    [Key(0)]
+    public int Id { get; set; }
+}
+```

diff --git a/doc/analyzers/index.md b/doc/analyzers/index.md
index 38365b68..cb34ebc0 100644
--- a/doc/analyzers/index.md
+++ b/doc/analyzers/index.md
@@ -23,5 +23,9 @@ ID | Title
 [MsgPack016](MsgPack016.md) | KeyAttribute-derived attributes are not supported by AOT formatters
 [MsgPack017](MsgPack017.md) | Property with init accessor and initializer
 [MsgPack018](MsgPack018.md) | Unique names required in force map mode
+[MsgPack019](MsgPack019.md) | Generated formatter must be partial
+[MsgPack020](MsgPack020.md) | Generated formatter must implement `IMessagePackFormatter<T>`
+[MsgPack021](MsgPack021.md) | Generated formatter data type not supported
+[MsgPack022](MsgPack022.md) | Surrogate member does not match the formatted type
 
 [1]: https://nuget.org/packages/MessagePackAnalyzer

diff --git a/src/MessagePack.Annotations/Attributes.cs b/src/MessagePack.Annotations/Attributes.cs
index 13e3346f..e15a6f91 100644
--- a/src/MessagePack.Annotations/Attributes.cs
+++ b/src/MessagePack.Annotations/Attributes.cs
@@ -139,4 +139,40 @@ namespace MessagePack
             this.Arguments = arguments;
         }
     }
+
+    /// <summary>
+    /// Marks a <see langword="partial"/> class that implements <c>IMessagePackFormatter&lt;T&gt;</c> so that the MessagePack source generator
+    /// writes the formatter implementation for <c>T</c>, even when <c>T</c> is declared in another assembly that cannot reference MessagePack.
+    /// </summary>
+    /// <remarks>
+    /// <para>
+    /// The formatted type <c>T</c> is serialized in contractless mode: every public, non-static, read-write instance property and field
+    /// is serialized using its name as a string key. No attributes are required on <c>T</c>.
+    /// </para>
+    /// <para>
+    /// To control keys and membership without touching <c>T</c>, set <see cref="SurrogateType"/> to a type whose
+    /// <see cref="KeyAttribute"/> and <see cref="IgnoreMemberAttribute"/> annotations describe the wire contract.
+    /// The surrogate is only read at compile time and is never instantiated at run time.
+    /// Surrogate members are matched to members of <c>T</c> by name.
+    /// </para>
+    /// </remarks>
+    /// <example>
+    /// <code>
+    /// [GeneratedMessagePackFormatter]
+    /// public partial class MyObjectFormatter : IMessagePackFormatter&lt;ProjectA.MyObject&gt; { }
+    /// </code>
+    /// </example>
+    [AttributeUsage(AttributeTargets.Class, AllowMultiple = false, Inherited = false)]
+    public class GeneratedMessagePackFormatterAttribute : Attribute
+    {
+        /// <summary>
+        /// Gets or sets a type whose <see cref="KeyAttribute"/> members define the keys and membership of the formatted type.
+        /// </summary>
+        /// <remarks>
+        /// Each surrogate member that carries a <see cref="KeyAttribute"/> must match a public, read-write instance member of the formatted type by name.
+        /// Surrogate members that carry <see cref="IgnoreMemberAttribute"/> are excluded.
+        /// All keys in the surrogate must be the same kind (all integer or all string).
+        /// </remarks>
+        public Type? SurrogateType { get; set; }
+    }
 }

diff --git a/src/MessagePack.SourceGenerator/AnalyzerReleases.Unshipped.md b/src/MessagePack.SourceGenerator/AnalyzerReleases.Unshipped.md
index 5ef8f75e..4fc075ce 100644
--- a/src/MessagePack.SourceGenerator/AnalyzerReleases.Unshipped.md
+++ b/src/MessagePack.SourceGenerator/AnalyzerReleases.Unshipped.md
@@ -23,3 +23,7 @@ MsgPack015 | Usage | Warning | MessagePackObjectAttribute.AllowPrivate should be
 MsgPack016 | Usage | Error | KeyAttribute-derived attributes are not supported by AOT formatters
 MsgPack017 | Usage | Warning | Property with init accessor and initializer
 MsgPack018 | Usage | Error | Unique names required in force map mode
+MsgPack019 | Usage | Error | Generated formatter must be partial
+MsgPack020 | Usage | Error | Generated formatter must implement IMessagePackFormatter<T>
+MsgPack021 | Usage | Error | Generated formatter data type not supported
+MsgPack022 | Usage | Error | Surrogate member does not match the formatted type

diff --git a/src/MessagePack.SourceGenerator/Analyzers/MsgPack00xMessagePackAnalyzer.cs b/src/MessagePack.SourceGenerator/Analyzers/MsgPack00xMessagePackAnalyzer.cs
index 7ab75357..dab046e6 100644
--- a/src/MessagePack.SourceGenerator/Analyzers/MsgPack00xMessagePackAnalyzer.cs
+++ b/src/MessagePack.SourceGenerator/Analyzers/MsgPack00xMessagePackAnalyzer.cs
@@ -29,6 +29,10 @@ public class MsgPack00xMessagePackAnalyzer : DiagnosticAnalyzer
     public const string AOTDerivedKeyId = "MsgPack016";
     public const string AOTInitPropertyId = "MsgPack017";
     public const string CollidingMemberNamesInForceMapModeId = "MsgPack018";
+    public const string GeneratedFormatterMustBePartialId = "MsgPack019";
+    public const string GeneratedFormatterMustImplementFormatterId = "MsgPack020";
+    public const string GeneratedFormatterDataTypeNotSupportedId = "MsgPack021";
+    public const string SurrogateMemberNotFoundId = "MsgPack022";
 
     internal const string Category = "Usage";
 
@@ -311,6 +315,42 @@ public class MsgPack00xMessagePackAnalyzer : DiagnosticAnalyzer
         isEnabledByDefault: true,
         helpLinkUri: AnalyzerUtilities.GetHelpLink(CollidingMemberNamesInForceMapModeId));
 
+    public static readonly DiagnosticDescriptor GeneratedFormatterMustBePartial = new(
+        id: GeneratedFormatterMustBePartialId,
+        title: "Generated formatter must be partial",
+        category: Category,
+        messageFormat: "The formatter '{0}' is marked with [GeneratedMessagePackFormatter] and must be declared 'partial' so the source generator can write its implementation",
+        defaultSeverity: DiagnosticSeverity.Error,
+        isEnabledByDefault: true,
+        helpLinkUri: AnalyzerUtilities.GetHelpLink(GeneratedFormatterMustBePartialId));
+
+    public static readonly DiagnosticDescriptor GeneratedFormatterMustImplementFormatter = new(
+        id: GeneratedFormatterMustImplementFormatterId,
+        title: "Generated formatter must implement IMessagePackFormatter<T>",
+        category: Category,
+        messageFormat: "The formatter '{0}' is marked with [GeneratedMessagePackFormatter] but does not implement IMessagePackFormatter<T> for exactly one data type",
+        defaultSeverity: DiagnosticSeverity.Error,
+        isEnabledByDefault: true,
+        helpLinkUri: AnalyzerUtilities.GetHelpLink(GeneratedFormatterMustImplementFormatterId));
+
+    public static readonly DiagnosticDescriptor GeneratedFormatterDataTypeNotSupported = new(
+        id: GeneratedFormatterDataTypeNotSupportedId,
+        title: "Generated formatter data type not supported",
+        category: Category,
+        messageFormat: "The formatter '{0}' cannot generate a formatter for '{1}': only accessible, non-generic, non-abstract classes and structs are supported",
+        defaultSeverity: DiagnosticSeverity.Error,
+        isEnabledByDefault: true,
+        helpLinkUri: AnalyzerUtilities.GetHelpLink(GeneratedFormatterDataTypeNotSupportedId));
+
+    public static readonly DiagnosticDescriptor SurrogateMemberNotFound = new(
+        id: SurrogateMemberNotFoundId,
+        title: "Surrogate member does not match the formatted type",
+        category: Category,
+        messageFormat: "The surrogate member '{0}' has no matching public, read-write instance member with the same name and type on '{1}'",
+        defaultSeverity: DiagnosticSeverity.Error,
+        isEnabledByDefault: true,
+        helpLinkUri: AnalyzerUtilities.GetHelpLink(SurrogateMemberNotFoundId));
+
     public override ImmutableArray<DiagnosticDescriptor> SupportedDiagnostics { get; } = ImmutableArray.Create(
         TypeMustBeMessagePackObject,
         MessageFormatterMustBeMessagePackFormatter,
@@ -338,7 +378,11 @@ public class MsgPack00xMessagePackAnalyzer : DiagnosticAnalyzer
         InaccessibleDataType,
         NullableReferenceTypeFormatter,
         MessagePackObjectAllowPrivateRequired,
-        CollidingMemberNamesInForceMapMode);
+        CollidingMemberNamesInForceMapMode,
+        GeneratedFormatterMustBePartial,
+        GeneratedFormatterMustImplementFormatter,
+        GeneratedFormatterDataTypeNotSupported,
+        SurrogateMemberNotFound);
 
     public override void Initialize(AnalysisContext context)
     {

diff --git a/src/MessagePack.SourceGenerator/CodeAnalysis/GeneratedFormatterCollector.cs b/src/MessagePack.SourceGenerator/CodeAnalysis/GeneratedFormatterCollector.cs
new file mode 100644
index 00000000..1d95afc5
--- /dev/null
+++ b/src/MessagePack.SourceGenerator/CodeAnalysis/GeneratedFormatterCollector.cs
@@ -0,0 +1,300 @@
+// Copyright (c) All contributors. All rights reserved.
+// Licensed under the MIT license. See LICENSE file in the project root for full license information.
+
+using System.Collections.Immutable;
+using MessagePack.SourceGenerator.Analyzers;
+using Microsoft.CodeAnalysis;
+using Microsoft.CodeAnalysis.CSharp;
+using Microsoft.CodeAnalysis.CSharp.Syntax;
+
+namespace MessagePack.SourceGenerator.CodeAnalysis;
+
+/// <summary>
+/// Builds the serialization model for a partial formatter marked with <c>[GeneratedMessagePackFormatter]</c>.
+/// The formatted type may come from an assembly that carries no MessagePack attributes, so its members are read
+/// in contractless mode, or through the keys declared on an optional surrogate type.
+/// </summary>
+internal static class GeneratedFormatterCollector
+{
+    private static readonly SymbolDisplayFormat BinaryWriteTypeFormat = new(
+        genericsOptions: SymbolDisplayGenericsOptions.IncludeTypeParameters,
+        miscellaneousOptions: SymbolDisplayMiscellaneousOptions.ExpandNullable,
+        typeQualificationStyle: SymbolDisplayTypeQualificationStyle.NameOnly);
+
+    /// <summary>
+    /// Creates the model for one generated formatter.
+    /// </summary>
+    /// <param name="compilation">The compilation that contains the formatter.</param>
+    /// <param name="options">The analyzer options for the compilation.</param>
+    /// <param name="referenceSymbols">The MessagePack reference symbols.</param>
+    /// <param name="reportDiagnostic">Receives diagnostics about the formatter. May be <see langword="null"/>.</param>
+    /// <param name="formatter">The user-declared partial formatter class.</param>
+    /// <param name="surrogate">The surrogate type, or <see langword="null"/> for contractless mode.</param>
+    /// <param name="cancellationToken">A cancellation token.</param>
+    /// <returns>The model, or <see langword="null"/> if the formatter cannot be generated.</returns>
+    internal static FullModel? Collect(
+        Compilation compilation,
+        AnalyzerOptions options,
+        ReferenceSymbols referenceSymbols,
+        Action<Diagnostic>? reportDiagnostic,
+        INamedTypeSymbol formatter,
+        INamedTypeSymbol? surrogate,
+        CancellationToken cancellationToken)
+    {
+        Location location = formatter.Locations.FirstOrDefault() ?? Location.None;
+        string formatterName = formatter.ToDisplayString(SymbolDisplayFormat.FullyQualifiedFormat);
+
+        if (!IsPartial(formatter, cancellationToken))
+        {
+            reportDiagnostic?.Invoke(Diagnostic.Create(MsgPack00xMessagePackAnalyzer.GeneratedFormatterMustBePartial, location, formatterName));
+            return null;
+        }
+
+        INamedTypeSymbol? openFormatterInterface = compilation.GetTypeByMetadataName($"{Constants.IMessagePackFormatterInterfaceNamespace}.{Constants.IMessagePackFormatterInterfaceName}`1");
+        ImmutableArray<INamedTypeSymbol> formatterInterfaces = formatter.AllInterfaces
+            .Where(i => i.IsGenericType && SymbolEqualityComparer.Default.Equals(i.OriginalDefinition, openFormatterInterface))
+            .ToImmutableArray();
+        if (formatterInterfaces.Length != 1)
+        {
+            reportDiagnostic?.Invoke(Diagnostic.Create(MsgPack00xMessagePackAnalyzer.GeneratedFormatterMustImplementFormatter, location, formatterName));
+            return null;
+        }
+
+        ITypeSymbol dataTypeSymbol = formatterInterfaces[0].TypeArguments[0];
+        if (dataTypeSymbol is not INamedTypeSymbol { IsGenericType: false, IsAbstract: false } type
+            || type.TypeKind is not (TypeKind.Class or TypeKind.Struct)
+            || !compilation.IsSymbolAccessibleWithin(type, formatter))
+        {
+            reportDiagnostic?.Invoke(Diagnostic.Create(
+                MsgPack00xMessagePackAnalyzer.GeneratedFormatterDataTypeNotSupported,
+                location,
+                formatterName,
+                dataTypeSymbol.ToDisplayString(SymbolDisplayFormat.FullyQualifiedFormat)));
+            return null;
+        }
+
+        bool isClass = type.TypeKind == TypeKind.Class;
+        if (isClass && !type.InstanceConstructors.Any(c => c.Parameters.Length == 0 && compilation.IsSymbolAccessibleWithin(c, formatter)))
+        {
+            reportDiagnostic?.Invoke(Diagnostic.Create(MsgPack00xMessagePackAnalyzer.NoDeserializingConstructor, location));
+            return null;
+        }
+
+        bool hasCallbackReceiver = type.AllInterfaces.Any(i => SymbolEqualityComparer.Default.Equals(i, referenceSymbols.IMessagePackSerializationCallbackReceiver));
+        bool needsCast = hasCallbackReceiver && type.GetMembers().OfType<IMethodSymbol>().Any(m =>
+            m.ExplicitInterfaceImplementations.Length > 0 && (m.Name == "OnBeforeSerialize" || m.Name == "OnAfterDeserialize"));
+
+        IReadOnlyList<MemberSerializationInfo>? members;
+        bool isIntKey;
+        if (surrogate is null)
+        {
+            members = CreateContractlessMembers(type);
+            isIntKey = false;
+        }
+        else
+        {
+            members = CreateSurrogateMembers(type, surrogate, referenceSymbols, reportDiagnostic, location, out isIntKey);
+        }
+
+        if (members is null)
+        {
+            return null;
+        }
+
+        ObjectSerializationInfo info = ObjectSerializationInfo.Create(
+            type,
+            isClass: isClass,
+            nestedFormatterRequired: false,
+            genericTypeParameters: Array.Empty<GenericTypeParameterInfo>(),
+            constructorParameters: Array.Empty<MemberSerializationInfo>(),
+            isIntKey: isIntKey,
+            members: members.ToArray(),
+            hasIMessagePackSerializationCallbackReceiver: hasCallbackReceiver,
+            needsCastOnAfter: needsCast,
+            needsCastOnBefore: needsCast,
+            resolverOptions: options.Generator.Resolver) with
+        {
+            Formatter = new QualifiedNamedTypeName(formatter),
+            IsUserDeclaredFormatter = true,
+        };
+
+        return FullModel.Empty with
+        {
+            ObjectInfos = ImmutableSortedSet.Create(info),
+            Options = options,
+        };
+    }
+
+    /// <summary>
+    /// Contractless mode: every public, read-write instance property and field is serialized under its name as a string key.
+    /// </summary>
+    private static IReadOnlyList<MemberSerializationInfo> CreateContractlessMembers(INamedTypeSymbol type)
+    {
+        List<ISymbol> targets = GetInstanceMembers(type).Where(IsPublicReadWrite).OrderBy(m => m.Name, StringComparer.Ordinal).ToList();
+        List<MemberSerializationInfo> members = new(targets.Count);
+        for (int i = 0; i < targets.Count; i++)
+        {
+            members.Add(CreateMember(targets[i], intKey: i, stringKey: targets[i].Name));
+        }
+
+        return members;
+    }
+
+    /// <summary>
+    /// Surrogate mode: keys and membership come from the surrogate's <c>[Key]</c> and <c>[IgnoreMember]</c> annotations.
+    /// Each keyed surrogate member is matched by name, and type, to a public read-write member of the formatted type.
+    /// </summary>
+    private static IReadOnlyList<MemberSerializationInfo>? CreateSurrogateMembers(
+        INamedTypeSymbol type,
+        INamedTypeSymbol surrogate,
+        ReferenceSymbols referenceSymbols,
+        Action<Diagnostic>? reportDiagnostic,
+        Location location,
+        out bool isIntKey)
+    {
+        isIntKey = false;
+        bool? keyKindIsInt = null;
+        HashSet<object> claimedKeys = new();
+        List<MemberSerializationInfo> members = new();
+        List<ISymbol> targetMembers = GetInstanceMembers(type);
+
+        foreach (ISymbol surrogateMember in GetInstanceMembers(surrogate))
+        {
+            ImmutableArray<AttributeData> attributes = surrogateMember.GetAttributes();
+            if (attributes.Any(a => SymbolEqualityComparer.Default.Equals(a.AttributeClass, referenceSymbols.IgnoreAttribute)))
+            {
+                continue;
+            }
+
+            AttributeData? keyAttribute = attributes.FirstOrDefault(a => SymbolEqualityComparer.Default.Equals(a.AttributeClass, referenceSymbols.KeyAttribute));
+            object? key = keyAttribute is { ConstructorArguments.Length: 1 } ? keyAttribute.ConstructorArguments[0].Value : null;
+            if (key is not (int or string))
+            {
+                reportDiagnostic?.Invoke(Diagnostic.Create(
+                    MsgPack00xMessagePackAnalyzer.MemberNeedsKey,
+                    surrogateMember.Locations.FirstOrDefault() ?? location,
+                    surrogate.Name,
+                    surrogateMember.Name));
+                return null;
+            }
+
+            bool memberIsIntKey = key is int;
+            keyKindIsInt ??= memberIsIntKey;
+            if (keyKindIsInt != memberIsIntKey)
+            {
+                reportDiagnostic?.Invoke(Diagnostic.Create(MsgPack00xMessagePackAnalyzer.DoNotMixStringAndIntKeys, surrogateMember.Locations.FirstOrDefault() ?? location));
+                return null;
+            }
+
+            ISymbol? target = targetMembers.FirstOrDefault(m => m.Name == surrogateMember.Name);
+            if (target is null || !IsPublicReadWrite(target) || !SymbolEqualityComparer.Default.Equals(GetMemberType(target), GetMemberType(surrogateMember)))
+            {
+                reportDiagnostic?.Invoke(Diagnostic.Create(
+                    MsgPack00xMessagePackAnalyzer.SurrogateMemberNotFound,
+                    surrogateMember.Locations.FirstOrDefault() ?? location,
+                    surrogateMember.Name,
+                    type.ToDisplayString(SymbolDisplayFormat.FullyQualifiedFormat)));
+                return null;
+            }
+
+            if (!claimedKeys.Add(key))
+            {
+                reportDiagnostic?.Invoke(Diagnostic.Create(MsgPack00xMessagePackAnalyzer.KeysMustBeUnique, surrogateMember.Locations.FirstOrDefault() ?? location));
+                return null;
+            }
+
+            members.Add(key is int intKey
+                ? CreateMember(target, intKey: intKey, stringKey: target.Name)
+                : CreateMember(target, intKey: members.Count, stringKey: (string)key));
+        }
+
+        isIntKey = keyKindIsInt ?? false;
+        return members;
+    }
+
+    private static MemberSerializationInfo CreateMember(ISymbol target, int intKey, string stringKey)
+    {
+        ITypeSymbol memberType = GetMemberType(target);
+        bool isProperty = target is IPropertySymbol;
+        bool isInitOnly = target is IPropertySymbol { SetMethod.IsInitOnly: true };
+        bool isRequired = target switch
+        {
+            IPropertySymbol property => property.IsRequired,
+            IFieldSymbol field => field.IsRequired,
+            _ => false,
+        };
+
+        return new MemberSerializationInfo(
+            IsProperty: isProperty,
+            IsWritable: true,
+            IsReadable: true,
+            IsInitOnly: isInitOnly,
+            IsRequired: isRequired,
+            IntKey: intKey,
+            StringKey: stringKey,
+            Name: target.Name,
+            Type: memberType.ToDisplayString(SymbolDisplayFormat.FullyQualifiedFormat),
+            ShortTypeName: memberType.ToDisplayString(BinaryWriteTypeFormat),
+            CustomFormatter: null)
+        {
+            // Members of the formatted type are never colliding with a base-type member of the same name here,
+            // because GetInstanceMembers keeps only the most derived member of each name.
+            DeclaringType = null,
+        };
+    }
+
+    /// <summary>
+    /// Enumerates the instance fields and properties of a type and its base types, keeping only the most derived member of each name.
+    /// </summary>
+    private static List<ISymbol> GetInstanceMembers(INamedTypeSymbol type)
+    {
+        HashSet<string> seen = new(StringComparer.Ordinal);
+        List<ISymbol> result = new();
+        for (INamedTypeSymbol? current = type; current is not null && current.SpecialType != SpecialType.System_Object; current = current.BaseType)
+        {
+            foreach (ISymbol member in current.GetMembers())
+            {
+                if (member.IsStatic || member.IsImplicitlyDeclared || member is not (IPropertySymbol or IFieldSymbol))
+                {
+                    continue;
+                }
+
+                if (member is IPropertySymbol { IsIndexer: true })
+                {
+                    continue;
+                }
+
+                if (seen.Add(member.Name))
+                {
+                    result.Add(member);
+                }
+            }
+        }
+
+        return result;
+    }
+
+    private static bool IsPublicReadWrite(ISymbol member) => member switch
+    {
+        IPropertySymbol property => property.DeclaredAccessibility == Accessibility.Public
+            && property.GetMethod is { DeclaredAccessibility: Accessibility.Public }
+            && property.SetMethod is { DeclaredAccessibility: Accessibility.Public },
+        IFieldSymbol field => field.DeclaredAccessibility == Accessibility.Public && !field.IsReadOnly && !field.IsConst,
+        _ => false,
+    };
+
+    private static ITypeSymbol GetMemberType(ISymbol member) => member switch
+    {
+        IPropertySymbol property => property.Type,
+        IFieldSymbol field => field.Type,
+        _ => throw new ArgumentOutOfRangeException(nameof(member)),
+    };
+
+    private static bool IsPartial(INamedTypeSymbol symbol, CancellationToken cancellationToken)
+    {
+        return symbol.DeclaringSyntaxReferences
+            .Select(r => r.GetSyntax(cancellationToken))
+            .OfType<ClassDeclarationSyntax>()
+            .Any(c => c.Modifiers.Any(SyntaxKind.PartialKeyword));
+    }
+}

diff --git a/src/MessagePack.SourceGenerator/CodeAnalysis/GeneratedFormatterRequest.cs b/src/MessagePack.SourceGenerator/CodeAnalysis/GeneratedFormatterRequest.cs
new file mode 100644
index 00000000..edf09175
--- /dev/null
+++ b/src/MessagePack.SourceGenerator/CodeAnalysis/GeneratedFormatterRequest.cs
@@ -0,0 +1,13 @@
+// Copyright (c) All contributors. All rights reserved.
+// Licensed under the MIT license. See LICENSE file in the project root for full license information.
+
+using Microsoft.CodeAnalysis;
+
+namespace MessagePack.SourceGenerator.CodeAnalysis;
+
+/// <summary>
+/// A partial formatter class marked with <c>[GeneratedMessagePackFormatter]</c>, and the optional surrogate type it names.
+/// </summary>
+/// <param name="Formatter">The user-declared partial formatter class.</param>
+/// <param name="Surrogate">The surrogate type named by <c>SurrogateType</c>, or <see langword="null"/> for contractless mode.</param>
+public sealed record GeneratedFormatterRequest(INamedTypeSymbol Formatter, INamedTypeSymbol? Surrogate);

diff --git a/src/MessagePack.SourceGenerator/CodeAnalysis/ObjectSerializationInfo.cs b/src/MessagePack.SourceGenerator/CodeAnalysis/ObjectSerializationInfo.cs
index f1b4e762..c5d7422d 100644
--- a/src/MessagePack.SourceGenerator/CodeAnalysis/ObjectSerializationInfo.cs
+++ b/src/MessagePack.SourceGenerator/CodeAnalysis/ObjectSerializationInfo.cs
@@ -10,6 +10,12 @@ public record ObjectSerializationInfo : ResolverRegisterInfo
 {
     public required bool IsClass { get; init; }
 
+    /// <summary>
+    /// Gets a value indicating whether the formatter is a user-declared <c>partial</c> class marked with
+    /// <c>[GeneratedMessagePackFormatter]</c>, into which the generator writes the formatter body.
+    /// </summary>
+    public bool IsUserDeclaredFormatter { get; init; }
+
     public required GenericTypeParameterInfo[] GenericTypeParameters { get; init; }
 
     public required MemberSerializationInfo[] ConstructorParameters { get; init; }
@@ -159,6 +165,7 @@ public record ObjectSerializationInfo : ResolverRegisterInfo
         // Compare all the properties by value
         return base.Equals(other)
             && IsClass == other.IsClass
+            && IsUserDeclaredFormatter == other.IsUserDeclaredFormatter
             && GenericTypeParameters.SequenceEqual(other.GenericTypeParameters)
             && ConstructorParameters.SequenceEqual(other.ConstructorParameters)
             && IsIntKey == other.IsIntKey

diff --git a/src/MessagePack.SourceGenerator/GeneratorUtilities.cs b/src/MessagePack.SourceGenerator/GeneratorUtilities.cs
index ca35f234..eb282833 100644
--- a/src/MessagePack.SourceGenerator/GeneratorUtilities.cs
+++ b/src/MessagePack.SourceGenerator/GeneratorUtilities.cs
@@ -32,7 +32,10 @@ internal static class GeneratorUtilities
             predicate: static (node, ct) => node is ClassDeclarationSyntax { BaseList.Types.Count: > 0 },
             transform: (ctxt, ct) =>
             {
+                // Formatters marked with [GeneratedMessagePackFormatter] are generated by the source generator
+                // and are registered as ObjectSerializationInfo, so they must not also be registered as hand-written formatters.
                 return ctxt.SemanticModel.GetDeclaredSymbol(ctxt.Node, ct) is INamedTypeSymbol symbol
+                    && !symbol.GetAttributes().Any(a => a.AttributeClass?.ToDisplayString() == $"{AttributeNamespace}.{GeneratedMessagePackFormatterAttributeName}")
                     && FormatterDescriptor.TryCreate(symbol, out FormatterDescriptor? formatter)
                     && !formatter.ExcludeFromSourceGeneratedResolver
                     ? formatter

diff --git a/src/MessagePack.SourceGenerator/MessagePackGenerator.cs b/src/MessagePack.SourceGenerator/MessagePackGenerator.cs
index 66db96c2..4246a4e4 100644
--- a/src/MessagePack.SourceGenerator/MessagePackGenerator.cs
+++ b/src/MessagePack.SourceGenerator/MessagePackGenerator.cs
@@ -26,8 +26,15 @@ public partial class MessagePackGenerator : IIncrementalGenerator
             predicate: static (node, _) => node is InterfaceDeclarationSyntax,
             transform: static (context, _) => (ITypeSymbol)context.TargetSymbol);
 
+        var generatedFormatters = context.SyntaxProvider.ForAttributeWithMetadataName(
+            $"{AttributeNamespace}.{GeneratedMessagePackFormatterAttributeName}",
+            predicate: static (node, _) => node is ClassDeclarationSyntax,
+            transform: static (context, _) => new GeneratedFormatterRequest(
+                (INamedTypeSymbol)context.TargetSymbol,
+                context.Attributes[0].NamedArguments.FirstOrDefault(kvp => kvp.Key == GeneratedMessagePackFormatterSurrogatePropertyName).Value.Value as INamedTypeSymbol));
+
         var combined =
-            messagePackObjectTypes.Collect().Combine(unionTypes.Collect());
+            messagePackObjectTypes.Collect().Combine(unionTypes.Collect()).Combine(generatedFormatters.Collect());
 
         var source = combined
             .Combine(context.CompilationProvider)
@@ -50,16 +57,24 @@ public partial class MessagePackGenerator : IIncrementalGenerator
                     }
                 }
 
-                foreach (var typeSymbol in s.Left.Left.Left)
+                foreach (var typeSymbol in s.Left.Left.Left.Left)
                 {
                     Collect(typeSymbol);
                 }
 
-                foreach (var typeSymbol in s.Left.Left.Right)
+                foreach (var typeSymbol in s.Left.Left.Left.Right)
                 {
                     Collect(typeSymbol);
                 }
 
+                foreach (GeneratedFormatterRequest request in s.Left.Left.Right)
+                {
+                    if (GeneratedFormatterCollector.Collect(s.Left.Right, options, referenceSymbols, reportDiagnostic: null, request.Formatter, request.Surrogate, ct) is FullModel generatedModel)
+                    {
+                        modelPerType.Add(generatedModel);
+                    }
+                }
+
                 if (!options.KnownFormatters.IsEmpty)
                 {
                     var customFormatterInfos = FullModel.Empty.CustomFormatterInfos.Union(
@@ -97,6 +112,24 @@ public partial class MessagePackGenerator : IIncrementalGenerator
                 return models.ToImmutableArray();
             });
 
+        // Diagnostics for [GeneratedMessagePackFormatter] classes are reported separately from the models,
+        // so that a rejected formatter produces a diagnostic and no partial output.
+        var generatedFormatterDiagnostics = generatedFormatters
+            .Combine(context.CompilationProvider)
+            .Combine(options)
+            .SelectMany(static (s, ct) =>
+            {
+                List<Diagnostic> diagnostics = new();
+                if (ReferenceSymbols.TryCreate(s.Left.Right, out ReferenceSymbols? referenceSymbols))
+                {
+                    GeneratedFormatterCollector.Collect(s.Left.Right, s.Right, referenceSymbols, diagnostics.Add, s.Left.Left.Formatter, s.Left.Left.Surrogate, ct);
+                }
+
+                return diagnostics.ToImmutableArray();
+            });
+
+        context.RegisterSourceOutput(generatedFormatterDiagnostics, static (context, diagnostic) => context.ReportDiagnostic(diagnostic));
+
         context.RegisterSourceOutput(source, static (context, source) =>
         {
             if (source is { Options.IsGeneratingSource: true })

diff --git a/src/MessagePack.SourceGenerator/Transforms/FormatterTemplate.tt b/src/MessagePack.SourceGenerator/Transforms/FormatterTemplate.tt
index 2bd9a8a6..b6bf8696 100644
--- a/src/MessagePack.SourceGenerator/Transforms/FormatterTemplate.tt
+++ b/src/MessagePack.SourceGenerator/Transforms/FormatterTemplate.tt
@@ -11,7 +11,7 @@ using MsgPack = global::MessagePack;
 <# using (this.EmitNestingTypesAndNamespaces(this.Write)) { #>
 
 <#  bool isFormatterResolverNecessary = GeneratorUtilities.ShouldUseFormatterResolver(Info.Members);#>
-	internal sealed class <#= Info.Formatter.GetQualifiedName(Qualifiers.None) #> : MsgPack::Formatters.IMessagePackFormatter<<#= Info.DataType.GetQualifiedName(genericStyle: GenericParameterStyle.Identifiers) #>>
+	<#= Info.IsUserDeclaredFormatter ? "partial class" : "internal sealed class" #> <#= Info.Formatter.GetQualifiedName(Qualifiers.None) #> : MsgPack::Formatters.IMessagePackFormatter<<#= Info.DataType.GetQualifiedName(genericStyle: GenericParameterStyle.Identifiers) #>>
 <# TransformUtilities.EmitTypeConstraints(Info.Formatter, this.Write); #>
 	{
 <# foreach (var item in Info.Members) { #>

diff --git a/src/MessagePack.SourceGenerator/Transforms/StringKey/StringKeyFormatterTemplate.tt b/src/MessagePack.SourceGenerator/Transforms/StringKey/StringKeyFormatterTemplate.tt
index c81a3c37..39d892ef 100644
--- a/src/MessagePack.SourceGenerator/Transforms/StringKey/StringKeyFormatterTemplate.tt
+++ b/src/MessagePack.SourceGenerator/Transforms/StringKey/StringKeyFormatterTemplate.tt
@@ -15,7 +15,7 @@ using MsgPack = global::MessagePack;
 
 	bool isFormatterResolverNecessary = GeneratorUtilities.ShouldUseFormatterResolver(Info.Members); #>
 <# using (this.EmitNestingTypesAndNamespaces(this.Write)) { #>
-	internal sealed class <#= Info.Formatter.GetQualifiedName(Qualifiers.None) #> : global::MessagePack.Formatters.IMessagePackFormatter<<#= Info.DataType.GetQualifiedName() #>>
+	<#= Info.IsUserDeclaredFormatter ? "partial class" : "internal sealed class" #> <#= Info.Formatter.GetQualifiedName(Qualifiers.None) #> : global::MessagePack.Formatters.IMessagePackFormatter<<#= Info.DataType.GetQualifiedName() #>>
 <# TransformUtilities.EmitTypeConstraints(Info.Formatter, this.Write); #>
 	{
 <# foreach (var item in Info.Members) { #>

diff --git a/src/MessagePack.SourceGenerator/Utils/Constants.cs b/src/MessagePack.SourceGenerator/Utils/Constants.cs
index 4df875e4..f554f50f 100644
--- a/src/MessagePack.SourceGenerator/Utils/Constants.cs
+++ b/src/MessagePack.SourceGenerator/Utils/Constants.cs
@@ -14,6 +14,8 @@ internal static class Constants
     internal const string MessagePackAssumedFormattableAttributeName = "MessagePackAssumedFormattableAttribute";
     internal const string MessagePackObjectAttributeName = "MessagePackObjectAttribute";
     internal const string MessagePackUnionAttributeName = "UnionAttribute";
+    internal const string GeneratedMessagePackFormatterAttributeName = "GeneratedMessagePackFormatterAttribute";
+    internal const string GeneratedMessagePackFormatterSurrogatePropertyName = "SurrogateType";
     internal const string SuppressSourceGenerationPropertyName = "SuppressSourceGeneration";
     internal const string AllowPrivatePropertyName = "AllowPrivate";
 

diff --git a/tests/MessagePack.SourceGenerator.ExecutionTests/GeneratedFormatterForExternalTypes.cs b/tests/MessagePack.SourceGenerator.ExecutionTests/GeneratedFormatterForExternalTypes.cs
new file mode 100644
index 00000000..c5feac26
--- /dev/null
+++ b/tests/MessagePack.SourceGenerator.ExecutionTests/GeneratedFormatterForExternalTypes.cs
@@ -0,0 +1,50 @@
+// Copyright (c) All contributors. All rights reserved.
+// Licensed under the MIT license. See LICENSE file in the project root for full license information.
+
+using ExternalTypes.Library;
+using MessagePack.Formatters;
+
+// Formatter bodies for types from ExternalTypes that carry no MessagePack attributes.
+// The source generator writes the members of each partial class (https://github.com/MessagePack-CSharp/MessagePack-CSharp/issues/2129).
+[GeneratedMessagePackFormatter]
+public partial class ExternalPersonFormatter : IMessagePackFormatter<ExternalPerson>
+{
+}
+
+[GeneratedMessagePackFormatter]
+public partial class ExternalPointFormatter : IMessagePackFormatter<ExternalPoint>
+{
+}
+
+[GeneratedMessagePackFormatter(SurrogateType = typeof(ExternalWidgetSurrogate))]
+public partial class ExternalWidgetFormatter : IMessagePackFormatter<ExternalWidget>
+{
+}
+
+/// <summary>
+/// Describes the wire contract of <see cref="ExternalWidget"/>. It is only read at compile time and is never instantiated.
+/// </summary>
+public class ExternalWidgetSurrogate
+{
+    [Key(3)]
+    public int Id { get; set; }
+
+    [Key(7)]
+    public string Name { get; set; } = string.Empty;
+
+    [IgnoreMember]
+    public int Internal { get; set; }
+}
+
+/// <summary>
+/// A serializable type that refers to <see cref="ExternalPerson"/>, whose formatter is generated by <see cref="ExternalPersonFormatter"/>.
+/// </summary>
+[MessagePackObject]
+public class ContainsExternalPerson
+{
+    [Key(0)]
+    public ExternalPerson Person { get; set; }
+
+    [Key(1)]
+    public ExternalWidget Widget { get; set; }
+}

diff --git a/tests/MessagePack.SourceGenerator.ExecutionTests/GeneratedFormatterForExternalTypesTests.cs b/tests/MessagePack.SourceGenerator.ExecutionTests/GeneratedFormatterForExternalTypesTests.cs
new file mode 100644
index 00000000..904f41f8
--- /dev/null
+++ b/tests/MessagePack.SourceGenerator.ExecutionTests/GeneratedFormatterForExternalTypesTests.cs
@@ -0,0 +1,95 @@
+// Copyright (c) All contributors. All rights reserved.
+// Licensed under the MIT license. See LICENSE file in the project root for full license information.
+
+using ExternalTypes.Library;
+
+public class GeneratedFormatterForExternalTypesTests
+{
+    private static readonly MessagePackSerializerOptions Options = MessagePackSerializerOptions.Standard
+        .WithResolver(CompositeResolver.Create(GeneratedMessagePackResolver.Instance, StandardResolver.Instance));
+
+    [Fact]
+    public void ContractlessClassRoundTrips()
+    {
+        var person = new ExternalPerson { Id = 7, Label = "seven" };
+
+        byte[] bytes = MessagePackSerializer.Serialize(person, Options);
+        ExternalPerson result = MessagePackSerializer.Deserialize<ExternalPerson>(bytes, Options);
+
+        Assert.Equal(7, result.Id);
+        Assert.Equal("seven", result.Label);
+    }
+
+    [Fact]
+    public void ContractlessClassUsesStringKeysForPublicReadWriteMembers()
+    {
+        byte[] bytes = MessagePackSerializer.Serialize(new ExternalPerson { Id = 1, Label = "x" }, Options);
+
+        // A fixmap with two entries: Id and Label. The read-only Doubled member is not serialized.
+        Assert.Equal(0x82, bytes[0]);
+        string json = MessagePackSerializer.ConvertToJson(bytes, Options);
+        Assert.Contains("\"Id\":1", json);
+        Assert.Contains("\"Label\":\"x\"", json);
+        Assert.DoesNotContain("Doubled", json);
+    }
+
+    [Fact]
+    public void ContractlessClassNullRoundTrips()
+    {
+        byte[] bytes = MessagePackSerializer.Serialize(default(ExternalPerson), Options);
+        Assert.Null(MessagePackSerializer.Deserialize<ExternalPerson>(bytes, Options));
+    }
+
+    [Fact]
+    public void ContractlessStructRoundTrips()
+    {
+        var point = new ExternalPoint { X = 3, Y = -4 };
+
+        ExternalPoint result = MessagePackSerializer.Deserialize<ExternalPoint>(MessagePackSerializer.Serialize(point, Options), Options);
+
+        Assert.Equal(3, result.X);
+        Assert.Equal(-4, result.Y);
+    }
+
+    [Fact]
+    public void SurrogateControlsKeysAndMembership()
+    {
+        var widget = new ExternalWidget { Id = 1, Name = "w", Internal = 99 };
+
+        byte[] bytes = MessagePackSerializer.Serialize(widget, Options);
+
+        // The surrogate uses integer keys 3 and 7, so the array has MaxKey + 1 = 8 slots.
+        var reader = new MessagePackReader(bytes);
+        Assert.Equal(8, reader.ReadArrayHeader());
+
+        ExternalWidget result = MessagePackSerializer.Deserialize<ExternalWidget>(bytes, Options);
+        Assert.Equal(1, result.Id);
+        Assert.Equal("w", result.Name);
+        Assert.Equal(0, result.Internal);
+    }
+
+    [Fact]
+    public void MessagePackObjectCanContainExternalTypes()
+    {
+        var value = new ContainsExternalPerson
+        {
+            Person = new ExternalPerson { Id = 5, Label = "five" },
+            Widget = new ExternalWidget { Id = 6, Name = "six" },
+        };
+
+        ContainsExternalPerson result = MessagePackSerializer.Deserialize<ContainsExternalPerson>(MessagePackSerializer.Serialize(value, Options), Options);
+
+        Assert.Equal(5, result.Person.Id);
+        Assert.Equal("five", result.Person.Label);
+        Assert.Equal(6, result.Widget.Id);
+        Assert.Equal("six", result.Widget.Name);
+    }
+
+    [Fact]
+    public void GeneratedFormattersAreRegisteredInGeneratedResolver()
+    {
+        Assert.IsType<ExternalPersonFormatter>(GeneratedMessagePackResolver.Instance.GetFormatter<ExternalPerson>());
+        Assert.IsType<ExternalPointFormatter>(GeneratedMessagePackResolver.Instance.GetFormatter<ExternalPoint>());
+        Assert.IsType<ExternalWidgetFormatter>(GeneratedMessagePackResolver.Instance.GetFormatter<ExternalWidget>());
+    }
+}

diff --git a/tests/MessagePack.SourceGenerator.ExecutionTests/MessagePack.SourceGenerator.ExecutionTests.csproj b/tests/MessagePack.SourceGenerator.ExecutionTests/MessagePack.SourceGenerator.ExecutionTests.csproj
index 1bb24dcc..ca55cf19 100644
--- a/tests/MessagePack.SourceGenerator.ExecutionTests/MessagePack.SourceGenerator.ExecutionTests.csproj
+++ b/tests/MessagePack.SourceGenerator.ExecutionTests/MessagePack.SourceGenerator.ExecutionTests.csproj
@@ -14,5 +14,10 @@
     <PackageReference Include="xunit.runner.visualstudio" />
   </ItemGroup>
 
+  <ItemGroup>
+    <!-- Types from an assembly that does not reference MessagePack (https://github.com/MessagePack-CSharp/MessagePack-CSharp/issues/2129). -->
+    <ProjectReference Include="..\MessagePack.SourceGenerator.ExternalTypes\MessagePack.SourceGenerator.ExternalTypes.csproj" />
+  </ItemGroup>
+
   <Import Project="..\SourceGeneratorConsumer.targets" />
 </Project>

diff --git a/tests/MessagePack.SourceGenerator.ExternalTypes/ExternalPerson.cs b/tests/MessagePack.SourceGenerator.ExternalTypes/ExternalPerson.cs
new file mode 100644
index 00000000..d824057b
--- /dev/null
+++ b/tests/MessagePack.SourceGenerator.ExternalTypes/ExternalPerson.cs
@@ -0,0 +1,15 @@
+// Copyright (c) All contributors. All rights reserved.
+// Licensed under the MIT license. See LICENSE file in the project root for full license information.
+
+namespace ExternalTypes.Library;
+
+/// <summary>A type with no serialization attributes. Its public read-write members are serialized in contractless mode.</summary>
+public class ExternalPerson
+{
+    public int Id { get; set; }
+
+    public string Label { get; set; }
+
+    /// <summary>Gets a value derived from <see cref="Id"/>. Contractless mode skips it because it cannot be deserialized.</summary>
+    public int Doubled => this.Id * 2;
+}

diff --git a/tests/MessagePack.SourceGenerator.ExternalTypes/ExternalPoint.cs b/tests/MessagePack.SourceGenerator.ExternalTypes/ExternalPoint.cs
new file mode 100644
index 00000000..48ac1203
--- /dev/null
+++ b/tests/MessagePack.SourceGenerator.ExternalTypes/ExternalPoint.cs
@@ -0,0 +1,12 @@
+// Copyright (c) All contributors. All rights reserved.
+// Licensed under the MIT license. See LICENSE file in the project root for full license information.
+
+namespace ExternalTypes.Library;
+
+/// <summary>A struct with no serialization attributes.</summary>
+public struct ExternalPoint
+{
+    public int X { get; set; }
+
+    public int Y { get; set; }
+}

diff --git a/tests/MessagePack.SourceGenerator.ExternalTypes/ExternalWidget.cs b/tests/MessagePack.SourceGenerator.ExternalTypes/ExternalWidget.cs
new file mode 100644
index 00000000..9590ad2c
--- /dev/null
+++ b/tests/MessagePack.SourceGenerator.ExternalTypes/ExternalWidget.cs
@@ -0,0 +1,15 @@
+// Copyright (c) All contributors. All rights reserved.
+// Licensed under the MIT license. See LICENSE file in the project root for full license information.
+
+namespace ExternalTypes.Library;
+
+/// <summary>A type with no serialization attributes whose wire contract is described by a surrogate type in the consuming assembly.</summary>
+public class ExternalWidget
+{
+    public int Id { get; set; }
+
+    public string Name { get; set; }
+
+    /// <summary>Gets or sets a value that is not part of the surrogate's contract, so it is not serialized.</summary>
+    public int Internal { get; set; }
+}

diff --git a/tests/MessagePack.SourceGenerator.ExternalTypes/MessagePack.SourceGenerator.ExternalTypes.csproj b/tests/MessagePack.SourceGenerator.ExternalTypes/MessagePack.SourceGenerator.ExternalTypes.csproj
new file mode 100644
index 00000000..145125d3
--- /dev/null
+++ b/tests/MessagePack.SourceGenerator.ExternalTypes/MessagePack.SourceGenerator.ExternalTypes.csproj
@@ -0,0 +1,17 @@
+<Project Sdk="Microsoft.NET.Sdk">
+
+  <!--
+    This assembly deliberately does NOT reference MessagePack.
+    It models a dependency-free library (Project A in https://github.com/MessagePack-CSharp/MessagePack-CSharp/issues/2129)
+    whose types are serialized by generated formatters declared in a consuming assembly.
+  -->
+  <PropertyGroup>
+    <TargetFramework>net8.0</TargetFramework>
+    <ImplicitUsings>disable</ImplicitUsings>
+    <Nullable>disable</Nullable>
+    <IsTestProject>false</IsTestProject>
+    <NonShipping>true</NonShipping>
+    <NoWarn>$(NoWarn);CS1591</NoWarn>
+  </PropertyGroup>
+
+</Project>

diff --git a/tests/MessagePack.SourceGenerator.MapModeExecutionTests/MessagePack.SourceGenerator.MapModeExecutionTests.csproj b/tests/MessagePack.SourceGenerator.MapModeExecutionTests/MessagePack.SourceGenerator.MapModeExecutionTests.csproj
index cdb16c2c..73997170 100644
--- a/tests/MessagePack.SourceGenerator.MapModeExecutionTests/MessagePack.SourceGenerator.MapModeExecutionTests.csproj
+++ b/tests/MessagePack.SourceGenerator.MapModeExecutionTests/MessagePack.SourceGenerator.MapModeExecutionTests.csproj
@@ -10,7 +10,8 @@
   </PropertyGroup>
 
   <ItemGroup>
-    <Compile Include="..\MessagePack.SourceGenerator.ExecutionTests\**\*.cs" Exclude="..\MessagePack.SourceGenerator.ExecutionTests\**\GeneratedMessagePackResolver.cs" />
+    <!-- GeneratedFormatterForExternalTypes*.cs need the ExternalTypes assembly, which this project does not reference. -->
+    <Compile Include="..\MessagePack.SourceGenerator.ExecutionTests\**\*.cs" Exclude="..\MessagePack.SourceGenerator.ExecutionTests\**\GeneratedMessagePackResolver.cs;..\MessagePack.SourceGenerator.ExecutionTests\**\GeneratedFormatterForExternalTypes*.cs" />
   </ItemGroup>
 
   <ItemGroup>

diff --git a/tests/MessagePack.SourceGenerator.Tests/GeneratedMessagePackFormatterTests.cs b/tests/MessagePack.SourceGenerator.Tests/GeneratedMessagePackFormatterTests.cs
new file mode 100644
index 00000000..7161ffc9
--- /dev/null
+++ b/tests/MessagePack.SourceGenerator.Tests/GeneratedMessagePackFormatterTests.cs
@@ -0,0 +1,210 @@
+// Copyright (c) All contributors. All rights reserved.
+// Licensed under the MIT license. See LICENSE file in the project root for full license information.
+
+using MessagePack.SourceGenerator.Tests;
+using Microsoft.CodeAnalysis.Testing;
+using VerifyCS = CSharpSourceGeneratorVerifier<MessagePack.SourceGenerator.MessagePackGenerator>;
+
+/// <summary>
+/// Tests for <c>[GeneratedMessagePackFormatter]</c>, which lets the generator write a formatter for a type from another assembly (https://github.com/MessagePack-CSharp/MessagePack-CSharp/issues/2129).
+/// </summary>
+public class GeneratedMessagePackFormatterTests
+{
+    private readonly ITestOutputHelper testOutputHelper;
+
+    public GeneratedMessagePackFormatterTests(ITestOutputHelper testOutputHelper)
+    {
+        this.testOutputHelper = testOutputHelper;
+    }
+
+    // Formatter members are written by hand in the diagnostic tests, so the compiler accepts the source
+    // even when the generator declines to write them.
+    private const string Members = """
+            public void Serialize(ref MessagePackWriter writer, MyType value, MessagePackSerializerOptions options) => throw new System.NotImplementedException();
+
+            public MyType Deserialize(ref MessagePackReader reader, MessagePackSerializerOptions options) => throw new System.NotImplementedException();
+        """;
+
+    [Fact]
+    public async Task FormatterMustBePartial()
+    {
+        string testSource = /* lang=c#-test */ $$"""
+            using MessagePack;
+            using MessagePack.Formatters;
+
+            public class MyType
+            {
+                public int Id { get; set; }
+            }
+
+            [GeneratedMessagePackFormatter]
+            public class {|MsgPack019:MyFormatter|} : IMessagePackFormatter<MyType>
+            {
+            {{Members}}
+            }
+            """;
+
+        await new VerifyCS.Test
+        {
+            TestState =
+            {
+                Sources = { testSource },
+            },
+        }.RunDefaultAsync(this.testOutputHelper);
+    }
+
+    [Fact]
+    public async Task FormatterMustImplementFormatterOfT()
+    {
+        string testSource = /* lang=c#-test */ """
+            using MessagePack;
+
+            [GeneratedMessagePackFormatter]
+            public partial class {|MsgPack020:MyFormatter|}
+            {
+            }
+            """;
+
+        await new VerifyCS.Test
+        {
+            TestState =
+            {
+                Sources = { testSource },
+            },
+        }.RunDefaultAsync(this.testOutputHelper);
+    }
+
+    [Fact]
+    public async Task FormattedTypeMustNotBeAbstract()
+    {
+        string testSource = /* lang=c#-test */ $$"""
+            using MessagePack;
+            using MessagePack.Formatters;
+
+            public abstract class MyType
+            {
+            }
+
+            [GeneratedMessagePackFormatter]
+            public partial class {|MsgPack021:MyFormatter|} : IMessagePackFormatter<MyType>
+            {
+            {{Members}}
+            }
+            """;
+
+        await new VerifyCS.Test
+        {
+            TestState =
+            {
+                Sources = { testSource },
+            },
+        }.RunDefaultAsync(this.testOutputHelper);
+    }
+
+    [Fact]
+    public async Task SurrogateMemberMustMatchFormattedType()
+    {
+        string testSource = /* lang=c#-test */ $$"""
+            using MessagePack;
+            using MessagePack.Formatters;
+
+            public class MyType
+            {
+                public int Id { get; set; }
+            }
+
+            public class MySurrogate
+            {
+                [Key(0)]
+                public int {|MsgPack022:Missing|} { get; set; }
+            }
+
+            [GeneratedMessagePackFormatter(SurrogateType = typeof(MySurrogate))]
+            public partial class MyFormatter : IMessagePackFormatter<MyType>
+            {
+            {{Members}}
+            }
+            """;
+
+        await new VerifyCS.Test
+        {
+            TestState =
+            {
+                Sources = { testSource },
+            },
+        }.RunDefaultAsync(this.testOutputHelper);
+    }
+
+    [Fact]
+    public async Task SurrogateMemberMustHaveMatchingType()
+    {
+        string testSource = /* lang=c#-test */ $$"""
+            using MessagePack;
+            using MessagePack.Formatters;
+
+            public class MyType
+            {
+                public int Id { get; set; }
+            }
+
+            public class MySurrogate
+            {
+                [Key(0)]
+                public string {|MsgPack022:Id|} { get; set; }
+            }
+
+            [GeneratedMessagePackFormatter(SurrogateType = typeof(MySurrogate))]
+            public partial class MyFormatter : IMessagePackFormatter<MyType>
+            {
+            {{Members}}
+            }
+            """;
+
+        await new VerifyCS.Test
+        {
+            TestState =
+            {
+                Sources = { testSource },
+            },
+        }.RunDefaultAsync(this.testOutputHelper);
+    }
+
+    [Fact]
+    public async Task SurrogateKeysMustNotMixStringAndInt()
+    {
+        string testSource = /* lang=c#-test */ $$"""
+            using MessagePack;
+            using MessagePack.Formatters;
+
+            public class MyType
+            {
+                public int Id { get; set; }
+                public string Name { get; set; }
+            }
+
+            public class MySurrogate
+            {
+                [Key(0)]
+                public int Id { get; set; }
+
+                [Key("Name")]
+                public string {|#0:Name|} { get; set; }
+            }
+
+            [GeneratedMessagePackFormatter(SurrogateType = typeof(MySurrogate))]
+            public partial class MyFormatter : IMessagePackFormatter<MyType>
+            {
+            {{Members}}
+            }
+            """;
+
+        await new VerifyCS.Test
+        {
+            TestState =
+            {
+                Sources = { testSource },
+            },
+            ExpectedDiagnostics = { DiagnosticResult.CompilerError("MsgPack005").WithLocation(0) },
+        }.RunDefaultAsync(this.testOutputHelper);
+    }
+}

```

## File contents (line numbers in the gutter; quote the text after '| ')

### src/MessagePack.Annotations/Attributes.cs at head (083afd99), around the changed lines
```
  ... lines 1-108 not shown ...
  109|         /// </summary>
  110|         /// <param name="key">The distinguishing value that identifies a particular subtype.</param>
  111|         /// <param name="subType">The full name (should be assembly qualified) of the derived or implementing type.</param>
  112|         public UnionAttribute(int key, string subType)
  113|         {
  114|             this.Key = key;
  115|             this.SubType = Type.GetType(subType, throwOnError: true);
  116|         }
  117|     }
  118| 
  119|     [AttributeUsage(AttributeTargets.Constructor, AllowMultiple = false, Inherited = true)]
  120|     public class SerializationConstructorAttribute : Attribute
  121|     {
  122|     }
  123| 
  124|     [AttributeUsage(AttributeTargets.Class | AttributeTargets.Struct | AttributeTargets.Interface | AttributeTargets.Enum | AttributeTargets.Field | AttributeTargets.Property | AttributeTargets.Parameter | AttributeTargets.ReturnValue, AllowMultiple = false, Inherited = true)]
  125|     public class MessagePackFormatterAttribute : Attribute
  126|     {
  127|         public Type FormatterType { get; }
  128| 
  129|         public object?[]? Arguments { get; }
  130| 
  131|         public MessagePackFormatterAttribute(Type formatterType)
  132|         {
  133|             this.FormatterType = formatterType ?? throw new ArgumentNullException(nameof(formatterType));
  134|         }
  135| 
  136|         public MessagePackFormatterAttribute(Type formatterType, params object?[]? arguments)
  137|         {
  138|             this.FormatterType = formatterType ?? throw new ArgumentNullException(nameof(formatterType));
  139|             this.Arguments = arguments;
  140|         }
  141|     }
  142| 
  143|     /// <summary>
  144|     /// Marks a <see langword="partial"/> class that implements <c>IMessagePackFormatter&lt;T&gt;</c> so that the MessagePack source generator
  145|     /// writes the formatter implementation for <c>T</c>, even when <c>T</c> is declared in another assembly that cannot reference MessagePack.
  146|     /// </summary>
  147|     /// <remarks>
  148|     /// <para>
  149|     /// The formatted type <c>T</c> is serialized in contractless mode: every public, non-static, read-write instance property and field
  150|     /// is serialized using its name as a string key. No attributes are required on <c>T</c>.
  151|     /// </para>
  152|     /// <para>
  153|     /// To control keys and membership without touching <c>T</c>, set <see cref="SurrogateType"/> to a type whose
  154|     /// <see cref="KeyAttribute"/> and <see cref="IgnoreMemberAttribute"/> annotations describe the wire contract.
  155|     /// The surrogate is only read at compile time and is never instantiated at run time.
  156|     /// Surrogate members are matched to members of <c>T</c> by name.
  157|     /// </para>
  158|     /// </remarks>
  159|     /// <example>
  160|     /// <code>
  161|     /// [GeneratedMessagePackFormatter]
  162|     /// public partial class MyObjectFormatter : IMessagePackFormatter&lt;ProjectA.MyObject&gt; { }
  163|     /// </code>
  164|     /// </example>
  165|     [AttributeUsage(AttributeTargets.Class, AllowMultiple = false, Inherited = false)]
  166|     public class GeneratedMessagePackFormatterAttribute : Attribute
  167|     {
  168|         /// <summary>
  169|         /// Gets or sets a type whose <see cref="KeyAttribute"/> members define the keys and membership of the formatted type.
  170|         /// </summary>
  171|         /// <remarks>
  172|         /// Each surrogate member that carries a <see cref="KeyAttribute"/> must match a public, read-write instance member of the formatted type by name.
  173|         /// Surrogate members that carry <see cref="IgnoreMemberAttribute"/> are excluded.
  174|         /// All keys in the surrogate must be the same kind (all integer or all string).
  175|         /// </remarks>
  176|         public Type? SurrogateType { get; set; }
  177|     }
  178| }
```

### src/MessagePack.SourceGenerator/Analyzers/MsgPack00xMessagePackAnalyzer.cs at head (083afd99), around the changed lines
```
    1| // Copyright (c) All contributors. All rights reserved.
    2| // Licensed under the MIT license. See LICENSE file in the project root for full license information.
    3| 
    4| using System.Collections.Immutable;
    5| using Microsoft.CodeAnalysis;
    6| using Microsoft.CodeAnalysis.CSharp;
    7| using Microsoft.CodeAnalysis.CSharp.Syntax;
    8| using Microsoft.CodeAnalysis.Diagnostics;
    9| using AnalyzerOptions = MessagePack.SourceGenerator.CodeAnalysis.AnalyzerOptions;
   10| 
   11| namespace MessagePack.SourceGenerator.Analyzers;
   12| 
   13| [DiagnosticAnalyzer(LanguageNames.CSharp)]
   14| public class MsgPack00xMessagePackAnalyzer : DiagnosticAnalyzer
   15| {
   16|     public const string UseMessagePackObjectAttributeId = "MsgPack003";
   17|     public const string AttributeMessagePackObjectMembersId = "MsgPack004";
   18|     public const string InvalidMessagePackObjectId = "MsgPack005";
   19|     public const string MessagePackFormatterMustBeMessagePackFormatterId = "MsgPack006";
   20|     public const string DeserializingConstructorId = "MsgPack007";
   21|     public const string AOTLimitationsId = "MsgPack008";
   22|     public const string CollidingFormattersId = "MsgPack009";
   23|     public const string InaccessibleFormatterTypeId = "MsgPack010";
   24|     public const string PartialTypeRequiredId = "MsgPack011";
   25|     public const string InaccessibleDataTypeId = "MsgPack012";
   26|     public const string InaccessibleFormatterInstanceId = "MsgPack013";
   27|     public const string NullableReferenceTypeFormatterId = "MsgPack014";
   28|     public const string MessagePackObjectAllowPrivateId = "MsgPack015";
   29|     public const string AOTDerivedKeyId = "MsgPack016";
   30|     public const string AOTInitPropertyId = "MsgPack017";
   31|     public const string CollidingMemberNamesInForceMapModeId = "MsgPack018";
   32|     public const string GeneratedFormatterMustBePartialId = "MsgPack019";
   33|     public const string GeneratedFormatterMustImplementFormatterId = "MsgPack020";
   34|     public const string GeneratedFormatterDataTypeNotSupportedId = "MsgPack021";
   35|     public const string SurrogateMemberNotFoundId = "MsgPack022";
   36| 
   37|     internal const string Category = "Usage";
   38| 
   39|     public const string MessagePackObjectAttributeShortName = Constants.MessagePackObjectAttributeName;
   40|     public const string KeyAttributeShortName = "KeyAttribute";
   41|     public const string IgnoreShortName = "IgnoreMemberAttribute";
   42|     public const string DataMemberShortName = "DataMemberAttribute";
   43|     public const string IgnoreDataMemberShortName = "IgnoreDataMemberAttribute";
   44|     public const string AllowPrivatePropertyName = "AllowPrivate";
   45| 
   46|     private const string InvalidMessagePackObjectTitle = "MessagePackObject validation";
   47|     private const DiagnosticSeverity InvalidMessagePackObjectSeverity = DiagnosticSeverity.Error;
   48| 
   49|     public static readonly DiagnosticDescriptor TypeMustBeMessagePackObject = new DiagnosticDescriptor(
   50|         id: UseMessagePackObjectAttributeId,
   51|         title: "Use MessagePackObjectAttribute",
   52|         category: Category,
   53|         messageFormat: "Type must be marked with MessagePackObjectAttribute: {0}", // type.Name
   54|         description: "Type must be marked with MessagePackObjectAttribute.",
   55|         defaultSeverity: DiagnosticSeverity.Error,
   56|         isEnabledByDefault: true,
   57|         helpLinkUri: AnalyzerUtilities.GetHelpLink(UseMessagePackObjectAttributeId));
   58| 
   59|     public static readonly DiagnosticDescriptor MessageFormatterMustBeMessagePackFormatter = new DiagnosticDescriptor(
   60|         id: MessagePackFormatterMustBeMessagePackFormatterId,
   61|         title: "Must be IMessageFormatter",
   62|         category: Category,
   63|         messageFormat: "Type must be of IMessagePackFormatter: {0}", // type.Name
   64|         description: "Type must be of IMessagePackFormatter.",
   65|         defaultSeverity: DiagnosticSeverity.Error,
   66|         isEnabledByDefault: true,
   67|         helpLinkUri: AnalyzerUtilities.GetHelpLink(MessagePackFormatterMustBeMessagePackFormatterId));
   68| 
  ... lines 69-284 not shown ...
  285|         messageFormat: "This MessagePack formattable type must have at least internal visibility",
  286|         description: "MessagePack serializable objects must be at least internally accessible so a source-generated formatter can access it.",
  287|         defaultSeverity: DiagnosticSeverity.Error,
  288|         isEnabledByDefault: true,
  289|         helpLinkUri: AnalyzerUtilities.GetHelpLink(InaccessibleDataTypeId));
  290| 
  291|     public static readonly DiagnosticDescriptor NullableReferenceTypeFormatter = new(
  292|         id: NullableReferenceTypeFormatterId,
  293|         title: "Format nullable reference types",
  294|         category: Category,
  295|         messageFormat: "Implement IMessagePackFormatter<{0}?> (with nullable annotation)",
  296|         defaultSeverity: DiagnosticSeverity.Warning,
  297|         isEnabledByDefault: true,
  298|         helpLinkUri: AnalyzerUtilities.GetHelpLink(NullableReferenceTypeFormatterId));
  299| 
  300|     public static readonly DiagnosticDescriptor MessagePackObjectAllowPrivateRequired = new(
  301|         id: MessagePackObjectAllowPrivateId,
  302|         title: "MessagePackObjectAttribute.AllowPrivate should be set",
  303|         category: Category,
  304|         messageFormat: "MessagePackObjectAttribute.AllowPrivate should be set to true because the type is not public and/or at least one of its non-public members are attributed for serialization",
  305|         defaultSeverity: DiagnosticSeverity.Warning,
  306|         isEnabledByDefault: true,
  307|         helpLinkUri: AnalyzerUtilities.GetHelpLink(MessagePackObjectAllowPrivateId));
  308| 
  309|     public static readonly DiagnosticDescriptor CollidingMemberNamesInForceMapMode = new(
  310|         id: CollidingMemberNamesInForceMapModeId,
  311|         title: "Unique names required in force map mode",
  312|         category: Category,
  313|         messageFormat: "All serialized member names must be unique in force map mode, but this member redeclares a member with the same name as one found on a base type",
  314|         defaultSeverity: DiagnosticSeverity.Error,
  315|         isEnabledByDefault: true,
  316|         helpLinkUri: AnalyzerUtilities.GetHelpLink(CollidingMemberNamesInForceMapModeId));
  317| 
  318|     public static readonly DiagnosticDescriptor GeneratedFormatterMustBePartial = new(
  319|         id: GeneratedFormatterMustBePartialId,
  320|         title: "Generated formatter must be partial",
  321|         category: Category,
  322|         messageFormat: "The formatter '{0}' is marked with [GeneratedMessagePackFormatter] and must be declared 'partial' so the source generator can write its implementation",
  323|         defaultSeverity: DiagnosticSeverity.Error,
  324|         isEnabledByDefault: true,
  325|         helpLinkUri: AnalyzerUtilities.GetHelpLink(GeneratedFormatterMustBePartialId));
  326| 
  327|     public static readonly DiagnosticDescriptor GeneratedFormatterMustImplementFormatter = new(
  328|         id: GeneratedFormatterMustImplementFormatterId,
  329|         title: "Generated formatter must implement IMessagePackFormatter<T>",
  330|         category: Category,
  331|         messageFormat: "The formatter '{0}' is marked with [GeneratedMessagePackFormatter] but does not implement IMessagePackFormatter<T> for exactly one data type",
  332|         defaultSeverity: DiagnosticSeverity.Error,
  333|         isEnabledByDefault: true,
  334|         helpLinkUri: AnalyzerUtilities.GetHelpLink(GeneratedFormatterMustImplementFormatterId));
  335| 
  336|     public static readonly DiagnosticDescriptor GeneratedFormatterDataTypeNotSupported = new(
  337|         id: GeneratedFormatterDataTypeNotSupportedId,
  338|         title: "Generated formatter data type not supported",
  339|         category: Category,
  340|         messageFormat: "The formatter '{0}' cannot generate a formatter for '{1}': only accessible, non-generic, non-abstract classes and structs are supported",
  341|         defaultSeverity: DiagnosticSeverity.Error,
  342|         isEnabledByDefault: true,
  343|         helpLinkUri: AnalyzerUtilities.GetHelpLink(GeneratedFormatterDataTypeNotSupportedId));
  344| 
  345|     public static readonly DiagnosticDescriptor SurrogateMemberNotFound = new(
  346|         id: SurrogateMemberNotFoundId,
  347|         title: "Surrogate member does not match the formatted type",
  348|         category: Category,
  349|         messageFormat: "The surrogate member '{0}' has no matching public, read-write instance member with the same name and type on '{1}'",
  350|         defaultSeverity: DiagnosticSeverity.Error,
  351|         isEnabledByDefault: true,
  352|         helpLinkUri: AnalyzerUtilities.GetHelpLink(SurrogateMemberNotFoundId));
  353| 
  354|     public override ImmutableArray<DiagnosticDescriptor> SupportedDiagnostics { get; } = ImmutableArray.Create(
  355|         TypeMustBeMessagePackObject,
  356|         MessageFormatterMustBeMessagePackFormatter,
  357|         MemberNeedsKey,
  358|         BaseTypeContainsUnattributedPublicMembers,
  359|         InvalidMessagePackObject,
  360|         BothStringAndIntKeyAreNull,
  361|         DoNotMixStringAndIntKeys,
  362|         KeysMustBeUnique,
  363|         UnionAttributeRequired,
  364|         KeyAnnotatedMemberInMapMode,
  365|         NoDeserializingConstructor,
  366|         DeserializingConstructorParameterTypeMismatch,
  367|         DeserializingConstructorParameterIndexMissing,
  368|         DeserializingConstructorParameterNameMissing,
  369|         DeserializingConstructorParameterNameDuplicate,
  370|         AotUnionAttributeRequiresTypeArg,
  371|         AotArrayRankTooHigh,
  372|         AOTDerivedKeyAttribute,
  373|         AOTInitProperty,
  374|         CollidingFormatters,
  375|         InaccessibleFormatterInstance,
  376|         InaccessibleFormatterType,
  377|         PartialTypeRequired,
  378|         InaccessibleDataType,
  379|         NullableReferenceTypeFormatter,
  380|         MessagePackObjectAllowPrivateRequired,
  381|         CollidingMemberNamesInForceMapMode,
  382|         GeneratedFormatterMustBePartial,
  383|         GeneratedFormatterMustImplementFormatter,
  384|         GeneratedFormatterDataTypeNotSupported,
  385|         SurrogateMemberNotFound);
  386| 
  387|     public override void Initialize(AnalysisContext context)
  388|     {
  389|         context.EnableConcurrentExecution();
  390|         context.ConfigureGeneratedCodeAnalysis(GeneratedCodeAnalysisFlags.Analyze | GeneratedCodeAnalysisFlags.ReportDiagnostics);
  391|         context.RegisterCompilationStartAction(context =>
  392|         {
  393|             if (ReferenceSymbols.TryCreate(context.Compilation, out ReferenceSymbols? typeReferences))
  394|             {
  395|                 // Search the compilation for implementations of IMessagePackFormatter<T>.
  396|                 ImmutableHashSet<FormatterDescriptor> formatterTypes = this.SearchForFormatters(context.Compilation.Assembly.GlobalNamespace).ToImmutableHashSet();
  397| 
  398|                 AnalyzerOptions options = new AnalyzerOptions()
  399|                     .WithFormatterTypes(ImmutableArray<FormattableType>.Empty, formatterTypes)
  400|                     .WithAssemblyAttributes(context.Compilation.Assembly.GetAttributes(), context.CancellationToken);
  401|                 context.RegisterSymbolAction(context => this.AnalyzeSymbol(context, typeReferences, options), SymbolKind.NamedType);
  402|                 context.RegisterSymbolStartAction(context => SymbolStartAction(context, typeReferences, options), SymbolKind.NamedType);
  403|             }
  404|         });
  405|     }
  406| 
  407|     private static void SymbolStartAction(SymbolStartAnalysisContext context, ReferenceSymbols typeReferences, AnalyzerOptions options)
  408|     {
  409|         INamedTypeSymbol declaredSymbol = (INamedTypeSymbol)context.Symbol;
  410|         QualifiedNamedTypeName typeName = new(declaredSymbol);
  411| 
  412|         // If this is a formatter, confirm that it meets requirements.
  413|         if (options.KnownFormattersByName.TryGetValue(typeName, out FormatterDescriptor? formatter))
  414|         {
  415|             // Call out any formattable reference types that are not nullable.
  416|             INamedTypeSymbol[] missing = (
  417|                 from iface in declaredSymbol.Interfaces
  418|                 where SymbolEqualityComparer.Default.Equals(iface.ConstructUnboundGenericType(), typeReferences.MessagePackFormatterOfT) &&
  ... lines 419-511 not shown ...
```

### src/MessagePack.SourceGenerator/CodeAnalysis/GeneratedFormatterCollector.cs at head (083afd99), full file
```
    1| // Copyright (c) All contributors. All rights reserved.
    2| // Licensed under the MIT license. See LICENSE file in the project root for full license information.
    3| 
    4| using System.Collections.Immutable;
    5| using MessagePack.SourceGenerator.Analyzers;
    6| using Microsoft.CodeAnalysis;
    7| using Microsoft.CodeAnalysis.CSharp;
    8| using Microsoft.CodeAnalysis.CSharp.Syntax;
    9| 
   10| namespace MessagePack.SourceGenerator.CodeAnalysis;
   11| 
   12| /// <summary>
   13| /// Builds the serialization model for a partial formatter marked with <c>[GeneratedMessagePackFormatter]</c>.
   14| /// The formatted type may come from an assembly that carries no MessagePack attributes, so its members are read
   15| /// in contractless mode, or through the keys declared on an optional surrogate type.
   16| /// </summary>
   17| internal static class GeneratedFormatterCollector
   18| {
   19|     private static readonly SymbolDisplayFormat BinaryWriteTypeFormat = new(
   20|         genericsOptions: SymbolDisplayGenericsOptions.IncludeTypeParameters,
   21|         miscellaneousOptions: SymbolDisplayMiscellaneousOptions.ExpandNullable,
   22|         typeQualificationStyle: SymbolDisplayTypeQualificationStyle.NameOnly);
   23| 
   24|     /// <summary>
   25|     /// Creates the model for one generated formatter.
   26|     /// </summary>
   27|     /// <param name="compilation">The compilation that contains the formatter.</param>
   28|     /// <param name="options">The analyzer options for the compilation.</param>
   29|     /// <param name="referenceSymbols">The MessagePack reference symbols.</param>
   30|     /// <param name="reportDiagnostic">Receives diagnostics about the formatter. May be <see langword="null"/>.</param>
   31|     /// <param name="formatter">The user-declared partial formatter class.</param>
   32|     /// <param name="surrogate">The surrogate type, or <see langword="null"/> for contractless mode.</param>
   33|     /// <param name="cancellationToken">A cancellation token.</param>
   34|     /// <returns>The model, or <see langword="null"/> if the formatter cannot be generated.</returns>
   35|     internal static FullModel? Collect(
   36|         Compilation compilation,
   37|         AnalyzerOptions options,
   38|         ReferenceSymbols referenceSymbols,
   39|         Action<Diagnostic>? reportDiagnostic,
   40|         INamedTypeSymbol formatter,
   41|         INamedTypeSymbol? surrogate,
   42|         CancellationToken cancellationToken)
   43|     {
   44|         Location location = formatter.Locations.FirstOrDefault() ?? Location.None;
   45|         string formatterName = formatter.ToDisplayString(SymbolDisplayFormat.FullyQualifiedFormat);
   46| 
   47|         if (!IsPartial(formatter, cancellationToken))
   48|         {
   49|             reportDiagnostic?.Invoke(Diagnostic.Create(MsgPack00xMessagePackAnalyzer.GeneratedFormatterMustBePartial, location, formatterName));
   50|             return null;
   51|         }
   52| 
   53|         INamedTypeSymbol? openFormatterInterface = compilation.GetTypeByMetadataName($"{Constants.IMessagePackFormatterInterfaceNamespace}.{Constants.IMessagePackFormatterInterfaceName}`1");
   54|         ImmutableArray<INamedTypeSymbol> formatterInterfaces = formatter.AllInterfaces
   55|             .Where(i => i.IsGenericType && SymbolEqualityComparer.Default.Equals(i.OriginalDefinition, openFormatterInterface))
   56|             .ToImmutableArray();
   57|         if (formatterInterfaces.Length != 1)
   58|         {
   59|             reportDiagnostic?.Invoke(Diagnostic.Create(MsgPack00xMessagePackAnalyzer.GeneratedFormatterMustImplementFormatter, location, formatterName));
   60|             return null;
   61|         }
   62| 
   63|         ITypeSymbol dataTypeSymbol = formatterInterfaces[0].TypeArguments[0];
   64|         if (dataTypeSymbol is not INamedTypeSymbol { IsGenericType: false, IsAbstract: false } type
   65|             || type.TypeKind is not (TypeKind.Class or TypeKind.Struct)
   66|             || !compilation.IsSymbolAccessibleWithin(type, formatter))
   67|         {
   68|             reportDiagnostic?.Invoke(Diagnostic.Create(
   69|                 MsgPack00xMessagePackAnalyzer.GeneratedFormatterDataTypeNotSupported,
   70|                 location,
   71|                 formatterName,
   72|                 dataTypeSymbol.ToDisplayString(SymbolDisplayFormat.FullyQualifiedFormat)));
   73|             return null;
   74|         }
   75| 
   76|         bool isClass = type.TypeKind == TypeKind.Class;
   77|         if (isClass && !type.InstanceConstructors.Any(c => c.Parameters.Length == 0 && compilation.IsSymbolAccessibleWithin(c, formatter)))
   78|         {
   79|             reportDiagnostic?.Invoke(Diagnostic.Create(MsgPack00xMessagePackAnalyzer.NoDeserializingConstructor, location));
   80|             return null;
   81|         }
   82| 
   83|         bool hasCallbackReceiver = type.AllInterfaces.Any(i => SymbolEqualityComparer.Default.Equals(i, referenceSymbols.IMessagePackSerializationCallbackReceiver));
   84|         bool needsCast = hasCallbackReceiver && type.GetMembers().OfType<IMethodSymbol>().Any(m =>
   85|             m.ExplicitInterfaceImplementations.Length > 0 && (m.Name == "OnBeforeSerialize" || m.Name == "OnAfterDeserialize"));
   86| 
   87|         IReadOnlyList<MemberSerializationInfo>? members;
   88|         bool isIntKey;
   89|         if (surrogate is null)
   90|         {
   91|             members = CreateContractlessMembers(type);
   92|             isIntKey = false;
   93|         }
   94|         else
   95|         {
   96|             members = CreateSurrogateMembers(type, surrogate, referenceSymbols, reportDiagnostic, location, out isIntKey);
   97|         }
   98| 
   99|         if (members is null)
  100|         {
  101|             return null;
  102|         }
  103| 
  104|         ObjectSerializationInfo info = ObjectSerializationInfo.Create(
  105|             type,
  106|             isClass: isClass,
  107|             nestedFormatterRequired: false,
  108|             genericTypeParameters: Array.Empty<GenericTypeParameterInfo>(),
  109|             constructorParameters: Array.Empty<MemberSerializationInfo>(),
  110|             isIntKey: isIntKey,
  111|             members: members.ToArray(),
  112|             hasIMessagePackSerializationCallbackReceiver: hasCallbackReceiver,
  113|             needsCastOnAfter: needsCast,
  114|             needsCastOnBefore: needsCast,
  115|             resolverOptions: options.Generator.Resolver) with
  116|         {
  117|             Formatter = new QualifiedNamedTypeName(formatter),
  118|             IsUserDeclaredFormatter = true,
  119|         };
  120| 
  121|         return FullModel.Empty with
  122|         {
  123|             ObjectInfos = ImmutableSortedSet.Create(info),
  124|             Options = options,
  125|         };
  126|     }
  127| 
  128|     /// <summary>
  129|     /// Contractless mode: every public, read-write instance property and field is serialized under its name as a string key.
  130|     /// </summary>
  131|     private static IReadOnlyList<MemberSerializationInfo> CreateContractlessMembers(INamedTypeSymbol type)
  132|     {
  133|         List<ISymbol> targets = GetInstanceMembers(type).Where(IsPublicReadWrite).OrderBy(m => m.Name, StringComparer.Ordinal).ToList();
  134|         List<MemberSerializationInfo> members = new(targets.Count);
  135|         for (int i = 0; i < targets.Count; i++)
  136|         {
  137|             members.Add(CreateMember(targets[i], intKey: i, stringKey: targets[i].Name));
  138|         }
  139| 
  140|         return members;
  141|     }
  142| 
  143|     /// <summary>
  144|     /// Surrogate mode: keys and membership come from the surrogate's <c>[Key]</c> and <c>[IgnoreMember]</c> annotations.
  145|     /// Each keyed surrogate member is matched by name, and type, to a public read-write member of the formatted type.
  146|     /// </summary>
  147|     private static IReadOnlyList<MemberSerializationInfo>? CreateSurrogateMembers(
  148|         INamedTypeSymbol type,
  149|         INamedTypeSymbol surrogate,
  150|         ReferenceSymbols referenceSymbols,
  151|         Action<Diagnostic>? reportDiagnostic,
  152|         Location location,
  153|         out bool isIntKey)
  154|     {
  155|         isIntKey = false;
  156|         bool? keyKindIsInt = null;
  157|         HashSet<object> claimedKeys = new();
  158|         List<MemberSerializationInfo> members = new();
  159|         List<ISymbol> targetMembers = GetInstanceMembers(type);
  160| 
  161|         foreach (ISymbol surrogateMember in GetInstanceMembers(surrogate))
  162|         {
  163|             ImmutableArray<AttributeData> attributes = surrogateMember.GetAttributes();
  164|             if (attributes.Any(a => SymbolEqualityComparer.Default.Equals(a.AttributeClass, referenceSymbols.IgnoreAttribute)))
  165|             {
  166|                 continue;
  167|             }
  168| 
  169|             AttributeData? keyAttribute = attributes.FirstOrDefault(a => SymbolEqualityComparer.Default.Equals(a.AttributeClass, referenceSymbols.KeyAttribute));
  170|             object? key = keyAttribute is { ConstructorArguments.Length: 1 } ? keyAttribute.ConstructorArguments[0].Value : null;
  171|             if (key is not (int or string))
  172|             {
  173|                 reportDiagnostic?.Invoke(Diagnostic.Create(
  174|                     MsgPack00xMessagePackAnalyzer.MemberNeedsKey,
  175|                     surrogateMember.Locations.FirstOrDefault() ?? location,
  176|                     surrogate.Name,
  177|                     surrogateMember.Name));
  178|                 return null;
  179|             }
  180| 
  181|             bool memberIsIntKey = key is int;
  182|             keyKindIsInt ??= memberIsIntKey;
  183|             if (keyKindIsInt != memberIsIntKey)
  184|             {
  185|                 reportDiagnostic?.Invoke(Diagnostic.Create(MsgPack00xMessagePackAnalyzer.DoNotMixStringAndIntKeys, surrogateMember.Locations.FirstOrDefault() ?? location));
  186|                 return null;
  187|             }
  188| 
  189|             ISymbol? target = targetMembers.FirstOrDefault(m => m.Name == surrogateMember.Name);
  190|             if (target is null || !IsPublicReadWrite(target) || !SymbolEqualityComparer.Default.Equals(GetMemberType(target), GetMemberType(surrogateMember)))
  191|             {
  192|                 reportDiagnostic?.Invoke(Diagnostic.Create(
  193|                     MsgPack00xMessagePackAnalyzer.SurrogateMemberNotFound,
  194|                     surrogateMember.Locations.FirstOrDefault() ?? location,
  195|                     surrogateMember.Name,
  196|                     type.ToDisplayString(SymbolDisplayFormat.FullyQualifiedFormat)));
  197|                 return null;
  198|             }
  199| 
  200|             if (!claimedKeys.Add(key))
  201|             {
  202|                 reportDiagnostic?.Invoke(Diagnostic.Create(MsgPack00xMessagePackAnalyzer.KeysMustBeUnique, surrogateMember.Locations.FirstOrDefault() ?? location));
  203|                 return null;
  204|             }
  205| 
  206|             members.Add(key is int intKey
  207|                 ? CreateMember(target, intKey: intKey, stringKey: target.Name)
  208|                 : CreateMember(target, intKey: members.Count, stringKey: (string)key));
  209|         }
  210| 
  211|         isIntKey = keyKindIsInt ?? false;
  212|         return members;
  213|     }
  214| 
  215|     private static MemberSerializationInfo CreateMember(ISymbol target, int intKey, string stringKey)
  216|     {
  217|         ITypeSymbol memberType = GetMemberType(target);
  218|         bool isProperty = target is IPropertySymbol;
  219|         bool isInitOnly = target is IPropertySymbol { SetMethod.IsInitOnly: true };
  220|         bool isRequired = target switch
  221|         {
  222|             IPropertySymbol property => property.IsRequired,
  223|             IFieldSymbol field => field.IsRequired,
  224|             _ => false,
  225|         };
  226| 
  227|         return new MemberSerializationInfo(
  228|             IsProperty: isProperty,
  229|             IsWritable: true,
  230|             IsReadable: true,
  231|             IsInitOnly: isInitOnly,
  232|             IsRequired: isRequired,
  233|             IntKey: intKey,
  234|             StringKey: stringKey,
  235|             Name: target.Name,
  236|             Type: memberType.ToDisplayString(SymbolDisplayFormat.FullyQualifiedFormat),
  237|             ShortTypeName: memberType.ToDisplayString(BinaryWriteTypeFormat),
  238|             CustomFormatter: null)
  239|         {
  240|             // Members of the formatted type are never colliding with a base-type member of the same name here,
  241|             // because GetInstanceMembers keeps only the most derived member of each name.
  242|             DeclaringType = null,
  243|         };
  244|     }
  245| 
  246|     /// <summary>
  247|     /// Enumerates the instance fields and properties of a type and its base types, keeping only the most derived member of each name.
  248|     /// </summary>
  249|     private static List<ISymbol> GetInstanceMembers(INamedTypeSymbol type)
  250|     {
  251|         HashSet<string> seen = new(StringComparer.Ordinal);
  252|         List<ISymbol> result = new();
  253|         for (INamedTypeSymbol? current = type; current is not null && current.SpecialType != SpecialType.System_Object; current = current.BaseType)
  254|         {
  255|             foreach (ISymbol member in current.GetMembers())
  256|             {
  257|                 if (member.IsStatic || member.IsImplicitlyDeclared || member is not (IPropertySymbol or IFieldSymbol))
  258|                 {
  259|                     continue;
  260|                 }
  261| 
  262|                 if (member is IPropertySymbol { IsIndexer: true })
  263|                 {
  264|                     continue;
  265|                 }
  266| 
  267|                 if (seen.Add(member.Name))
  268|                 {
  269|                     result.Add(member);
  270|                 }
  271|             }
  272|         }
  273| 
  274|         return result;
  275|     }
  276| 
  277|     private static bool IsPublicReadWrite(ISymbol member) => member switch
  278|     {
  279|         IPropertySymbol property => property.DeclaredAccessibility == Accessibility.Public
  280|             && property.GetMethod is { DeclaredAccessibility: Accessibility.Public }
  281|             && property.SetMethod is { DeclaredAccessibility: Accessibility.Public },
  282|         IFieldSymbol field => field.DeclaredAccessibility == Accessibility.Public && !field.IsReadOnly && !field.IsConst,
  283|         _ => false,
  284|     };
  285| 
  286|     private static ITypeSymbol GetMemberType(ISymbol member) => member switch
  287|     {
  288|         IPropertySymbol property => property.Type,
  289|         IFieldSymbol field => field.Type,
  290|         _ => throw new ArgumentOutOfRangeException(nameof(member)),
  291|     };
  292| 
  293|     private static bool IsPartial(INamedTypeSymbol symbol, CancellationToken cancellationToken)
  294|     {
  295|         return symbol.DeclaringSyntaxReferences
  296|             .Select(r => r.GetSyntax(cancellationToken))
  297|             .OfType<ClassDeclarationSyntax>()
  298|             .Any(c => c.Modifiers.Any(SyntaxKind.PartialKeyword));
  299|     }
  300| }
```

### src/MessagePack.SourceGenerator/CodeAnalysis/GeneratedFormatterRequest.cs at head (083afd99), full file
```
    1| // Copyright (c) All contributors. All rights reserved.
    2| // Licensed under the MIT license. See LICENSE file in the project root for full license information.
    3| 
    4| using Microsoft.CodeAnalysis;
    5| 
    6| namespace MessagePack.SourceGenerator.CodeAnalysis;
    7| 
    8| /// <summary>
    9| /// A partial formatter class marked with <c>[GeneratedMessagePackFormatter]</c>, and the optional surrogate type it names.
   10| /// </summary>
   11| /// <param name="Formatter">The user-declared partial formatter class.</param>
   12| /// <param name="Surrogate">The surrogate type named by <c>SurrogateType</c>, or <see langword="null"/> for contractless mode.</param>
   13| public sealed record GeneratedFormatterRequest(INamedTypeSymbol Formatter, INamedTypeSymbol? Surrogate);
```

### src/MessagePack.SourceGenerator/CodeAnalysis/ObjectSerializationInfo.cs at head (083afd99), around the changed lines
```
    1| ﻿// Copyright (c) All contributors. All rights reserved.
    2| // Licensed under the MIT license. See LICENSE file in the project root for full license information.
    3| 
    4| using System.Text;
    5| using Microsoft.CodeAnalysis;
    6| 
    7| namespace MessagePack.SourceGenerator.CodeAnalysis;
    8| 
    9| public record ObjectSerializationInfo : ResolverRegisterInfo
   10| {
   11|     public required bool IsClass { get; init; }
   12| 
   13|     /// <summary>
   14|     /// Gets a value indicating whether the formatter is a user-declared <c>partial</c> class marked with
   15|     /// <c>[GeneratedMessagePackFormatter]</c>, into which the generator writes the formatter body.
   16|     /// </summary>
   17|     public bool IsUserDeclaredFormatter { get; init; }
   18| 
   19|     public required GenericTypeParameterInfo[] GenericTypeParameters { get; init; }
   20| 
   21|     public required MemberSerializationInfo[] ConstructorParameters { get; init; }
   22| 
   23|     /// <summary>
   24|     /// Gets the members that are either init-only properties or required (and therefore must appear in an object initializer).
   25|     /// </summary>
   26|     public required MemberSerializationInfo[] InitMembers { get; init; }
   27| 
   28|     public bool MustDeserializeFieldsFirst => this.ConstructorParameters.Length > 0 || this.InitMembers.Length > 0;
   29| 
   30|     public required bool IsIntKey { get; init; }
   31| 
   32|     public required MemberSerializationInfo[] Members { get; init; }
   33| 
   34|     public required bool HasIMessagePackSerializationCallbackReceiver { get; init; }
   35| 
   36|     public required bool NeedsCastOnAfter { get; init; }
   37| 
   38|     public required bool NeedsCastOnBefore { get; init; }
   39| 
   40|     public bool IsStringKey => !this.IsIntKey;
   41| 
   42|     public int WriteCount
   43|     {
   44|         get
   45|         {
   46|             if (this.IsStringKey)
   47|             {
   48|                 return this.Members.Count(x => x.IsReadable);
   49|             }
   50|             else
   51|             {
  ... lines 52-134 not shown ...
  135|                 // However the C# language does not provide a means to do this, so we always assign them.
  136|                 // https://github.com/dotnet/csharplang/issues/6117
  137|                 builder.Append(this.InitMembers[i].Name);
  138|                 builder.Append(" = ");
  139|                 builder.Append(this.InitMembers[i].LocalVariableName);
  140|             }
  141| 
  142|             builder.Append(" }");
  143|         }
  144| 
  145|         return builder.ToString();
  146|     }
  147| 
  148|     public virtual bool Equals(ObjectSerializationInfo? other)
  149|     {
  150|         if (other == null)
  151|         {
  152|             return false;
  153|         }
  154| 
  155|         if (ReferenceEquals(this, other))
  156|         {
  157|             return true;
  158|         }
  159| 
  160|         if (this.GetType() != other.GetType())
  161|         {
  162|             return false;
  163|         }
  164| 
  165|         // Compare all the properties by value
  166|         return base.Equals(other)
  167|             && IsClass == other.IsClass
  168|             && IsUserDeclaredFormatter == other.IsUserDeclaredFormatter
  169|             && GenericTypeParameters.SequenceEqual(other.GenericTypeParameters)
  170|             && ConstructorParameters.SequenceEqual(other.ConstructorParameters)
  171|             && IsIntKey == other.IsIntKey
  172|             && Members.SequenceEqual(other.Members)
  173|             && HasIMessagePackSerializationCallbackReceiver == other.HasIMessagePackSerializationCallbackReceiver
  174|             && NeedsCastOnAfter == other.NeedsCastOnAfter
  175|             && NeedsCastOnBefore == other.NeedsCastOnBefore;
  176|     }
  177| 
  178|     public override int GetHashCode()
  179|     {
  180|         int hash = base.GetHashCode();
  181| 
  182|         hash = Hash(hash, this.IsClass ? 1 : 2);
  183|         hash = Hash(hash, this.GenericTypeParameters.Length);
  184| 
  185|         return hash;
  186| 
  187|         static int Hash(int hashCode, int value)
  188|         {
  189|             return (hashCode * 31) + value;
  190|         }
  191|     }
  192| }
```

### src/MessagePack.SourceGenerator/GeneratorUtilities.cs at head (083afd99), full file
```
    1| ﻿// Copyright (c) All contributors. All rights reserved.
    2| // Licensed under the MIT license. See LICENSE file in the project root for full license information.
    3| 
    4| using System;
    5| using System.Collections.Generic;
    6| using System.Collections.Immutable;
    7| using System.Text;
    8| using Microsoft.CodeAnalysis;
    9| using Microsoft.CodeAnalysis.CSharp.Syntax;
   10| using static MessagePack.SourceGenerator.Constants;
   11| 
   12| namespace MessagePack.SourceGenerator;
   13| 
   14| internal static class GeneratorUtilities
   15| {
   16|     internal static IncrementalValueProvider<AnalyzerOptions> GetAnalyzerOption(IncrementalGeneratorInitializationContext context)
   17|     {
   18|         // Search for [assembly: MessagePackKnownFormatter(typeof(SomeFormatter))]
   19|         var customFormatters = context.SyntaxProvider.ForAttributeWithMetadataName(
   20|             $"{AttributeNamespace}.{MessagePackKnownFormatterAttributeName}",
   21|             predicate: static (node, ct) => true,
   22|             transform: static (context, ct) => AnalyzerUtilities.ParseKnownFormatterAttribute(context.Attributes, ct)).Collect();
   23| 
   24|         // Search for [assembly: MessagePackAssumedFormattable(typeof(SomeCustomType))]
   25|         var customFormattedTypes = context.SyntaxProvider.ForAttributeWithMetadataName(
   26|             $"{AttributeNamespace}.{MessagePackAssumedFormattableAttributeName}",
   27|             predicate: static (node, ct) => true,
   28|             transform: static (context, ct) => AnalyzerUtilities.ParseAssumedFormattableAttribute(context.Attributes, ct)).SelectMany((a, ct) => a).Collect();
   29| 
   30|         // Search for all implementations of IMessagePackFormatter<T> in the compilation.
   31|         var customFormattersInThisCompilation = context.SyntaxProvider.CreateSyntaxProvider(
   32|             predicate: static (node, ct) => node is ClassDeclarationSyntax { BaseList.Types.Count: > 0 },
   33|             transform: (ctxt, ct) =>
   34|             {
   35|                 // Formatters marked with [GeneratedMessagePackFormatter] are generated by the source generator
   36|                 // and are registered as ObjectSerializationInfo, so they must not also be registered as hand-written formatters.
   37|                 return ctxt.SemanticModel.GetDeclaredSymbol(ctxt.Node, ct) is INamedTypeSymbol symbol
   38|                     && !symbol.GetAttributes().Any(a => a.AttributeClass?.ToDisplayString() == $"{AttributeNamespace}.{GeneratedMessagePackFormatterAttributeName}")
   39|                     && FormatterDescriptor.TryCreate(symbol, out FormatterDescriptor? formatter)
   40|                     && !formatter.ExcludeFromSourceGeneratedResolver
   41|                     ? formatter
   42|                     : null;
   43|             }).Collect();
   44| 
   45|         // Search for a [GeneratedMessagePackResolver] attribute (presumably on a partial class).
   46|         var resolverOptions = context.SyntaxProvider.ForAttributeWithMetadataName(
   47|             $"{AttributeNamespace}.{GeneratedMessagePackResolverAttributeName}",
   48|             predicate: static (node, ct) => true,
   49|             transform: static (context, ct) => AnalyzerUtilities.ParseGeneratorAttribute(context.Attributes, context.TargetSymbol, ct)).Collect().Select((a, ct) => a.SingleOrDefault(ao => ao is not null));
   50| 
   51|         // Assembly an aggregating AnalyzerOptions object from the attributes and interface implementations that we've found.
   52|         var options = resolverOptions.Combine(customFormattedTypes).Combine(customFormatters).Combine(customFormattersInThisCompilation)
   53|             .Select(static (input, ct) =>
   54|             {
   55|                 AnalyzerOptions? options = input.Left.Left.Left ?? new() { IsGeneratingSource = true };
   56|                 ImmutableArray<FormatterDescriptor?> formatterImplementations = input.Right;
   57| 
   58|                 ImmutableArray<FormattableType> formattableTypes = input.Left.Left.Right;
   59|                 ImmutableHashSet<FormatterDescriptor> formatterTypes = input.Left.Right.Aggregate(
   60|                     ImmutableHashSet<FormatterDescriptor>.Empty,
   61|                     (first, second) => first.Union(second));
   62| 
   63|                 // Merge the formatters discovered through attributes (which need only reference formatters from other assemblies),
   64|                 // with formatters discovered in the project being compiled.
   65|                 formatterTypes = formatterImplementations.Aggregate(
   66|                     formatterTypes,
   67|                     (first, second) => second is not null ? first.Add(second) : first);
   68| 
   69|                 options = options.WithFormatterTypes(formattableTypes, formatterTypes);
   70| 
   71|                 return options;
   72|             });
   73| 
   74|         return options;
   75|     }
   76| }
```

### src/MessagePack.SourceGenerator/MessagePackGenerator.cs at head (083afd99), around the changed lines
```
    1| ﻿// Copyright (c) All contributors. All rights reserved.
    2| // Licensed under the MIT license. See LICENSE file in the project root for full license information.
    3| 
    4| using System.Collections.Immutable;
    5| using Microsoft.CodeAnalysis;
    6| using Microsoft.CodeAnalysis.CSharp.Syntax;
    7| using static MessagePack.SourceGenerator.Constants;
    8| using AnalyzerOptions = MessagePack.SourceGenerator.CodeAnalysis.AnalyzerOptions;
    9| 
   10| namespace MessagePack.SourceGenerator;
   11| 
   12| [Generator(LanguageNames.CSharp)]
   13| public partial class MessagePackGenerator : IIncrementalGenerator
   14| {
   15|     public void Initialize(IncrementalGeneratorInitializationContext context)
   16|     {
   17|         IncrementalValueProvider<AnalyzerOptions> options = GeneratorUtilities.GetAnalyzerOption(context);
   18| 
   19|         var messagePackObjectTypes = context.SyntaxProvider.ForAttributeWithMetadataName(
   20|             $"{AttributeNamespace}.{MessagePackObjectAttributeName}",
   21|             predicate: static (node, _) => node is TypeDeclarationSyntax,
   22|             transform: static (context, _) => (ITypeSymbol)context.TargetSymbol);
   23| 
   24|         var unionTypes = context.SyntaxProvider.ForAttributeWithMetadataName(
   25|             $"{AttributeNamespace}.{MessagePackUnionAttributeName}",
   26|             predicate: static (node, _) => node is InterfaceDeclarationSyntax,
   27|             transform: static (context, _) => (ITypeSymbol)context.TargetSymbol);
   28| 
   29|         var generatedFormatters = context.SyntaxProvider.ForAttributeWithMetadataName(
   30|             $"{AttributeNamespace}.{GeneratedMessagePackFormatterAttributeName}",
   31|             predicate: static (node, _) => node is ClassDeclarationSyntax,
   32|             transform: static (context, _) => new GeneratedFormatterRequest(
   33|                 (INamedTypeSymbol)context.TargetSymbol,
   34|                 context.Attributes[0].NamedArguments.FirstOrDefault(kvp => kvp.Key == GeneratedMessagePackFormatterSurrogatePropertyName).Value.Value as INamedTypeSymbol));
   35| 
   36|         var combined =
   37|             messagePackObjectTypes.Collect().Combine(unionTypes.Collect()).Combine(generatedFormatters.Collect());
   38| 
   39|         var source = combined
   40|             .Combine(context.CompilationProvider)
   41|             .Combine(options)
   42|             .Select(static (s, ct) =>
   43|             {
   44|                 AnalyzerOptions options = s.Right;
   45| 
   46|                 if (!ReferenceSymbols.TryCreate(s.Left.Right, out ReferenceSymbols? referenceSymbols) || referenceSymbols.MessagePackFormatter is null)
   47|                 {
   48|                     return default;
   49|                 }
   50| 
   51|                 List<FullModel> modelPerType = new();
   52|                 void Collect(ITypeSymbol typeSymbol)
   53|                 {
   54|                     if (TypeCollector.Collect(s.Left.Right, options, referenceSymbols, reportAnalyzerDiagnostic: null, typeSymbol, ct) is FullModel model)
   55|                     {
   56|                         modelPerType.Add(model);
   57|                     }
   58|                 }
   59| 
   60|                 foreach (var typeSymbol in s.Left.Left.Left.Left)
   61|                 {
   62|                     Collect(typeSymbol);
   63|                 }
   64| 
   65|                 foreach (var typeSymbol in s.Left.Left.Left.Right)
   66|                 {
   67|                     Collect(typeSymbol);
   68|                 }
   69| 
   70|                 foreach (GeneratedFormatterRequest request in s.Left.Left.Right)
   71|                 {
   72|                     if (GeneratedFormatterCollector.Collect(s.Left.Right, options, referenceSymbols, reportDiagnostic: null, request.Formatter, request.Surrogate, ct) is FullModel generatedModel)
   73|                     {
   74|                         modelPerType.Add(generatedModel);
   75|                     }
   76|                 }
   77| 
   78|                 if (!options.KnownFormatters.IsEmpty)
   79|                 {
   80|                     var customFormatterInfos = FullModel.Empty.CustomFormatterInfos.Union(
   81|                         from known in options.KnownFormatters
   82|                         where known.InaccessibleDescriptor is null
   83|                         from formatted in known.FormattableTypes
   84|                         where !options.GetCollidingFormatterDataTypes(known.Name).Contains(formatted) // skip formatters with colliding types to avoid non-deterministic code generation
   85|                         select new CustomFormatterRegisterInfo
   86|                         {
   87|                             Formatter = known.Name,
   88|                             DataType = formatted.Name,
   89|                             FormattableDataType = formatted,
   90|                             CustomFormatter = known,
   91|                         });
   92|                     modelPerType.Add(FullModel.Empty with { CustomFormatterInfos = customFormatterInfos, Options = options });
   93|                 }
   94| 
   95|                 return FullModel.Combine(modelPerType.ToImmutableArray());
   96|             });
   97| 
   98|         var splittedSources = source
   99|             .SelectMany(static (s, ct) =>
  100|             {
  101|                 if (s is null)
  102|                 {
  103|                     return ImmutableArray<FullModel>.Empty;
  104|                 }
  105| 
  106|                 var models = new List<FullModel>();
  107|                 models.AddRange(s.ArrayFormatterInfos.Select(i => FullModel.Empty with { Options = s.Options, ArrayFormatterInfos = ImmutableSortedSet.Create(i) }));
  108|                 models.AddRange(s.ObjectInfos.Select(i => FullModel.Empty with { Options = s.Options, ObjectInfos = ImmutableSortedSet.Create(i) }));
  109|                 models.AddRange(s.EnumInfos.Select(i => FullModel.Empty with { Options = s.Options, EnumInfos = ImmutableSortedSet.Create(i) }));
  110|                 models.AddRange(s.UnionInfos.Select(i => FullModel.Empty with { Options = s.Options, UnionInfos = ImmutableSortedSet.Create(i) }));
  111| 
  112|                 return models.ToImmutableArray();
  113|             });
  114| 
  115|         // Diagnostics for [GeneratedMessagePackFormatter] classes are reported separately from the models,
  116|         // so that a rejected formatter produces a diagnostic and no partial output.
  117|         var generatedFormatterDiagnostics = generatedFormatters
  118|             .Combine(context.CompilationProvider)
  119|             .Combine(options)
  120|             .SelectMany(static (s, ct) =>
  121|             {
  122|                 List<Diagnostic> diagnostics = new();
  123|                 if (ReferenceSymbols.TryCreate(s.Left.Right, out ReferenceSymbols? referenceSymbols))
  124|                 {
  125|                     GeneratedFormatterCollector.Collect(s.Left.Right, s.Right, referenceSymbols, diagnostics.Add, s.Left.Left.Formatter, s.Left.Left.Surrogate, ct);
  126|                 }
  127| 
  128|                 return diagnostics.ToImmutableArray();
  129|             });
  130| 
  131|         context.RegisterSourceOutput(generatedFormatterDiagnostics, static (context, diagnostic) => context.ReportDiagnostic(diagnostic));
  132| 
  133|         context.RegisterSourceOutput(source, static (context, source) =>
  134|         {
  135|             if (source is { Options.IsGeneratingSource: true })
  136|             {
  137|                 GenerateResolver(new GeneratorContext(context), source);
  138|             }
  139|         });
  140| 
  141|         context.RegisterSourceOutput(splittedSources, static (context, source) =>
  142|         {
  143|             if (source is { Options.IsGeneratingSource: true })
  144|             {
  145|                 Generate(new GeneratorContext(context), source);
  146|             }
  147|         });
  148|     }
  149| 
  150|     private class Comparer : IEqualityComparer<(TypeDeclarationSyntax, Compilation)>
  151|     {
  152|         public static readonly Comparer Instance = new Comparer();
  153| 
  154|         public bool Equals((TypeDeclarationSyntax, Compilation) x, (TypeDeclarationSyntax, Compilation) y)
  155|         {
  156|             return x.Item1.Equals(y.Item1);
  157|         }
  158| 
  159|         public int GetHashCode((TypeDeclarationSyntax, Compilation) obj)
  160|         {
  161|             return obj.Item1.GetHashCode();
  162|         }
  163|     }
  164| 
  165|     private class GeneratorContext : IGeneratorContext
  ... lines 166-180 not shown ...
```

### src/MessagePack.SourceGenerator/Transforms/FormatterTemplate.tt at head (083afd99), around the changed lines
```
    1| ﻿<#@ template debug="false" hostspecific="false" linePragmas="false" language="C#" #>
    2| <#@ assembly name="System.Core" #>
    3| <#@ import namespace="System.Linq" #>
    4| <#@ import namespace="System.Text" #>
    5| <#@ import namespace="System.Collections.Generic" #>
    6| 
    7| #pragma warning disable CS8669 // We may leak nullable annotations into generated code.
    8| 
    9| using MsgPack = global::MessagePack;
   10| 
   11| <# using (this.EmitNestingTypesAndNamespaces(this.Write)) { #>
   12| 
   13| <#  bool isFormatterResolverNecessary = GeneratorUtilities.ShouldUseFormatterResolver(Info.Members);#>
   14| 	<#= Info.IsUserDeclaredFormatter ? "partial class" : "internal sealed class" #> <#= Info.Formatter.GetQualifiedName(Qualifiers.None) #> : MsgPack::Formatters.IMessagePackFormatter<<#= Info.DataType.GetQualifiedName(genericStyle: GenericParameterStyle.Identifiers) #>>
   15| <# TransformUtilities.EmitTypeConstraints(Info.Formatter, this.Write); #>
   16| 	{
   17| <# foreach (var item in Info.Members) { #>
   18| <# if (item.CustomFormatter != null) { #>
   19| 		private readonly <#= item.CustomFormatter.InstanceTypeName.GetQualifiedName(genericStyle: GenericParameterStyle.Arguments) #> __<#= item.Name #>CustomFormatter__ = <#= item.CustomFormatter.InstanceExpression #>;
   20| <# } #>
   21| <# } #>
   22| 
   23| 		public void Serialize(ref MsgPack::MessagePackWriter writer, <#= Info.DataType.GetQualifiedName(genericStyle: GenericParameterStyle.Identifiers) #> value, MsgPack::MessagePackSerializerOptions options)
   24| 		{
   25| <# if (Info.IsClass) { #>
   26| 			if (value == null)
   27| 			{
   28| 				writer.WriteNil();
   29| 				return;
   30| 			}
   31| 
   32| <# }
   33| 
   34|   if (isFormatterResolverNecessary) { #>
   35| 			MsgPack::IFormatterResolver formatterResolver = options.Resolver;
   36| <# }
   37| 
   38|  if (Info.HasIMessagePackSerializationCallbackReceiver) {
   39|   if (Info.NeedsCastOnBefore) { #>
   40| 			((MsgPack::IMessagePackSerializationCallbackReceiver)value).OnBeforeSerialize();
   41| <# } else { #>
   42| 			value.OnBeforeSerialize();
   43| <# } #>
   44| <# } #>
   45| 			writer.WriteArrayHeader(<#= Info.MaxKey + 1 #>);
   46| <# for (var i = 0; i <= Info.MaxKey; i++) {
   47|   var member = Info.GetMember(i);
  ... lines 48-141 not shown ...
```

### src/MessagePack.SourceGenerator/Transforms/StringKey/StringKeyFormatterTemplate.tt at head (083afd99), around the changed lines
```
    1| ﻿<#@ template debug="false" hostspecific="false" linePragmas="false" language="C#" #>
    2| <#@ assembly name="System.Core" #>
    3| <#@ import namespace="System" #>
    4| <#@ import namespace="System.Linq" #>
    5| <#@ import namespace="System.Collections.Generic" #>
    6| <#@ import namespace="MessagePack.SourceGenerator.CodeAnalysis" #>
    7| 
    8| using MsgPack = global::MessagePack;
    9| 
   10| <# var list = new List<ValueTuple<MemberSerializationInfo, byte[]>>();
   11| 	foreach (var member in Info.Members) {
   12| 		var binary = EmbedStringHelper.Utf8.GetBytes(member.StringKey);
   13| 		list.Add(new ValueTuple<MemberSerializationInfo, byte[]>(member, binary));
   14| 	}
   15| 
   16| 	bool isFormatterResolverNecessary = GeneratorUtilities.ShouldUseFormatterResolver(Info.Members); #>
   17| <# using (this.EmitNestingTypesAndNamespaces(this.Write)) { #>
   18| 	<#= Info.IsUserDeclaredFormatter ? "partial class" : "internal sealed class" #> <#= Info.Formatter.GetQualifiedName(Qualifiers.None) #> : global::MessagePack.Formatters.IMessagePackFormatter<<#= Info.DataType.GetQualifiedName() #>>
   19| <# TransformUtilities.EmitTypeConstraints(Info.Formatter, this.Write); #>
   20| 	{
   21| <# foreach (var item in Info.Members) { #>
   22| <# if (item.CustomFormatter != null) { #>
   23| 		private readonly <#= item.CustomFormatter.Name.GetQualifiedName() #> __<#= item.Name #>CustomFormatter__ = <#= item.CustomFormatter.InstanceExpression #>;
   24| <# } #>
   25| <# } #>
   26| <# for (var i = 0; i < list.Count; i++) {
   27| 		var member = list[i].Item1;
   28| 		var binary = list[i].Item2; #>
   29| 		// <#= member.StringKey #>
   30| 		private static global::System.ReadOnlySpan<byte> GetSpan_<#= member.UniqueIdentifier #>() => <#= EmbedStringHelper.ToByteArrayString(binary) #>;
   31| <# } #>
   32| <# if (list.Count != 0) { #>
   33| 
   34| <# } #>
   35| 		public void Serialize(ref global::MessagePack.MessagePackWriter writer, <#= Info.DataType.GetQualifiedName() #> value, global::MessagePack.MessagePackSerializerOptions options)
   36| 		{
   37| <# if (Info.IsClass) { #>
   38| 			if (value is null)
   39| 			{
   40| 				writer.WriteNil();
   41| 				return;
   42| 			}
   43| 
   44| <# }
   45| 
   46| 	if (isFormatterResolverNecessary) { #>
   47| 			var formatterResolver = options.Resolver;
   48| <# }
   49| 
   50| 	if (Info.HasIMessagePackSerializationCallbackReceiver) {
   51| 		if (Info.NeedsCastOnBefore) { #>
  ... lines 52-136 not shown ...
```

### src/MessagePack.SourceGenerator/Utils/Constants.cs at head (083afd99), full file
```
    1| ﻿// Copyright (c) All contributors. All rights reserved.
    2| // Licensed under the MIT license. See LICENSE file in the project root for full license information.
    3| 
    4| namespace MessagePack.SourceGenerator;
    5| 
    6| internal static class Constants
    7| {
    8|     internal const string AttributeNamespace = "MessagePack";
    9|     internal const string CompositeResolverAttributeName = "CompositeResolverAttribute";
   10|     internal const string CompositeResolverAttributeIncludeLocalFormattersPropertyName = "IncludeLocalFormatters";
   11|     internal const string GeneratedMessagePackResolverAttributeName = "GeneratedMessagePackResolverAttribute";
   12|     internal const string MessagePackKnownFormatterAttributeName = "MessagePackKnownFormatterAttribute";
   13|     internal const string ExcludeFormatterFromSourceGeneratedResolverAttributeName = "ExcludeFormatterFromSourceGeneratedResolverAttribute";
   14|     internal const string MessagePackAssumedFormattableAttributeName = "MessagePackAssumedFormattableAttribute";
   15|     internal const string MessagePackObjectAttributeName = "MessagePackObjectAttribute";
   16|     internal const string MessagePackUnionAttributeName = "UnionAttribute";
   17|     internal const string GeneratedMessagePackFormatterAttributeName = "GeneratedMessagePackFormatterAttribute";
   18|     internal const string GeneratedMessagePackFormatterSurrogatePropertyName = "SurrogateType";
   19|     internal const string SuppressSourceGenerationPropertyName = "SuppressSourceGeneration";
   20|     internal const string AllowPrivatePropertyName = "AllowPrivate";
   21| 
   22|     internal const string IMessagePackFormatterInterfaceNamespace = "MessagePack.Formatters";
   23|     internal const string IMessagePackFormatterInterfaceName = "IMessagePackFormatter";
   24| 
   25|     internal const string IFormatterResolverInterfaceName = "IFormatterResolver";
   26| }
```

### tests/MessagePack.SourceGenerator.ExecutionTests/GeneratedFormatterForExternalTypes.cs at head (083afd99), full file
```
    1| // Copyright (c) All contributors. All rights reserved.
    2| // Licensed under the MIT license. See LICENSE file in the project root for full license information.
    3| 
    4| using ExternalTypes.Library;
    5| using MessagePack.Formatters;
    6| 
    7| // Formatter bodies for types from ExternalTypes that carry no MessagePack attributes.
    8| // The source generator writes the members of each partial class (https://github.com/MessagePack-CSharp/MessagePack-CSharp/issues/2129).
    9| [GeneratedMessagePackFormatter]
   10| public partial class ExternalPersonFormatter : IMessagePackFormatter<ExternalPerson>
   11| {
   12| }
   13| 
   14| [GeneratedMessagePackFormatter]
   15| public partial class ExternalPointFormatter : IMessagePackFormatter<ExternalPoint>
   16| {
   17| }
   18| 
   19| [GeneratedMessagePackFormatter(SurrogateType = typeof(ExternalWidgetSurrogate))]
   20| public partial class ExternalWidgetFormatter : IMessagePackFormatter<ExternalWidget>
   21| {
   22| }
   23| 
   24| /// <summary>
   25| /// Describes the wire contract of <see cref="ExternalWidget"/>. It is only read at compile time and is never instantiated.
   26| /// </summary>
   27| public class ExternalWidgetSurrogate
   28| {
   29|     [Key(3)]
   30|     public int Id { get; set; }
   31| 
   32|     [Key(7)]
   33|     public string Name { get; set; } = string.Empty;
   34| 
   35|     [IgnoreMember]
   36|     public int Internal { get; set; }
   37| }
   38| 
   39| /// <summary>
   40| /// A serializable type that refers to <see cref="ExternalPerson"/>, whose formatter is generated by <see cref="ExternalPersonFormatter"/>.
   41| /// </summary>
   42| [MessagePackObject]
   43| public class ContainsExternalPerson
   44| {
   45|     [Key(0)]
   46|     public ExternalPerson Person { get; set; }
   47| 
   48|     [Key(1)]
   49|     public ExternalWidget Widget { get; set; }
   50| }
```

### tests/MessagePack.SourceGenerator.ExecutionTests/GeneratedFormatterForExternalTypesTests.cs at head (083afd99), full file
```
    1| // Copyright (c) All contributors. All rights reserved.
    2| // Licensed under the MIT license. See LICENSE file in the project root for full license information.
    3| 
    4| using ExternalTypes.Library;
    5| 
    6| public class GeneratedFormatterForExternalTypesTests
    7| {
    8|     private static readonly MessagePackSerializerOptions Options = MessagePackSerializerOptions.Standard
    9|         .WithResolver(CompositeResolver.Create(GeneratedMessagePackResolver.Instance, StandardResolver.Instance));
   10| 
   11|     [Fact]
   12|     public void ContractlessClassRoundTrips()
   13|     {
   14|         var person = new ExternalPerson { Id = 7, Label = "seven" };
   15| 
   16|         byte[] bytes = MessagePackSerializer.Serialize(person, Options);
   17|         ExternalPerson result = MessagePackSerializer.Deserialize<ExternalPerson>(bytes, Options);
   18| 
   19|         Assert.Equal(7, result.Id);
   20|         Assert.Equal("seven", result.Label);
   21|     }
   22| 
   23|     [Fact]
   24|     public void ContractlessClassUsesStringKeysForPublicReadWriteMembers()
   25|     {
   26|         byte[] bytes = MessagePackSerializer.Serialize(new ExternalPerson { Id = 1, Label = "x" }, Options);
   27| 
   28|         // A fixmap with two entries: Id and Label. The read-only Doubled member is not serialized.
   29|         Assert.Equal(0x82, bytes[0]);
   30|         string json = MessagePackSerializer.ConvertToJson(bytes, Options);
   31|         Assert.Contains("\"Id\":1", json);
   32|         Assert.Contains("\"Label\":\"x\"", json);
   33|         Assert.DoesNotContain("Doubled", json);
   34|     }
   35| 
   36|     [Fact]
   37|     public void ContractlessClassNullRoundTrips()
   38|     {
   39|         byte[] bytes = MessagePackSerializer.Serialize(default(ExternalPerson), Options);
   40|         Assert.Null(MessagePackSerializer.Deserialize<ExternalPerson>(bytes, Options));
   41|     }
   42| 
   43|     [Fact]
   44|     public void ContractlessStructRoundTrips()
   45|     {
   46|         var point = new ExternalPoint { X = 3, Y = -4 };
   47| 
   48|         ExternalPoint result = MessagePackSerializer.Deserialize<ExternalPoint>(MessagePackSerializer.Serialize(point, Options), Options);
   49| 
   50|         Assert.Equal(3, result.X);
   51|         Assert.Equal(-4, result.Y);
   52|     }
   53| 
   54|     [Fact]
   55|     public void SurrogateControlsKeysAndMembership()
   56|     {
   57|         var widget = new ExternalWidget { Id = 1, Name = "w", Internal = 99 };
   58| 
   59|         byte[] bytes = MessagePackSerializer.Serialize(widget, Options);
   60| 
   61|         // The surrogate uses integer keys 3 and 7, so the array has MaxKey + 1 = 8 slots.
   62|         var reader = new MessagePackReader(bytes);
   63|         Assert.Equal(8, reader.ReadArrayHeader());
   64| 
   65|         ExternalWidget result = MessagePackSerializer.Deserialize<ExternalWidget>(bytes, Options);
   66|         Assert.Equal(1, result.Id);
   67|         Assert.Equal("w", result.Name);
   68|         Assert.Equal(0, result.Internal);
   69|     }
   70| 
   71|     [Fact]
   72|     public void MessagePackObjectCanContainExternalTypes()
   73|     {
   74|         var value = new ContainsExternalPerson
   75|         {
   76|             Person = new ExternalPerson { Id = 5, Label = "five" },
   77|             Widget = new ExternalWidget { Id = 6, Name = "six" },
   78|         };
   79| 
   80|         ContainsExternalPerson result = MessagePackSerializer.Deserialize<ContainsExternalPerson>(MessagePackSerializer.Serialize(value, Options), Options);
   81| 
   82|         Assert.Equal(5, result.Person.Id);
   83|         Assert.Equal("five", result.Person.Label);
   84|         Assert.Equal(6, result.Widget.Id);
   85|         Assert.Equal("six", result.Widget.Name);
   86|     }
   87| 
   88|     [Fact]
   89|     public void GeneratedFormattersAreRegisteredInGeneratedResolver()
   90|     {
   91|         Assert.IsType<ExternalPersonFormatter>(GeneratedMessagePackResolver.Instance.GetFormatter<ExternalPerson>());
   92|         Assert.IsType<ExternalPointFormatter>(GeneratedMessagePackResolver.Instance.GetFormatter<ExternalPoint>());
   93|         Assert.IsType<ExternalWidgetFormatter>(GeneratedMessagePackResolver.Instance.GetFormatter<ExternalWidget>());
   94|     }
   95| }
```

### tests/MessagePack.SourceGenerator.ExternalTypes/ExternalPerson.cs at head (083afd99), full file
```
    1| // Copyright (c) All contributors. All rights reserved.
    2| // Licensed under the MIT license. See LICENSE file in the project root for full license information.
    3| 
    4| namespace ExternalTypes.Library;
    5| 
    6| /// <summary>A type with no serialization attributes. Its public read-write members are serialized in contractless mode.</summary>
    7| public class ExternalPerson
    8| {
    9|     public int Id { get; set; }
   10| 
   11|     public string Label { get; set; }
   12| 
   13|     /// <summary>Gets a value derived from <see cref="Id"/>. Contractless mode skips it because it cannot be deserialized.</summary>
   14|     public int Doubled => this.Id * 2;
   15| }
```

### tests/MessagePack.SourceGenerator.ExternalTypes/ExternalPoint.cs at head (083afd99), full file
```
    1| // Copyright (c) All contributors. All rights reserved.
    2| // Licensed under the MIT license. See LICENSE file in the project root for full license information.
    3| 
    4| namespace ExternalTypes.Library;
    5| 
    6| /// <summary>A struct with no serialization attributes.</summary>
    7| public struct ExternalPoint
    8| {
    9|     public int X { get; set; }
   10| 
   11|     public int Y { get; set; }
   12| }
```

### tests/MessagePack.SourceGenerator.ExternalTypes/ExternalWidget.cs at head (083afd99), full file
```
    1| // Copyright (c) All contributors. All rights reserved.
    2| // Licensed under the MIT license. See LICENSE file in the project root for full license information.
    3| 
    4| namespace ExternalTypes.Library;
    5| 
    6| /// <summary>A type with no serialization attributes whose wire contract is described by a surrogate type in the consuming assembly.</summary>
    7| public class ExternalWidget
    8| {
    9|     public int Id { get; set; }
   10| 
   11|     public string Name { get; set; }
   12| 
   13|     /// <summary>Gets or sets a value that is not part of the surrogate's contract, so it is not serialized.</summary>
   14|     public int Internal { get; set; }
   15| }
```

### tests/MessagePack.SourceGenerator.Tests/GeneratedMessagePackFormatterTests.cs at head (083afd99), full file
```
    1| // Copyright (c) All contributors. All rights reserved.
    2| // Licensed under the MIT license. See LICENSE file in the project root for full license information.
    3| 
    4| using MessagePack.SourceGenerator.Tests;
    5| using Microsoft.CodeAnalysis.Testing;
    6| using VerifyCS = CSharpSourceGeneratorVerifier<MessagePack.SourceGenerator.MessagePackGenerator>;
    7| 
    8| /// <summary>
    9| /// Tests for <c>[GeneratedMessagePackFormatter]</c>, which lets the generator write a formatter for a type from another assembly (https://github.com/MessagePack-CSharp/MessagePack-CSharp/issues/2129).
   10| /// </summary>
   11| public class GeneratedMessagePackFormatterTests
   12| {
   13|     private readonly ITestOutputHelper testOutputHelper;
   14| 
   15|     public GeneratedMessagePackFormatterTests(ITestOutputHelper testOutputHelper)
   16|     {
   17|         this.testOutputHelper = testOutputHelper;
   18|     }
   19| 
   20|     // Formatter members are written by hand in the diagnostic tests, so the compiler accepts the source
   21|     // even when the generator declines to write them.
   22|     private const string Members = """
   23|             public void Serialize(ref MessagePackWriter writer, MyType value, MessagePackSerializerOptions options) => throw new System.NotImplementedException();
   24| 
   25|             public MyType Deserialize(ref MessagePackReader reader, MessagePackSerializerOptions options) => throw new System.NotImplementedException();
   26|         """;
   27| 
   28|     [Fact]
   29|     public async Task FormatterMustBePartial()
   30|     {
   31|         string testSource = /* lang=c#-test */ $$"""
   32|             using MessagePack;
   33|             using MessagePack.Formatters;
   34| 
   35|             public class MyType
   36|             {
   37|                 public int Id { get; set; }
   38|             }
   39| 
   40|             [GeneratedMessagePackFormatter]
   41|             public class {|MsgPack019:MyFormatter|} : IMessagePackFormatter<MyType>
   42|             {
   43|             {{Members}}
   44|             }
   45|             """;
   46| 
   47|         await new VerifyCS.Test
   48|         {
   49|             TestState =
   50|             {
   51|                 Sources = { testSource },
   52|             },
   53|         }.RunDefaultAsync(this.testOutputHelper);
   54|     }
   55| 
   56|     [Fact]
   57|     public async Task FormatterMustImplementFormatterOfT()
   58|     {
   59|         string testSource = /* lang=c#-test */ """
   60|             using MessagePack;
   61| 
   62|             [GeneratedMessagePackFormatter]
   63|             public partial class {|MsgPack020:MyFormatter|}
   64|             {
   65|             }
   66|             """;
   67| 
   68|         await new VerifyCS.Test
   69|         {
   70|             TestState =
   71|             {
   72|                 Sources = { testSource },
   73|             },
   74|         }.RunDefaultAsync(this.testOutputHelper);
   75|     }
   76| 
   77|     [Fact]
   78|     public async Task FormattedTypeMustNotBeAbstract()
   79|     {
   80|         string testSource = /* lang=c#-test */ $$"""
   81|             using MessagePack;
   82|             using MessagePack.Formatters;
   83| 
   84|             public abstract class MyType
   85|             {
   86|             }
   87| 
   88|             [GeneratedMessagePackFormatter]
   89|             public partial class {|MsgPack021:MyFormatter|} : IMessagePackFormatter<MyType>
   90|             {
   91|             {{Members}}
   92|             }
   93|             """;
   94| 
   95|         await new VerifyCS.Test
   96|         {
   97|             TestState =
   98|             {
   99|                 Sources = { testSource },
  100|             },
  101|         }.RunDefaultAsync(this.testOutputHelper);
  102|     }
  103| 
  104|     [Fact]
  105|     public async Task SurrogateMemberMustMatchFormattedType()
  106|     {
  107|         string testSource = /* lang=c#-test */ $$"""
  108|             using MessagePack;
  109|             using MessagePack.Formatters;
  110| 
  111|             public class MyType
  112|             {
  113|                 public int Id { get; set; }
  114|             }
  115| 
  116|             public class MySurrogate
  117|             {
  118|                 [Key(0)]
  119|                 public int {|MsgPack022:Missing|} { get; set; }
  120|             }
  121| 
  122|             [GeneratedMessagePackFormatter(SurrogateType = typeof(MySurrogate))]
  123|             public partial class MyFormatter : IMessagePackFormatter<MyType>
  124|             {
  125|             {{Members}}
  126|             }
  127|             """;
  128| 
  129|         await new VerifyCS.Test
  130|         {
  131|             TestState =
  132|             {
  133|                 Sources = { testSource },
  134|             },
  135|         }.RunDefaultAsync(this.testOutputHelper);
  136|     }
  137| 
  138|     [Fact]
  139|     public async Task SurrogateMemberMustHaveMatchingType()
  140|     {
  141|         string testSource = /* lang=c#-test */ $$"""
  142|             using MessagePack;
  143|             using MessagePack.Formatters;
  144| 
  145|             public class MyType
  146|             {
  147|                 public int Id { get; set; }
  148|             }
  149| 
  150|             public class MySurrogate
  151|             {
  152|                 [Key(0)]
  153|                 public string {|MsgPack022:Id|} { get; set; }
  154|             }
  155| 
  156|             [GeneratedMessagePackFormatter(SurrogateType = typeof(MySurrogate))]
  157|             public partial class MyFormatter : IMessagePackFormatter<MyType>
  158|             {
  159|             {{Members}}
  160|             }
  161|             """;
  162| 
  163|         await new VerifyCS.Test
  164|         {
  165|             TestState =
  166|             {
  167|                 Sources = { testSource },
  168|             },
  169|         }.RunDefaultAsync(this.testOutputHelper);
  170|     }
  171| 
  172|     [Fact]
  173|     public async Task SurrogateKeysMustNotMixStringAndInt()
  174|     {
  175|         string testSource = /* lang=c#-test */ $$"""
  176|             using MessagePack;
  177|             using MessagePack.Formatters;
  178| 
  179|             public class MyType
  180|             {
  181|                 public int Id { get; set; }
  182|                 public string Name { get; set; }
  183|             }
  184| 
  185|             public class MySurrogate
  186|             {
  187|                 [Key(0)]
  188|                 public int Id { get; set; }
  189| 
  190|                 [Key("Name")]
  191|                 public string {|#0:Name|} { get; set; }
  192|             }
  193| 
  194|             [GeneratedMessagePackFormatter(SurrogateType = typeof(MySurrogate))]
  195|             public partial class MyFormatter : IMessagePackFormatter<MyType>
  196|             {
  197|             {{Members}}
  198|             }
  199|             """;
  200| 
  201|         await new VerifyCS.Test
  202|         {
  203|             TestState =
  204|             {
  205|                 Sources = { testSource },
  206|             },
  207|             ExpectedDiagnostics = { DiagnosticResult.CompilerError("MsgPack005").WithLocation(0) },
  208|         }.RunDefaultAsync(this.testOutputHelper);
  209|     }
  210| }
```

### src/MessagePack.Annotations/Attributes.cs at base (32258fdb), around the changed lines
```
  ... lines 1-108 not shown ...
  109|         /// </summary>
  110|         /// <param name="key">The distinguishing value that identifies a particular subtype.</param>
  111|         /// <param name="subType">The full name (should be assembly qualified) of the derived or implementing type.</param>
  112|         public UnionAttribute(int key, string subType)
  113|         {
  114|             this.Key = key;
  115|             this.SubType = Type.GetType(subType, throwOnError: true);
  116|         }
  117|     }
  118| 
  119|     [AttributeUsage(AttributeTargets.Constructor, AllowMultiple = false, Inherited = true)]
  120|     public class SerializationConstructorAttribute : Attribute
  121|     {
  122|     }
  123| 
  124|     [AttributeUsage(AttributeTargets.Class | AttributeTargets.Struct | AttributeTargets.Interface | AttributeTargets.Enum | AttributeTargets.Field | AttributeTargets.Property | AttributeTargets.Parameter | AttributeTargets.ReturnValue, AllowMultiple = false, Inherited = true)]
  125|     public class MessagePackFormatterAttribute : Attribute
  126|     {
  127|         public Type FormatterType { get; }
  128| 
  129|         public object?[]? Arguments { get; }
  130| 
  131|         public MessagePackFormatterAttribute(Type formatterType)
  132|         {
  133|             this.FormatterType = formatterType ?? throw new ArgumentNullException(nameof(formatterType));
  134|         }
  135| 
  136|         public MessagePackFormatterAttribute(Type formatterType, params object?[]? arguments)
  137|         {
  138|             this.FormatterType = formatterType ?? throw new ArgumentNullException(nameof(formatterType));
  139|             this.Arguments = arguments;
  140|         }
  141|     }
  142| }
```

### src/MessagePack.SourceGenerator/Analyzers/MsgPack00xMessagePackAnalyzer.cs at base (32258fdb), around the changed lines
```
    1| // Copyright (c) All contributors. All rights reserved.
    2| // Licensed under the MIT license. See LICENSE file in the project root for full license information.
    3| 
    4| using System.Collections.Immutable;
    5| using Microsoft.CodeAnalysis;
    6| using Microsoft.CodeAnalysis.CSharp;
    7| using Microsoft.CodeAnalysis.CSharp.Syntax;
    8| using Microsoft.CodeAnalysis.Diagnostics;
    9| using AnalyzerOptions = MessagePack.SourceGenerator.CodeAnalysis.AnalyzerOptions;
   10| 
   11| namespace MessagePack.SourceGenerator.Analyzers;
   12| 
   13| [DiagnosticAnalyzer(LanguageNames.CSharp)]
   14| public class MsgPack00xMessagePackAnalyzer : DiagnosticAnalyzer
   15| {
   16|     public const string UseMessagePackObjectAttributeId = "MsgPack003";
   17|     public const string AttributeMessagePackObjectMembersId = "MsgPack004";
   18|     public const string InvalidMessagePackObjectId = "MsgPack005";
   19|     public const string MessagePackFormatterMustBeMessagePackFormatterId = "MsgPack006";
   20|     public const string DeserializingConstructorId = "MsgPack007";
   21|     public const string AOTLimitationsId = "MsgPack008";
   22|     public const string CollidingFormattersId = "MsgPack009";
   23|     public const string InaccessibleFormatterTypeId = "MsgPack010";
   24|     public const string PartialTypeRequiredId = "MsgPack011";
   25|     public const string InaccessibleDataTypeId = "MsgPack012";
   26|     public const string InaccessibleFormatterInstanceId = "MsgPack013";
   27|     public const string NullableReferenceTypeFormatterId = "MsgPack014";
   28|     public const string MessagePackObjectAllowPrivateId = "MsgPack015";
   29|     public const string AOTDerivedKeyId = "MsgPack016";
   30|     public const string AOTInitPropertyId = "MsgPack017";
   31|     public const string CollidingMemberNamesInForceMapModeId = "MsgPack018";
   32| 
   33|     internal const string Category = "Usage";
   34| 
   35|     public const string MessagePackObjectAttributeShortName = Constants.MessagePackObjectAttributeName;
   36|     public const string KeyAttributeShortName = "KeyAttribute";
   37|     public const string IgnoreShortName = "IgnoreMemberAttribute";
   38|     public const string DataMemberShortName = "DataMemberAttribute";
   39|     public const string IgnoreDataMemberShortName = "IgnoreDataMemberAttribute";
   40|     public const string AllowPrivatePropertyName = "AllowPrivate";
   41| 
   42|     private const string InvalidMessagePackObjectTitle = "MessagePackObject validation";
   43|     private const DiagnosticSeverity InvalidMessagePackObjectSeverity = DiagnosticSeverity.Error;
   44| 
   45|     public static readonly DiagnosticDescriptor TypeMustBeMessagePackObject = new DiagnosticDescriptor(
   46|         id: UseMessagePackObjectAttributeId,
   47|         title: "Use MessagePackObjectAttribute",
   48|         category: Category,
   49|         messageFormat: "Type must be marked with MessagePackObjectAttribute: {0}", // type.Name
   50|         description: "Type must be marked with MessagePackObjectAttribute.",
   51|         defaultSeverity: DiagnosticSeverity.Error,
   52|         isEnabledByDefault: true,
   53|         helpLinkUri: AnalyzerUtilities.GetHelpLink(UseMessagePackObjectAttributeId));
   54| 
   55|     public static readonly DiagnosticDescriptor MessageFormatterMustBeMessagePackFormatter = new DiagnosticDescriptor(
   56|         id: MessagePackFormatterMustBeMessagePackFormatterId,
   57|         title: "Must be IMessageFormatter",
   58|         category: Category,
   59|         messageFormat: "Type must be of IMessagePackFormatter: {0}", // type.Name
   60|         description: "Type must be of IMessagePackFormatter.",
   61|         defaultSeverity: DiagnosticSeverity.Error,
   62|         isEnabledByDefault: true,
   63|         helpLinkUri: AnalyzerUtilities.GetHelpLink(MessagePackFormatterMustBeMessagePackFormatterId));
   64| 
  ... lines 65-280 not shown ...
  281|         messageFormat: "This MessagePack formattable type must have at least internal visibility",
  282|         description: "MessagePack serializable objects must be at least internally accessible so a source-generated formatter can access it.",
  283|         defaultSeverity: DiagnosticSeverity.Error,
  284|         isEnabledByDefault: true,
  285|         helpLinkUri: AnalyzerUtilities.GetHelpLink(InaccessibleDataTypeId));
  286| 
  287|     public static readonly DiagnosticDescriptor NullableReferenceTypeFormatter = new(
  288|         id: NullableReferenceTypeFormatterId,
  289|         title: "Format nullable reference types",
  290|         category: Category,
  291|         messageFormat: "Implement IMessagePackFormatter<{0}?> (with nullable annotation)",
  292|         defaultSeverity: DiagnosticSeverity.Warning,
  293|         isEnabledByDefault: true,
  294|         helpLinkUri: AnalyzerUtilities.GetHelpLink(NullableReferenceTypeFormatterId));
  295| 
  296|     public static readonly DiagnosticDescriptor MessagePackObjectAllowPrivateRequired = new(
  297|         id: MessagePackObjectAllowPrivateId,
  298|         title: "MessagePackObjectAttribute.AllowPrivate should be set",
  299|         category: Category,
  300|         messageFormat: "MessagePackObjectAttribute.AllowPrivate should be set to true because the type is not public and/or at least one of its non-public members are attributed for serialization",
  301|         defaultSeverity: DiagnosticSeverity.Warning,
  302|         isEnabledByDefault: true,
  303|         helpLinkUri: AnalyzerUtilities.GetHelpLink(MessagePackObjectAllowPrivateId));
  304| 
  305|     public static readonly DiagnosticDescriptor CollidingMemberNamesInForceMapMode = new(
  306|         id: CollidingMemberNamesInForceMapModeId,
  307|         title: "Unique names required in force map mode",
  308|         category: Category,
  309|         messageFormat: "All serialized member names must be unique in force map mode, but this member redeclares a member with the same name as one found on a base type",
  310|         defaultSeverity: DiagnosticSeverity.Error,
  311|         isEnabledByDefault: true,
  312|         helpLinkUri: AnalyzerUtilities.GetHelpLink(CollidingMemberNamesInForceMapModeId));
  313| 
  314|     public override ImmutableArray<DiagnosticDescriptor> SupportedDiagnostics { get; } = ImmutableArray.Create(
  315|         TypeMustBeMessagePackObject,
  316|         MessageFormatterMustBeMessagePackFormatter,
  317|         MemberNeedsKey,
  318|         BaseTypeContainsUnattributedPublicMembers,
  319|         InvalidMessagePackObject,
  320|         BothStringAndIntKeyAreNull,
  321|         DoNotMixStringAndIntKeys,
  322|         KeysMustBeUnique,
  323|         UnionAttributeRequired,
  324|         KeyAnnotatedMemberInMapMode,
  325|         NoDeserializingConstructor,
  326|         DeserializingConstructorParameterTypeMismatch,
  327|         DeserializingConstructorParameterIndexMissing,
  328|         DeserializingConstructorParameterNameMissing,
  329|         DeserializingConstructorParameterNameDuplicate,
  330|         AotUnionAttributeRequiresTypeArg,
  331|         AotArrayRankTooHigh,
  332|         AOTDerivedKeyAttribute,
  333|         AOTInitProperty,
  334|         CollidingFormatters,
  335|         InaccessibleFormatterInstance,
  336|         InaccessibleFormatterType,
  337|         PartialTypeRequired,
  338|         InaccessibleDataType,
  339|         NullableReferenceTypeFormatter,
  340|         MessagePackObjectAllowPrivateRequired,
  341|         CollidingMemberNamesInForceMapMode);
  342| 
  343|     public override void Initialize(AnalysisContext context)
  344|     {
  345|         context.EnableConcurrentExecution();
  346|         context.ConfigureGeneratedCodeAnalysis(GeneratedCodeAnalysisFlags.Analyze | GeneratedCodeAnalysisFlags.ReportDiagnostics);
  347|         context.RegisterCompilationStartAction(context =>
  348|         {
  349|             if (ReferenceSymbols.TryCreate(context.Compilation, out ReferenceSymbols? typeReferences))
  350|             {
  351|                 // Search the compilation for implementations of IMessagePackFormatter<T>.
  352|                 ImmutableHashSet<FormatterDescriptor> formatterTypes = this.SearchForFormatters(context.Compilation.Assembly.GlobalNamespace).ToImmutableHashSet();
  353| 
  354|                 AnalyzerOptions options = new AnalyzerOptions()
  355|                     .WithFormatterTypes(ImmutableArray<FormattableType>.Empty, formatterTypes)
  356|                     .WithAssemblyAttributes(context.Compilation.Assembly.GetAttributes(), context.CancellationToken);
  357|                 context.RegisterSymbolAction(context => this.AnalyzeSymbol(context, typeReferences, options), SymbolKind.NamedType);
  358|                 context.RegisterSymbolStartAction(context => SymbolStartAction(context, typeReferences, options), SymbolKind.NamedType);
  359|             }
  360|         });
  361|     }
  362| 
  363|     private static void SymbolStartAction(SymbolStartAnalysisContext context, ReferenceSymbols typeReferences, AnalyzerOptions options)
  364|     {
  365|         INamedTypeSymbol declaredSymbol = (INamedTypeSymbol)context.Symbol;
  366|         QualifiedNamedTypeName typeName = new(declaredSymbol);
  367| 
  368|         // If this is a formatter, confirm that it meets requirements.
  369|         if (options.KnownFormattersByName.TryGetValue(typeName, out FormatterDescriptor? formatter))
  370|         {
  371|             // Call out any formattable reference types that are not nullable.
  372|             INamedTypeSymbol[] missing = (
  373|                 from iface in declaredSymbol.Interfaces
  374|                 where SymbolEqualityComparer.Default.Equals(iface.ConstructUnboundGenericType(), typeReferences.MessagePackFormatterOfT) &&
  ... lines 375-467 not shown ...
```

### src/MessagePack.SourceGenerator/Transforms/FormatterTemplate.tt at base (32258fdb), around the changed lines
```
    1| ﻿<#@ template debug="false" hostspecific="false" linePragmas="false" language="C#" #>
    2| <#@ assembly name="System.Core" #>
    3| <#@ import namespace="System.Linq" #>
    4| <#@ import namespace="System.Text" #>
    5| <#@ import namespace="System.Collections.Generic" #>
    6| 
    7| #pragma warning disable CS8669 // We may leak nullable annotations into generated code.
    8| 
    9| using MsgPack = global::MessagePack;
   10| 
   11| <# using (this.EmitNestingTypesAndNamespaces(this.Write)) { #>
   12| 
   13| <#  bool isFormatterResolverNecessary = GeneratorUtilities.ShouldUseFormatterResolver(Info.Members);#>
   14| 	internal sealed class <#= Info.Formatter.GetQualifiedName(Qualifiers.None) #> : MsgPack::Formatters.IMessagePackFormatter<<#= Info.DataType.GetQualifiedName(genericStyle: GenericParameterStyle.Identifiers) #>>
   15| <# TransformUtilities.EmitTypeConstraints(Info.Formatter, this.Write); #>
   16| 	{
   17| <# foreach (var item in Info.Members) { #>
   18| <# if (item.CustomFormatter != null) { #>
   19| 		private readonly <#= item.CustomFormatter.InstanceTypeName.GetQualifiedName(genericStyle: GenericParameterStyle.Arguments) #> __<#= item.Name #>CustomFormatter__ = <#= item.CustomFormatter.InstanceExpression #>;
   20| <# } #>
   21| <# } #>
   22| 
   23| 		public void Serialize(ref MsgPack::MessagePackWriter writer, <#= Info.DataType.GetQualifiedName(genericStyle: GenericParameterStyle.Identifiers) #> value, MsgPack::MessagePackSerializerOptions options)
   24| 		{
   25| <# if (Info.IsClass) { #>
   26| 			if (value == null)
   27| 			{
   28| 				writer.WriteNil();
   29| 				return;
   30| 			}
   31| 
   32| <# }
   33| 
   34|   if (isFormatterResolverNecessary) { #>
   35| 			MsgPack::IFormatterResolver formatterResolver = options.Resolver;
   36| <# }
   37| 
   38|  if (Info.HasIMessagePackSerializationCallbackReceiver) {
   39|   if (Info.NeedsCastOnBefore) { #>
   40| 			((MsgPack::IMessagePackSerializationCallbackReceiver)value).OnBeforeSerialize();
   41| <# } else { #>
   42| 			value.OnBeforeSerialize();
   43| <# } #>
   44| <# } #>
   45| 			writer.WriteArrayHeader(<#= Info.MaxKey + 1 #>);
   46| <# for (var i = 0; i <= Info.MaxKey; i++) {
   47|   var member = Info.GetMember(i);
  ... lines 48-141 not shown ...
```

## What you did NOT get (refuse anything that depends on it)
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

Return only the JSON object described in the brief.