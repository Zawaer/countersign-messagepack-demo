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
# Change 2234: branch ju26-issue-2234, base 32258fdbee4bcd653c79f51b4376b5103c6f4d27, head 9007cee1163c4a274fd60c3cc20c21ae63622786
Commit message: Implementation for #2234 The analyzer does not work if SuppressSourceGeneration = true
Upstream issue: https://github.com/MessagePack-CSharp/MessagePack-CSharp/issues/2234

## Requirement set (requirements/2234.yaml)
```yaml
# PLACEHOLDER derived from upstream issue #2234 until Tieto's official requirement set is pasted in.
change: "2234"
branch: ju26-issue-2234
source: https://github.com/MessagePack-CSharp/MessagePack-CSharp/issues/2234
official: false
requirements:
  - id: REQ-2234-F1
    type: functional
    text: "The analyzer must report contract diagnostics (e.g. missing [Key], duplicate keys, mixed key kinds) for [MessagePackObject(SuppressSourceGeneration = true)] types, as it did in version 3.1.0."
  - id: REQ-2234-F2
    type: functional
    text: "Diagnostics that only apply when a formatter is generated (partial-class requirement, AOT-only checks) must not be reported for types with SuppressSourceGeneration = true."
  - id: REQ-2234-N1
    type: non-functional
    checks: [tests.full_suite]
    text: "The analyzer and generator must not crash on invalid contracts (e.g. duplicate keys) in such types."
  - id: REQ-2234-N2
    type: non-functional
    checks: [tests.fail_without_fix]
    text: "The fix is covered by automated tests that fail without it; no regressions in the existing test suite."
```

## facts.json (deterministic checks; cite their ids and test names)
```json
{
 "change": "2234",
 "branch": "ju26-issue-2234",
 "base": "32258fdb",
 "head": "9007cee1",
 "base_full": "32258fdbee4bcd653c79f51b4376b5103c6f4d27",
 "head_full": "9007cee1163c4a274fd60c3cc20c21ae63622786",
 "commit_message": "Implementation for #2234 The analyzer does not work if SuppressSourceGeneration = true",
 "author": "Stelian Vultur",
 "agent_written": true,
 "diff": {
  "files": 4,
  "insertions": 262,
  "deletions": 4,
  "by_kind": {
   "doc": 1,
   "source": 1,
   "test": 2
  },
  "by_file": [
   {
    "path": "README.md",
    "ins": 14,
    "del": 0,
    "kind": "doc"
   },
   {
    "path": "src/MessagePack.SourceGenerator/CodeAnalysis/TypeCollector.cs",
    "ins": 18,
    "del": 4,
    "kind": "source"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.ExecutionTests/SuppressedSourceGenerationTests.cs",
    "ins": 37,
    "del": 0,
    "kind": "test"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/SuppressSourceGenerationAnalyzerTests.cs",
    "ins": 193,
    "del": 0,
    "kind": "test"
   }
  ]
 },
 "new_tests_in_diff": [
  "SuppressSourceGenerationAnalyzerTests.AllowPrivateRequiredIsReported",
  "SuppressSourceGenerationAnalyzerTests.DuplicateIntKeysAreReportedWithoutAnalyzerFailure",
  "SuppressSourceGenerationAnalyzerTests.DuplicateKeysAreReportedWithoutAnalyzerFailureForGeneratedTypes",
  "SuppressSourceGenerationAnalyzerTests.DuplicateStringKeysAreReportedWithoutAnalyzerFailure",
  "SuppressSourceGenerationAnalyzerTests.MemberTypeMustBeMessagePackObjectIsReported",
  "SuppressSourceGenerationAnalyzerTests.MemberWithoutKeyIsReported",
  "SuppressSourceGenerationAnalyzerTests.MixedKeyKindsAreReportedWithoutAnalyzerFailure",
  "SuppressSourceGenerationAnalyzerTests.SourceGenerationOnlyDiagnosticsAreNotReportedWhenSuppressed",
  "SuppressedSourceGenerationTests.NoFormatterIsGeneratedForSuppressedType",
  "SuppressedSourceGenerationTests.SuppressedTypeRoundTripsThroughDynamicResolver"
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
   "summary": "0 errors, 1 unique warnings",
   "log": "evidence/2234/logs/build.log",
   "duration_s": 5.0
  },
  {
   "id": "tests.targeted",
   "tool": "dotnet test",
   "tool_version": "8.0.402",
   "status": "pass",
   "summary": "8 passed, 0 failed, 0 skipped (8 new tests in run)",
   "tests": [
    {
     "name": "SuppressSourceGenerationAnalyzerTests.AllowPrivateRequiredIsReported",
     "outcome": "passed",
     "new": true
    },
    {
     "name": "SuppressSourceGenerationAnalyzerTests.DuplicateIntKeysAreReportedWithoutAnalyzerFailure",
     "outcome": "passed",
     "new": true
    },
    {
     "name": "SuppressSourceGenerationAnalyzerTests.DuplicateKeysAreReportedWithoutAnalyzerFailureForGeneratedTypes",
     "outcome": "passed",
     "new": true
    },
    {
     "name": "SuppressSourceGenerationAnalyzerTests.DuplicateStringKeysAreReportedWithoutAnalyzerFailure",
     "outcome": "passed",
     "new": true
    },
    {
     "name": "SuppressSourceGenerationAnalyzerTests.MemberTypeMustBeMessagePackObjectIsReported",
     "outcome": "passed",
     "new": true
    },
    {
     "name": "SuppressSourceGenerationAnalyzerTests.MemberWithoutKeyIsReported",
     "outcome": "passed",
     "new": true
    },
    {
     "name": "SuppressSourceGenerationAnalyzerTests.MixedKeyKindsAreReportedWithoutAnalyzerFailure",
     "outcome": "passed",
     "new": true
    },
    {
     "name": "SuppressSourceGenerationAnalyzerTests.SourceGenerationOnlyDiagnosticsAreNotReportedWhenSuppressed",
     "outcome": "passed",
     "new": true
    }
   ],
   "log": "evidence/2234/logs/tests_targeted.1.log",
   "duration_s": 2.0,
   "filter": [
    "FullyQualifiedName~SuppressSourceGenerationAnalyzerTests."
   ],
   "project": "tests/MessagePack.SourceGenerator.Tests"
  },
  {
   "id": "tests.fail_without_fix",
   "tool": "dotnet test (source reverted, tests kept)",
   "tool_version": "8.0.402",
   "status": "pass",
   "summary": "new tests fail on base source: 4/8 failed -> tests do cover the change (4 new tests pass without the fix)",
   "tests": [
    {
     "name": "SuppressSourceGenerationAnalyzerTests.AllowPrivateRequiredIsReported",
     "outcome": "passed",
     "new": true
    },
    {
     "name": "SuppressSourceGenerationAnalyzerTests.DuplicateIntKeysAreReportedWithoutAnalyzerFailure",
     "outcome": "failed",
     "new": true,
     "error": "System.InvalidOperationException : Context: Diagnostics of test state\nMismatch between number of diagnostics returned, expected \"1\" actual \"2\"\r\n\r\nDiagnostics:\r\n// /0/Test0.cs(10,5): error MsgPack005: All KeyAttribute arguments must be unique\nVerifyCS.Diagnostic(MsgPack00xMessagePackAnalyzer.MsgPack005).WithSpan(10, 5, 11, 40),\n// error AD0001: Analyzer 'MessagePack.SourceGenerator.Analyzers.MsgPac [...]"
    },
    {
     "name": "SuppressSourceGenerationAnalyzerTests.DuplicateKeysAreReportedWithoutAnalyzerFailureForGeneratedTypes",
     "outcome": "failed",
     "new": true,
     "error": "System.InvalidOperationException : Context: Diagnostics of test state\nMismatch between number of diagnostics returned, expected \"1\" actual \"2\"\r\n\r\nDiagnostics:\r\n// /0/Test0.cs(10,5): error MsgPack005: All KeyAttribute arguments must be unique\nVerifyCS.Diagnostic(MsgPack00xMessagePackAnalyzer.MsgPack005).WithSpan(10, 5, 11, 40),\n// error AD0001: Analyzer 'MessagePack.SourceGenerator.Analyzers.MsgPac [...]"
    },
    {
     "name": "SuppressSourceGenerationAnalyzerTests.DuplicateStringKeysAreReportedWithoutAnalyzerFailure",
     "outcome": "failed",
     "new": true,
     "error": "System.InvalidOperationException : Context: Diagnostics of test state\nMismatch between number of diagnostics returned, expected \"1\" actual \"2\"\r\n\r\nDiagnostics:\r\n// /0/Test0.cs(10,5): error MsgPack005: All KeyAttribute arguments must be unique\nVerifyCS.Diagnostic(MsgPack00xMessagePackAnalyzer.MsgPack005).WithSpan(10, 5, 11, 40),\n// error AD0001: Analyzer 'MessagePack.SourceGenerator.Analyzers.MsgPac [...]"
    },
    {
     "name": "SuppressSourceGenerationAnalyzerTests.MemberTypeMustBeMessagePackObjectIsReported",
     "outcome": "passed",
     "new": true
    },
    {
     "name": "SuppressSourceGenerationAnalyzerTests.MemberWithoutKeyIsReported",
     "outcome": "passed",
     "new": true
    },
    {
     "name": "SuppressSourceGenerationAnalyzerTests.MixedKeyKindsAreReportedWithoutAnalyzerFailure",
     "outcome": "failed",
     "new": true,
     "error": "System.InvalidOperationException : Context: Diagnostics of test state\nMismatch between number of diagnostics returned, expected \"1\" actual \"2\"\r\n\r\nDiagnostics:\r\n// /0/Test0.cs(10,5): error MsgPack005: All KeyAttribute arguments must be of the same type (either string or int)\nVerifyCS.Diagnostic(MsgPack00xMessagePackAnalyzer.MsgPack005).WithSpan(10, 5, 11, 40),\n// error AD0001: Analyzer 'MessagePack [...]"
    },
    {
     "name": "SuppressSourceGenerationAnalyzerTests.SourceGenerationOnlyDiagnosticsAreNotReportedWhenSuppressed",
     "outcome": "passed",
     "new": true
    }
   ],
   "log": "evidence/2234/logs/tests_fail_without_fix.1.log",
   "duration_s": 2.0,
   "reverted_files": [
    "src/MessagePack.SourceGenerator/CodeAnalysis/TypeCollector.cs"
   ],
   "full_suite_with_source_reverted": {
    "total": 175,
    "failed": 4,
    "failed_tests": [
     "SuppressSourceGenerationAnalyzerTests.DuplicateIntKeysAreReportedWithoutAnalyzerFailure",
     "SuppressSourceGenerationAnalyzerTests.DuplicateKeysAreReportedWithoutAnalyzerFailureForGeneratedTypes",
     "SuppressSourceGenerationAnalyzerTests.DuplicateStringKeysAreReportedWithoutAnalyzerFailure",
     "SuppressSourceGenerationAnalyzerTests.MixedKeyKindsAreReportedWithoutAnalyzerFailure"
    ],
    "log": "evidence/2234/logs/fail_without_fix.full_suite.log"
   },
   "new_failed": 4,
   "new_total": 8
  },
  {
   "id": "tests.full_suite",
   "tool": "dotnet test",
   "tool_version": "8.0.402",
   "status": "pass",
   "summary": "tests/MessagePack.SourceGenerator.Tests: 175 tests, 175 passed, 0 failed (0 not failing on base, 0 also failing on base)",
   "project": "tests/MessagePack.SourceGenerator.Tests",
   "total": 175,
   "passed": 175,
   "failed": 0,
   "failures_not_on_base": [],
   "failures_also_on_base": [],
   "log": "evidence/2234/logs/tests_full_suite.log",
   "duration_s": 6.0
  },
  {
   "id": "public_api",
   "tool": "git diff of PublicAPI.*.txt + scan of added public/protected declarations in src/",
   "status": "pass",
   "summary": "no public API changes: no PublicAPI.Shipped/Unshipped.txt changed, no public/protected declarations added or removed in src/",
   "publicapi_files_changed": []
  },
  {
   "id": "analyzers",
   "tool": "dotnet build warnings (Roslyn analyzers, StyleCop, PublicApiAnalyzers) vs base",
   "status": "pass",
   "summary": "no new warnings",
   "new_warnings": [],
   "resolved_warnings": [],
   "base_warning_count": 1
  },
  {
   "id": "tests.targeted.execution",
   "tool": "dotnet build + dotnet test (ExecutionTests, MapModeExecutionTests)",
   "tool_version": "9.0.321",
   "tool_version_note": "SDK 9 used because the generator needs Roslyn 4.12; repo pins 8.0.402 (global.json overridden to 9.0.321 in the scratch worktree only)",
   "filter": "FullyQualifiedName~SuppressedSourceGenerationTests.",
   "projects": [
    "tests/MessagePack.SourceGenerator.ExecutionTests",
    "tests/MessagePack.SourceGenerator.MapModeExecutionTests"
   ],
   "status": "pass",
   "summary": "SuppressedSourceGenerationTests: 4 passed, 0 failed (4 new test results; runtime: generator runs inside csc, no CS9057)",
   "tests": [
    {
     "name": "SuppressedSourceGenerationTests.NoFormatterIsGeneratedForSuppressedType",
     "project": "tests/MessagePack.SourceGenerator.ExecutionTests",
     "outcome": "passed",
     "new": true
    },
    {
     "name": "SuppressedSourceGenerationTests.SuppressedTypeRoundTripsThroughDynamicResolver",
     "project": "tests/MessagePack.SourceGenerator.ExecutionTests",
     "outcome": "passed",
     "new": true
    },
    {
     "name": "SuppressedSourceGenerationTests.NoFormatterIsGeneratedForSuppressedType",
     "project": "tests/MessagePack.SourceGenerator.MapModeExecutionTests",
     "outcome": "passed",
     "new": true
    },
    {
     "name": "SuppressedSourceGenerationTests.SuppressedTypeRoundTripsThroughDynamicResolver",
     "project": "tests/MessagePack.SourceGenerator.MapModeExecutionTests",
     "outcome": "passed",
     "new": true
    }
   ],
   "cs9057": false,
   "log": [
    "evidence/2234/logs/execution.ExecutionTests.build.log",
    "evidence/2234/logs/execution.ExecutionTests.targeted.log",
    "evidence/2234/logs/execution.ExecutionTests.full.log",
    "evidence/2234/logs/execution.MapModeExecutionTests.build.log",
    "evidence/2234/logs/execution.MapModeExecutionTests.targeted.log",
    "evidence/2234/logs/execution.MapModeExecutionTests.full.log"
   ],
   "duration_s": 49.0,
   "on_base": "tests do not exist on base (new in this change): tests/MessagePack.SourceGenerator.ExecutionTests built=True, 0 matching tests, tests/MessagePack.SourceGenerator.MapModeExecutionTests built=True, 0 matching tests",
   "sdk8_attempt": {
    "tool_version": "8.0.402",
    "status": "error",
    "reason": "CS9057: generator references Microsoft.CodeAnalysis 4.12, SDK 8.0.402 ships Roslyn 4.11",
    "log": "evidence/2234/logs/execution_tests.sdk8.build.log"
   }
  },
  {
   "id": "tests.execution_fail_without_fix",
   "tool": "dotnet test (source reverted, tests kept) - ExecutionTests",
   "tool_version": "9.0.321",
   "tool_version_note": "SDK 9 used because the generator needs Roslyn 4.12; repo pins 8.0.402 (global.json overridden to 9.0.321 in the scratch worktree only)",
   "filter": "FullyQualifiedName~SuppressedSourceGenerationTests.",
   "projects": [
    "tests/MessagePack.SourceGenerator.ExecutionTests",
    "tests/MessagePack.SourceGenerator.MapModeExecutionTests"
   ],
   "tests": [
    {
     "name": "SuppressedSourceGenerationTests.NoFormatterIsGeneratedForSuppressedType",
     "project": "tests/MessagePack.SourceGenerator.ExecutionTests",
     "outcome": "passed",
     "new": true
    },
    {
     "name": "SuppressedSourceGenerationTests.SuppressedTypeRoundTripsThroughDynamicResolver",
     "project": "tests/MessagePack.SourceGenerator.ExecutionTests",
     "outcome": "passed",
     "new": true
    },
    {
     "name": "SuppressedSourceGenerationTests.NoFormatterIsGeneratedForSuppressedType",
     "project": "tests/MessagePack.SourceGenerator.MapModeExecutionTests",
     "outcome": "passed",
     "new": true
    },
    {
     "name": "SuppressedSourceGenerationTests.SuppressedTypeRoundTripsThroughDynamicResolver",
     "project": "tests/MessagePack.SourceGenerator.MapModeExecutionTests",
     "outcome": "passed",
     "new": true
    }
   ],
   "log": [
    "evidence/2234/logs/execution_fail_without_fix.ExecutionTests.build.log",
    "evidence/2234/logs/execution_fail_without_fix.ExecutionTests.targeted.log",
    "evidence/2234/logs/execution_fail_without_fix.ExecutionTests.full.log",
    "evidence/2234/logs/execution_fail_without_fix.MapModeExecutionTests.build.log",
    "evidence/2234/logs/execution_fail_without_fix.MapModeExecutionTests.targeted.log",
    "evidence/2234/logs/execution_fail_without_fix.MapModeExecutionTests.full.log"
   ],
   "status": "fail",
   "summary": "new runtime tests pass on base source: 0/4 failed -> these runtime tests do NOT demonstrate the change (runtime behaviour they check is identical with and without the fix)",
   "new_failed": 0,
   "new_total": 4
  },
  {
   "id": "tests.execution_full_suite",
   "tool": "dotnet test (whole ExecutionTests, MapModeExecutionTests) vs base",
   "tool_version": "9.0.321",
   "tool_version_note": "SDK 9 used because the generator needs Roslyn 4.12; repo pins 8.0.402 (global.json overridden to 9.0.321 in the scratch worktree only)",
   "status": "pass",
   "summary": "tests/MessagePack.SourceGenerator.ExecutionTests: 16/16 passed (base 14/14), 0 failures not on base; tests/MessagePack.SourceGenerator.MapModeExecutionTests: 22/22 passed (base 20/20), 0 failures not on base",
   "projects": [
    {
     "project": "tests/MessagePack.SourceGenerator.ExecutionTests",
     "total": 16,
     "passed": 16,
     "failed": 0,
     "failures_not_on_base": [],
     "base_total": 14,
     "base_passed": 14,
     "tests_added_vs_base": [
      "SuppressedSourceGenerationTests.NoFormatterIsGeneratedForSuppressedType",
      "SuppressedSourceGenerationTests.SuppressedTypeRoundTripsThroughDynamicResolver"
     ],
     "tests_missing_vs_base": [],
     "new_build_warnings_vs_base": [
      "tests/MessagePack.SourceGenerator.ExecutionTests/SuppressedSourceGenerationTests.cs: warning SA1649: File name should match first type name (https://github.com/DotNetAnalyzers/StyleCopAnalyzers/blob/master/documentation/SA1649.md)"
     ]
    },
    {
     "project": "tests/MessagePack.SourceGenerator.MapModeExecutionTests",
     "total": 22,
     "passed": 22,
     "failed": 0,
     "failures_not_on_base": [],
     "base_total": 20,
     "base_passed": 20,
     "tests_added_vs_base": [
      "SuppressedSourceGenerationTests.NoFormatterIsGeneratedForSuppressedType",
      "SuppressedSourceGenerationTests.SuppressedTypeRoundTripsThroughDynamicResolver"
     ],
     "tests_missing_vs_base": [],
     "new_build_warnings_vs_base": [
      "tests/MessagePack.SourceGenerator.ExecutionTests/SuppressedSourceGenerationTests.cs: warning SA1649: File name should match first type name (https://github.com/DotNetAnalyzers/StyleCopAnalyzers/blob/master/documentation/SA1649.md)"
     ]
    }
   ],
   "log": [
    "evidence/2234/logs/execution.ExecutionTests.full.log",
    "evidence/2234/logs/execution.MapModeExecutionTests.full.log"
   ],
   "duration_s": 1.0
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

## Files changed (4: 4 non-generated, 0 generated)
- README.md (+14 -0, doc)
- src/MessagePack.SourceGenerator/CodeAnalysis/TypeCollector.cs (+18 -4, source)
- tests/MessagePack.SourceGenerator.ExecutionTests/SuppressedSourceGenerationTests.cs (+37 -0, test)
- tests/MessagePack.SourceGenerator.Tests/SuppressSourceGenerationAnalyzerTests.cs (+193 -0, test)

## Diff (non-generated files)
```diff
diff --git a/README.md b/README.md
index c52f1088..3d37b675 100644
--- a/README.md
+++ b/README.md
@@ -1617,6 +1617,20 @@ This code generation has a minor upfront performance cost.
 > Note: When using Unity, dynamic code generation only works when targeting .NET Framework 4.x + mono runtime.
 For all other Unity targets, AOT is required.
 
+### Opting out of source generation
+
+A `[MessagePackObject]` type can opt out of source generation with `[MessagePackObject(SuppressSourceGeneration = true)]`.
+No formatter is generated for that type. It is serialized at run time by the dynamic resolvers, which use reflection, so such a type is not AOT-safe.
+
+The analyzer still validates these types, because they are serialized at run time and must still have a valid contract:
+- Members have a `[Key]` or `[IgnoreMember]` attribute ([MsgPack004](doc/analyzers/MsgPack004.md)).
+- Keys are unique and all of the same kind ([MsgPack005](doc/analyzers/MsgPack005.md)).
+- Non-public members require `AllowPrivate` ([MsgPack015](doc/analyzers/MsgPack015.md)).
+- Members have types that are themselves serializable ([MsgPack003](doc/analyzers/MsgPack003.md)).
+- Types are accessible to the resolver ([MsgPack012](doc/analyzers/MsgPack012.md)).
+
+The analyzer does not report the partial-class requirement ([MsgPack011](doc/analyzers/MsgPack011.md)) or the AOT-only checks ([MsgPack016](doc/analyzers/MsgPack016.md) and [MsgPack017](doc/analyzers/MsgPack017.md)) for these types, because they only apply when a formatter is generated.
+
 ### Customizations
 
 You can customize the generated source through properties on the `GeneratedMessagePackResolverAttribute`.

diff --git a/src/MessagePack.SourceGenerator/CodeAnalysis/TypeCollector.cs b/src/MessagePack.SourceGenerator/CodeAnalysis/TypeCollector.cs
index e121773d..470c93fc 100644
--- a/src/MessagePack.SourceGenerator/CodeAnalysis/TypeCollector.cs
+++ b/src/MessagePack.SourceGenerator/CodeAnalysis/TypeCollector.cs
@@ -1005,6 +1005,7 @@ public class TypeCollector
                         if ((isIntKey && intKey == null) || (!isIntKey && stringKey == null))
                         {
                             this.reportDiagnostic?.Invoke(Diagnostic.Create(MsgPack00xMessagePackAnalyzer.DoNotMixStringAndIntKeys, item.DeclaringSyntaxReferences.FirstOrDefault()?.GetSyntax().GetLocation()));
+                            continue; // The key kind does not match the other members; the diagnostic is reported, so skip this member.
                         }
                     }
 
@@ -1019,7 +1020,10 @@ public class TypeCollector
                         {
                             DeclaringType = GetDeclaringTypeIfColliding(item),
                         };
-                        intMembers.Add(member.IntKey, (member, item.Type));
+                        if (!intMembers.ContainsKey(member.IntKey))
+                        {
+                            intMembers.Add(member.IntKey, (member, item.Type));
+                        }
                     }
                     else if (stringKey is not null)
                     {
@@ -1032,7 +1036,10 @@ public class TypeCollector
                         {
                             DeclaringType = GetDeclaringTypeIfColliding(item),
                         };
-                        stringMembers.Add(member.StringKey, (member, item.Type));
+                        if (!stringMembers.ContainsKey(member.StringKey))
+                        {
+                            stringMembers.Add(member.StringKey, (member, item.Type));
+                        }
                     }
 
                     var messagePackFormatter = item.GetAttributes().FirstOrDefault(x => x.AttributeClass.ApproximatelyEqual(this.typeReferences.FormatterAttribute))?.ConstructorArguments[0];
@@ -1138,6 +1145,7 @@ public class TypeCollector
                         if ((isIntKey && intKey == null) || (!isIntKey && stringKey == null))
                         {
                             this.reportDiagnostic?.Invoke(Diagnostic.Create(MsgPack00xMessagePackAnalyzer.DoNotMixStringAndIntKeys, item.DeclaringSyntaxReferences.FirstOrDefault()?.GetSyntax().GetLocation()));
+                            continue; // The key kind does not match the other members; the diagnostic is reported, so skip this member.
                         }
                     }
 
@@ -1152,7 +1160,10 @@ public class TypeCollector
                         {
                             DeclaringType = GetDeclaringTypeIfColliding(item),
                         };
-                        intMembers.Add(member.IntKey, (member, item.Type));
+                        if (!intMembers.ContainsKey(member.IntKey))
+                        {
+                            intMembers.Add(member.IntKey, (member, item.Type));
+                        }
                     }
                     else
                     {
@@ -1165,7 +1176,10 @@ public class TypeCollector
                         {
                             DeclaringType = GetDeclaringTypeIfColliding(item),
                         };
-                        stringMembers.Add(member.StringKey, (member, item.Type));
+                        if (!stringMembers.ContainsKey(member.StringKey))
+                        {
+                            stringMembers.Add(member.StringKey, (member, item.Type));
+                        }
                     }
 
                     var messagePackFormatter = item.GetAttributes().FirstOrDefault(x => x.AttributeClass.ApproximatelyEqual(this.typeReferences.FormatterAttribute))?.ConstructorArguments[0];

diff --git a/tests/MessagePack.SourceGenerator.ExecutionTests/SuppressedSourceGenerationTests.cs b/tests/MessagePack.SourceGenerator.ExecutionTests/SuppressedSourceGenerationTests.cs
new file mode 100644
index 00000000..9ba87c4e
--- /dev/null
+++ b/tests/MessagePack.SourceGenerator.ExecutionTests/SuppressedSourceGenerationTests.cs
@@ -0,0 +1,37 @@
+// Copyright (c) All contributors. All rights reserved.
+// Licensed under the MIT license. See LICENSE file in the project root for full license information.
+
+/// <summary>
+/// A type that opts out of source generation (https://github.com/MessagePack-CSharp/MessagePack-CSharp/issues/2234).
+/// It must still serialize correctly through the run-time (dynamic) resolver.
+/// </summary>
+[MessagePackObject(SuppressSourceGeneration = true)]
+public class SuppressedSourceGenerationType
+{
+    [Key(0)]
+    public int Id { get; set; }
+
+    [Key(1)]
+    public string Name { get; set; } = string.Empty;
+}
+
+public class SuppressedSourceGenerationTests
+{
+    [Fact]
+    public void NoFormatterIsGeneratedForSuppressedType()
+    {
+        Assert.Null(GeneratedMessagePackResolver.Instance.GetFormatter<SuppressedSourceGenerationType>());
+    }
+
+    [Fact]
+    public void SuppressedTypeRoundTripsThroughDynamicResolver()
+    {
+        var value = new SuppressedSourceGenerationType { Id = 7, Name = "seven" };
+
+        byte[] bytes = MessagePackSerializer.Serialize(value, MessagePackSerializerOptions.Standard);
+        SuppressedSourceGenerationType result = MessagePackSerializer.Deserialize<SuppressedSourceGenerationType>(bytes, MessagePackSerializerOptions.Standard);
+
+        Assert.Equal(7, result.Id);
+        Assert.Equal("seven", result.Name);
+    }
+}

diff --git a/tests/MessagePack.SourceGenerator.Tests/SuppressSourceGenerationAnalyzerTests.cs b/tests/MessagePack.SourceGenerator.Tests/SuppressSourceGenerationAnalyzerTests.cs
new file mode 100644
index 00000000..3aa556f9
--- /dev/null
+++ b/tests/MessagePack.SourceGenerator.Tests/SuppressSourceGenerationAnalyzerTests.cs
@@ -0,0 +1,193 @@
+// Copyright (c) All contributors. All rights reserved.
+// Licensed under the MIT license. See LICENSE file in the project root for full license information.
+
+using MessagePack.Analyzers.CodeFixes;
+using Microsoft.CodeAnalysis.CSharp;
+using Microsoft.CodeAnalysis.Testing;
+using VerifyCS = CSharpCodeFixVerifier<MessagePack.SourceGenerator.Analyzers.MsgPack00xMessagePackAnalyzer, MessagePack.Analyzers.CodeFixes.MessagePackCodeFixProvider>;
+
+/// <summary>
+/// Verifies that the analyzer keeps validating <c>[MessagePackObject(SuppressSourceGeneration = true)]</c> types
+/// (https://github.com/MessagePack-CSharp/MessagePack-CSharp/issues/2234).
+/// Opting out of source generation only skips generation; the type is still serialized at run time, so its contract must still be checked.
+/// </summary>
+public class SuppressSourceGenerationAnalyzerTests
+{
+    private const string Preamble = @"
+using MessagePack;
+";
+
+    [Fact]
+    public async Task MemberWithoutKeyIsReported()
+    {
+        string input = Preamble + @"
+[MessagePackObject(SuppressSourceGeneration = true)]
+public class Foo
+{
+    public string {|MsgPack004:Member|} { get; set; }
+}
+";
+
+        await new VerifyCS.Test
+        {
+            TestCode = input,
+            MarkupOptions = MarkupOptions.UseFirstDescriptor,
+        }.RunAsync();
+    }
+
+    [Fact]
+    public async Task AllowPrivateRequiredIsReported()
+    {
+        string input = Preamble + @"
+[{|MsgPack015:MessagePackObject(SuppressSourceGeneration = true)|}]
+public class Foo
+{
+    [Key(0)]
+    private string member;
+}
+";
+
+        await new VerifyCS.Test
+        {
+            TestCode = input,
+            MarkupOptions = MarkupOptions.UseFirstDescriptor,
+        }.RunAsync();
+    }
+
+    [Fact]
+    public async Task MemberTypeMustBeMessagePackObjectIsReported()
+    {
+        string input = Preamble + @"
+public class Other
+{
+}
+
+[MessagePackObject(SuppressSourceGeneration = true)]
+public class Foo
+{
+    [Key(0)]
+    public Other {|MsgPack003:Member|} { get; set; }
+}
+";
+
+        await new VerifyCS.Test
+        {
+            TestCode = input,
+            MarkupOptions = MarkupOptions.UseFirstDescriptor,
+        }.RunAsync();
+    }
+
+    [Fact]
+    public async Task DuplicateIntKeysAreReportedWithoutAnalyzerFailure()
+    {
+        string input = Preamble + @"
+[MessagePackObject(SuppressSourceGeneration = true)]
+public class Foo
+{
+    [Key(0)]
+    public string Member1 { get; set; }
+
+    {|MsgPack005:[Key(0)]
+    public string Member2 { get; set; }|}
+}
+";
+
+        await new VerifyCS.Test
+        {
+            TestCode = input,
+            MarkupOptions = MarkupOptions.UseFirstDescriptor,
+        }.RunAsync();
+    }
+
+    [Fact]
+    public async Task DuplicateStringKeysAreReportedWithoutAnalyzerFailure()
+    {
+        string input = Preamble + @"
+[MessagePackObject(SuppressSourceGeneration = true)]
+public class Foo
+{
+    [Key(""a"")]
+    public string Member1 { get; set; }
+
+    {|MsgPack005:[Key(""a"")]
+    public string Member2 { get; set; }|}
+}
+";
+
+        await new VerifyCS.Test
+        {
+            TestCode = input,
+            MarkupOptions = MarkupOptions.UseFirstDescriptor,
+        }.RunAsync();
+    }
+
+    [Fact]
+    public async Task MixedKeyKindsAreReportedWithoutAnalyzerFailure()
+    {
+        string input = Preamble + @"
+[MessagePackObject(SuppressSourceGeneration = true)]
+public class Foo
+{
+    [Key(0)]
+    public string Member1 { get; set; }
+
+    {|MsgPack005:[Key(""Member2"")]
+    public string Member2 { get; set; }|}
+}
+";
+
+        await new VerifyCS.Test
+        {
+            TestCode = input,
+            MarkupOptions = MarkupOptions.UseFirstDescriptor,
+        }.RunAsync();
+    }
+
+    [Fact]
+    public async Task DuplicateKeysAreReportedWithoutAnalyzerFailureForGeneratedTypes()
+    {
+        string input = Preamble + @"
+[MessagePackObject]
+public class Foo
+{
+    [Key(0)]
+    public string Member1 { get; set; }
+
+    {|MsgPack005:[Key(0)]
+    public string Member2 { get; set; }|}
+}
+";
+
+        await new VerifyCS.Test
+        {
+            TestCode = input,
+            MarkupOptions = MarkupOptions.UseFirstDescriptor,
+        }.RunAsync();
+    }
+
+    [Fact]
+    public async Task SourceGenerationOnlyDiagnosticsAreNotReportedWhenSuppressed()
+    {
+        // The partial-class requirement (MsgPack011) and the AOT-only checks (MsgPack016, MsgPack017)
+        // only matter when a formatter is generated, so they are not reported for a suppressed type.
+        string input = Preamble + @"
+[MessagePackObject(AllowPrivate = true, SuppressSourceGeneration = true)]
+public class Foo
+{
+    [Key(0)]
+    private string member;
+
+    [Key(1)]
+    public string Prop1 { get; init; } = ""some default"";
+
+    [Key(2)]
+    public string Prop2 { get; set; }
+}
+";
+
+        await new VerifyCS.Test
+        {
+            TestCode = input,
+        }.RunAsync();
+    }
+}

```

## File contents (line numbers in the gutter; quote the text after '| ')

### src/MessagePack.SourceGenerator/CodeAnalysis/TypeCollector.cs at head (9007cee1), full file
```
    1| // Copyright (c) All contributors. All rights reserved.
    2| // Licensed under the MIT license. See LICENSE file in the project root for full license information.
    3| 
    4| #pragma warning disable SA1402 // File may only contain a single type
    5| #pragma warning disable SA1649 // File name should match first type name
    6| 
    7| using System.Collections.Immutable;
    8| using System.Reflection;
    9| using System.Text.RegularExpressions;
   10| using Microsoft.CodeAnalysis;
   11| using Microsoft.CodeAnalysis.CSharp;
   12| using Microsoft.CodeAnalysis.CSharp.Syntax;
   13| 
   14| namespace MessagePack.SourceGenerator.CodeAnalysis;
   15| 
   16| public class MessagePackGeneratorResolveFailedException : Exception
   17| {
   18|     public MessagePackGeneratorResolveFailedException(string message)
   19|         : base(message)
   20|     {
   21|     }
   22| }
   23| 
   24| public class TypeCollector
   25| {
   26|     private static readonly SymbolDisplayFormat BinaryWriteFormat = new SymbolDisplayFormat(
   27|         genericsOptions: SymbolDisplayGenericsOptions.IncludeTypeParameters,
   28|         miscellaneousOptions: SymbolDisplayMiscellaneousOptions.ExpandNullable,
   29|         typeQualificationStyle: SymbolDisplayTypeQualificationStyle.NameOnly);
   30| 
   31|     private static readonly SymbolDisplayFormat ShortTypeNameFormat = new SymbolDisplayFormat(
   32|             typeQualificationStyle: SymbolDisplayTypeQualificationStyle.NameAndContainingTypes);
   33| 
   34|     private static readonly HashSet<string> EmbeddedTypes = new(new[]
   35|     {
   36|         "short",
   37|         "int",
   38|         "long",
   39|         "ushort",
   40|         "uint",
   41|         "ulong",
   42|         "float",
   43|         "double",
   44|         "bool",
   45|         "byte",
   46|         "sbyte",
   47|         "decimal",
   48|         "char",
   49|         "string",
   50|         "object",
   51|         "System.Guid",
   52|         "System.TimeSpan",
   53|         "System.DateTime",
   54|         "System.DateTimeOffset",
   55| 
   56|         "MessagePack.Nil",
   57| 
   58|         // and arrays
   59|         "short[]",
   60|         "int[]",
   61|         "long[]",
   62|         "ushort[]",
   63|         "uint[]",
   64|         "ulong[]",
   65|         "float[]",
   66|         "double[]",
   67|         "bool[]",
   68|         "byte[]",
   69|         "sbyte[]",
   70|         "decimal[]",
   71|         "char[]",
   72|         "string[]",
   73|         "object[]",
   74|         "System.DateTime[]",
   75|         "System.ArraySegment<byte>",
   76|         "System.Memory<byte>",
   77|         "System.ReadOnlyMemory<byte>",
   78|         "System.Buffers.ReadOnlySequence<byte>",
   79| 
   80|         // List
   81|         "System.Collections.Generic.List<short>",
   82|         "System.Collections.Generic.List<int>",
   83|         "System.Collections.Generic.List<long>",
   84|         "System.Collections.Generic.List<ushort>",
   85|         "System.Collections.Generic.List<uint>",
   86|         "System.Collections.Generic.List<ulong>",
   87|         "System.Collections.Generic.List<float>",
   88|         "System.Collections.Generic.List<double>",
   89|         "System.Collections.Generic.List<bool>",
   90|         "System.Collections.Generic.List<byte>",
   91|         "System.Collections.Generic.List<sbyte>",
   92|         "System.Collections.Generic.List<char>",
   93|         "System.Collections.Generic.List<string>",
   94|         "System.Collections.Generic.List<object>",
   95|         "System.Collections.Generic.List<System.DateTime>",
   96| 
   97|         // extensions
   98|         "UnityEngine.Vector2",
   99|         "UnityEngine.Vector3",
  100|         "UnityEngine.Vector4",
  101|         "UnityEngine.Quaternion",
  102|         "UnityEngine.Color",
  103|         "UnityEngine.Bounds",
  104|         "UnityEngine.Rect",
  105|         "UnityEngine.AnimationCurve",
  106|         "UnityEngine.RectOffset",
  107|         "UnityEngine.Gradient",
  108|         "UnityEngine.WrapMode",
  109|         "UnityEngine.GradientMode",
  110|         "UnityEngine.Keyframe",
  111|         "UnityEngine.Matrix4x4",
  112|         "UnityEngine.GradientColorKey",
  113|         "UnityEngine.GradientAlphaKey",
  114|         "UnityEngine.Color32",
  115|         "UnityEngine.LayerMask",
  116|         "UnityEngine.Vector2Int",
  117|         "UnityEngine.Vector3Int",
  118|         "UnityEngine.RangeInt",
  119|         "UnityEngine.RectInt",
  120|         "UnityEngine.BoundsInt",
  121| 
  122|         "System.Reactive.Unit",
  123| 
  124|         "System.Numerics.BigInteger",
  125|         "System.Numerics.Complex",
  126|         "System.Numerics.Vector2",
  127|         "System.Numerics.Vector3",
  128|         "System.Numerics.Vector4",
  129|         "System.Numerics.Quaternion",
  130|         "System.Numerics.Matrix3x2",
  131|         "System.Numerics.Matrix4x4",
  132|     });
  133| 
  134|     private static readonly Dictionary<string, string> KnownGenericTypes = new()
  135|     {
  136| #pragma warning disable SA1509 // Opening braces should not be preceded by blank line
  137|         { "System.Collections.Generic.List<>", "MsgPack::Formatters.ListFormatter" },
  138|         { "System.Collections.Generic.LinkedList<>", "MsgPack::Formatters.LinkedListFormatter" },
  139|         { "System.Collections.Generic.Queue<>", "MsgPack::Formatters.QueueFormatter" },
  140|         { "System.Collections.Generic.Stack<>", "MsgPack::Formatters.StackFormatter" },
  141|         { "System.Collections.Generic.HashSet<>", "MsgPack::Formatters.HashSetFormatter" },
  142|         { "System.Collections.ObjectModel.ReadOnlyCollection<>", "MsgPack::Formatters.ReadOnlyCollectionFormatter" },
  143|         { "System.Collections.Generic.IList<>", "MsgPack::Formatters.InterfaceListFormatter2" },
  144|         { "System.Collections.Generic.ICollection<>", "MsgPack::Formatters.InterfaceCollectionFormatter2" },
  145|         { "System.Collections.Generic.IEnumerable<>", "MsgPack::Formatters.InterfaceEnumerableFormatter" },
  146|         { "System.Collections.Generic.Dictionary<,>", "MsgPack::Formatters.DictionaryFormatter" },
  147|         { "System.Collections.Generic.IDictionary<,>", "MsgPack::Formatters.InterfaceDictionaryFormatter" },
  148|         { "System.Collections.Generic.SortedDictionary<,>", "MsgPack::Formatters.SortedDictionaryFormatter" },
  149|         { "System.Collections.Generic.SortedList<,>", "MsgPack::Formatters.SortedListFormatter" },
  150|         { "System.Linq.ILookup<,>", "MsgPack::Formatters.InterfaceLookupFormatter" },
  151|         { "System.Linq.IGrouping<,>", "MsgPack::Formatters.InterfaceGroupingFormatter" },
  152|         { "System.Collections.ObjectModel.ObservableCollection<>", "MsgPack::Formatters.ObservableCollectionFormatter" },
  153|         { "System.Collections.ObjectModel.ReadOnlyObservableCollection<>", "MsgPack::Formatters.ReadOnlyObservableCollectionFormatter" },
  154|         { "System.Collections.Generic.IReadOnlyList<>", "MsgPack::Formatters.InterfaceReadOnlyListFormatter" },
  155|         { "System.Collections.Generic.IReadOnlyCollection<>", "MsgPack::Formatters.InterfaceReadOnlyCollectionFormatter" },
  156|         { "System.Collections.Generic.ISet<>", "MsgPack::Formatters.InterfaceSetFormatter" },
  157|         { "System.Collections.Concurrent.ConcurrentBag<>", "MsgPack::Formatters.ConcurrentBagFormatter" },
  158|         { "System.Collections.Concurrent.ConcurrentQueue<>", "MsgPack::Formatters.ConcurrentQueueFormatter" },
  159|         { "System.Collections.Concurrent.ConcurrentStack<>", "MsgPack::Formatters.ConcurrentStackFormatter" },
  160|         { "System.Collections.ObjectModel.ReadOnlyDictionary<,>", "MsgPack::Formatters.ReadOnlyDictionaryFormatter" },
  161|         { "System.Collections.Generic.IReadOnlyDictionary<,>", "MsgPack::Formatters.InterfaceReadOnlyDictionaryFormatter" },
  162|         { "System.Collections.Concurrent.ConcurrentDictionary<,>", "MsgPack::Formatters.ConcurrentDictionaryFormatter" },
  163|         { "System.Lazy<>", "MsgPack::Formatters.LazyFormatter" },
  164|         { "System.Threading.Tasks<>", "MsgPack::Formatters.TaskValueFormatter" },
  165| 
  166|         { "System.Tuple<>", "MsgPack::Formatters.TupleFormatter" },
  167|         { "System.Tuple<,>", "MsgPack::Formatters.TupleFormatter" },
  168|         { "System.Tuple<,,>", "MsgPack::Formatters.TupleFormatter" },
  169|         { "System.Tuple<,,,>", "MsgPack::Formatters.TupleFormatter" },
  170|         { "System.Tuple<,,,,>", "MsgPack::Formatters.TupleFormatter" },
  171|         { "System.Tuple<,,,,,>", "MsgPack::Formatters.TupleFormatter" },
  172|         { "System.Tuple<,,,,,,>", "MsgPack::Formatters.TupleFormatter" },
  173|         { "System.Tuple<,,,,,,,>", "MsgPack::Formatters.TupleFormatter" },
  174| 
  175|         { "System.ValueTuple<>", "MsgPack::Formatters.ValueTupleFormatter" },
  176|         { "System.ValueTuple<,>", "MsgPack::Formatters.ValueTupleFormatter" },
  177|         { "System.ValueTuple<,,>", "MsgPack::Formatters.ValueTupleFormatter" },
  178|         { "System.ValueTuple<,,,>", "MsgPack::Formatters.ValueTupleFormatter" },
  179|         { "System.ValueTuple<,,,,>", "MsgPack::Formatters.ValueTupleFormatter" },
  180|         { "System.ValueTuple<,,,,,>", "MsgPack::Formatters.ValueTupleFormatter" },
  181|         { "System.ValueTuple<,,,,,,>", "MsgPack::Formatters.ValueTupleFormatter" },
  182|         { "System.ValueTuple<,,,,,,,>", "MsgPack::Formatters.ValueTupleFormatter" },
  183| 
  184|         { "System.Collections.Generic.KeyValuePair<,>", "MsgPack::Formatters.KeyValuePairFormatter" },
  185|         { "System.Threading.Tasks.ValueTask<>", "MsgPack::Formatters.KeyValuePairFormatter" },
  186|         { "System.ArraySegment<>", "MsgPack::Formatters.ArraySegmentFormatter" },
  187|         { "System.Memory<>", "MsgPack::Formatters.MemoryFormatter" },
  188|         { "System.ReadOnlyMemory<>", "MsgPack::Formatters.ReadOnlyMemoryFormatter" },
  189|         { "System.Buffers.ReadOnlySequence<>", "MsgPack::Formatters.ReadOnlySequenceFormatter" },
  190| 
  191|         // extensions
  192|         { "System.Collections.Immutable.ImmutableArray<>", "MsgPack::ImmutableCollection.ImmutableArrayFormatter" },
  193|         { "System.Collections.Immutable.ImmutableList<>", "MsgPack::ImmutableCollection.ImmutableListFormatter" },
  194|         { "System.Collections.Immutable.ImmutableDictionary<,>", "MsgPack::ImmutableCollection.ImmutableDictionaryFormatter" },
  195|         { "System.Collections.Immutable.ImmutableHashSet<>", "MsgPack::ImmutableCollection.ImmutableHashSetFormatter" },
  196|         { "System.Collections.Immutable.ImmutableSortedDictionary<,>", "MsgPack::ImmutableCollection.ImmutableSortedDictionaryFormatter" },
  197|         { "System.Collections.Immutable.ImmutableSortedSet<>", "MsgPack::ImmutableCollection.ImmutableSortedSetFormatter" },
  198|         { "System.Collections.Immutable.ImmutableQueue<>", "MsgPack::ImmutableCollection.ImmutableQueueFormatter" },
  199|         { "System.Collections.Immutable.ImmutableStack<>", "MsgPack::ImmutableCollection.ImmutableStackFormatter" },
  200|         { "System.Collections.Immutable.IImmutableList<>", "MsgPack::ImmutableCollection.InterfaceImmutableListFormatter" },
  201|         { "System.Collections.Immutable.IImmutableDictionary<,>", "MsgPack::ImmutableCollection.InterfaceImmutableDictionaryFormatter" },
  202|         { "System.Collections.Immutable.IImmutableQueue<>", "MsgPack::ImmutableCollection.InterfaceImmutableQueueFormatter" },
  203|         { "System.Collections.Immutable.IImmutableSet<>", "MsgPack::ImmutableCollection.InterfaceImmutableSetFormatter" },
  204|         { "System.Collections.Immutable.IImmutableStack<>", "MsgPack::ImmutableCollection.InterfaceImmutableStackFormatter" },
  205| 
  206|         { "Reactive.Bindings.ReactiveProperty<>", "MsgPack::ReactivePropertyExtension.ReactivePropertyFormatter" },
  207|         { "Reactive.Bindings.IReactiveProperty<>", "MsgPack::ReactivePropertyExtension.InterfaceReactivePropertyFormatter" },
  208|         { "Reactive.Bindings.IReadOnlyReactiveProperty<>", "MsgPack::ReactivePropertyExtension.InterfaceReadOnlyReactivePropertyFormatter" },
  209|         { "Reactive.Bindings.ReactiveCollection<>", "MsgPack::ReactivePropertyExtension.ReactiveCollectionFormatter" },
  210| #pragma warning restore SA1509 // Opening braces should not be preceded by blank line
  211|     };
  212| 
  213|     private readonly AnalyzerOptions options;
  214|     private readonly ReferenceSymbols typeReferences;
  215| 
  216|     /// <summary>
  217|     /// The means of reporting diagnostics to the analyzer.
  218|     /// This will be <see langword="null" /> when running in the context of a source generator so as to avoid duplicate diagnostics.
  219|     /// </summary>
  220|     private readonly Action<Diagnostic>? reportDiagnostic;
  221| 
  222|     private readonly ITypeSymbol? targetType;
  223| 
  224|     // visitor workspace:
  225|     private readonly HashSet<ITypeSymbol> alreadyCollected = new(SymbolEqualityComparer.Default);
  226|     private readonly ImmutableSortedSet<ObjectSerializationInfo>.Builder collectedObjectInfo = ImmutableSortedSet.CreateBuilder<ObjectSerializationInfo>(ResolverRegisterInfoComparer.Default);
  227|     private readonly ImmutableSortedSet<EnumSerializationInfo>.Builder collectedEnumInfo = ImmutableSortedSet.CreateBuilder<EnumSerializationInfo>(ResolverRegisterInfoComparer.Default);
  228|     private readonly ImmutableSortedSet<GenericSerializationInfo>.Builder collectedGenericInfo = ImmutableSortedSet.CreateBuilder<GenericSerializationInfo>(ResolverRegisterInfoComparer.Default);
  229|     private readonly ImmutableSortedSet<UnionSerializationInfo>.Builder collectedUnionInfo = ImmutableSortedSet.CreateBuilder<UnionSerializationInfo>(ResolverRegisterInfoComparer.Default);
  230|     private readonly ImmutableSortedSet<ResolverRegisterInfo>.Builder collectedArrayInfo = ImmutableSortedSet.CreateBuilder<ResolverRegisterInfo>(ResolverRegisterInfoComparer.Default);
  231| 
  232|     private readonly Compilation compilation;
  233| 
  234|     private readonly CancellationToken cancellationToken;
  235| 
  236|     private TypeCollector(Compilation compilation, AnalyzerOptions options, ReferenceSymbols referenceSymbols, ITypeSymbol targetType, Action<Diagnostic>? reportAnalyzerDiagnostic, CancellationToken cancellationToken)
  237|     {
  238|         this.typeReferences = referenceSymbols;
  239|         this.reportDiagnostic = reportAnalyzerDiagnostic;
  240|         this.options = options;
  241|         this.compilation = compilation;
  242|         this.cancellationToken = cancellationToken;
  243| 
  244|         bool isInaccessible = false;
  245|         foreach (BaseTypeDeclarationSyntax? decl in CodeAnalysisUtilities.FindInaccessibleTypes(targetType))
  246|         {
  247|             isInaccessible = true;
  248|             reportAnalyzerDiagnostic?.Invoke(Diagnostic.Create(MsgPack00xMessagePackAnalyzer.InaccessibleDataType, decl.Identifier.GetLocation()));
  249|         }
  250| 
  251|         if (!isInaccessible)
  252|         {
  253|             if (((targetType.TypeKind == TypeKind.Interface) && targetType.GetAttributes().Any(x2 => x2.AttributeClass.ApproximatelyEqual(this.typeReferences.UnionAttribute)))
  254|                 || ((targetType.TypeKind == TypeKind.Class && targetType.IsAbstract) && targetType.GetAttributes().Any(x2 => x2.AttributeClass.ApproximatelyEqual(this.typeReferences.UnionAttribute)))
  255|                 || ((targetType.TypeKind == TypeKind.Class) && targetType.GetAttributes().Any(x2 => x2.AttributeClass.ApproximatelyEqual(this.typeReferences.MessagePackObjectAttribute)))
  256|                 || ((targetType.TypeKind == TypeKind.Struct) && targetType.GetAttributes().Any(x2 => x2.AttributeClass.ApproximatelyEqual(this.typeReferences.MessagePackObjectAttribute))))
  257|             {
  258|                 this.targetType = targetType;
  259|             }
  260|         }
  261|     }
  262| 
  263|     public static FullModel? Collect(Compilation compilation, AnalyzerOptions options, ReferenceSymbols referenceSymbols, Action<Diagnostic>? reportAnalyzerDiagnostic, ITypeSymbol targetType, CancellationToken cancellationToken)
  264|     {
  265|         TypeCollector collector = new(compilation, options, referenceSymbols, targetType, reportAnalyzerDiagnostic, cancellationToken);
  266|         if (collector.targetType is null)
  267|         {
  268|             return null;
  269|         }
  270| 
  271|         FullModel model = collector.Collect();
  272|         return model;
  273|     }
  274| 
  275|     private void ResetWorkspace()
  276|     {
  277|         this.alreadyCollected.Clear();
  278|         this.collectedObjectInfo.Clear();
  279|         this.collectedEnumInfo.Clear();
  280|         this.collectedGenericInfo.Clear();
  281|         this.collectedUnionInfo.Clear();
  282|         this.collectedArrayInfo.Clear();
  283|     }
  284| 
  285|     // EntryPoint
  286|     public FullModel Collect()
  287|     {
  288|         this.ResetWorkspace();
  289| 
  290|         if (this.targetType is not null)
  291|         {
  292|             this.CollectCore(this.targetType);
  293|         }
  294| 
  295|         return new FullModel(
  296|             this.collectedObjectInfo.ToImmutable(),
  297|             this.collectedEnumInfo.ToImmutable(),
  298|             this.collectedGenericInfo.ToImmutable(),
  299|             this.collectedUnionInfo.ToImmutable(),
  300|             ImmutableSortedSet<CustomFormatterRegisterInfo>.Empty,
  301|             this.collectedArrayInfo.ToImmutable(),
  302|             this.options);
  303|     }
  304| 
  305|     // Gate of recursive collect
  306|     private void CollectCore(ITypeSymbol typeSymbol, ISymbol? callerSymbol = null)
  307|     {
  308|         this.cancellationToken.ThrowIfCancellationRequested();
  309| 
  310|         if (!this.alreadyCollected.Add(typeSymbol))
  311|         {
  312|             return;
  313|         }
  314| 
  315|         var typeSymbolString = typeSymbol.WithNullableAnnotation(NullableAnnotation.NotAnnotated).ToString();
  316|         if (!string.IsNullOrEmpty(typeSymbolString) && EmbeddedTypes.Contains(typeSymbolString))
  317|         {
  318|             return;
  319|         }
  320| 
  321|         FormattableType formattableType = new(typeSymbol, null);
  322|         if (this.options.AssumedFormattableTypes.Contains(formattableType) || this.options.AssumedFormattableTypes.Contains(formattableType with { IsFormatterInSameAssembly = true }))
  323|         {
  324|             return;
  325|         }
  326| 
  327|         if (typeSymbol is IArrayTypeSymbol arrayTypeSymbol)
  328|         {
  329|             this.CollectArray((IArrayTypeSymbol)this.ToTupleUnderlyingType(arrayTypeSymbol), callerSymbol);
  330|             return;
  331|         }
  332| 
  333|         if (typeSymbol is ITypeParameterSymbol)
  334|         {
  335|             return;
  336|         }
  337| 
  338|         if (!IsAllowAccessibility(typeSymbol))
  339|         {
  340|             return;
  341|         }
  342| 
  343|         if (!(typeSymbol is INamedTypeSymbol type))
  344|         {
  345|             return;
  346|         }
  347| 
  348|         var customFormatterAttr = typeSymbol.GetAttributes().FirstOrDefault(x => x.AttributeClass.ApproximatelyEqual(this.typeReferences.FormatterAttribute));
  349|         if (customFormatterAttr != null)
  350|         {
  351|             this.CheckValidMessagePackFormatterAttribute(customFormatterAttr);
  352|             return;
  353|         }
  354| 
  355|         if (type.EnumUnderlyingType != null)
  356|         {
  357|             this.CollectEnum(type, type.EnumUnderlyingType);
  358|             return;
  359|         }
  360| 
  361|         if (type.IsGenericType)
  362|         {
  363|             this.CollectGeneric((INamedTypeSymbol)this.ToTupleUnderlyingType(type), callerSymbol);
  364|             return;
  365|         }
  366| 
  367|         if (type.Locations[0].IsInMetadata)
  368|         {
  369|             return;
  370|         }
  371| 
  372|         if (type.TypeKind == TypeKind.Interface || (type.TypeKind == TypeKind.Class && type.IsAbstract))
  373|         {
  374|             this.CollectUnion(type);
  375|             return;
  376|         }
  377| 
  378|         this.CollectObject(type, callerSymbol);
  379|     }
  380| 
  381|     private void CollectEnum(INamedTypeSymbol type, ISymbol enumUnderlyingType)
  382|     {
  383|         this.collectedEnumInfo.Add(EnumSerializationInfo.Create(type, enumUnderlyingType, this.options.Generator.Resolver));
  384|     }
  385| 
  386|     private void CollectUnion(INamedTypeSymbol type)
  387|     {
  388|         if (!options.IsGeneratingSource)
  389|         {
  390|             // In analyzer-only mode, this method doesn't work.
  391|             return;
  392|         }
  393| 
  394|         ImmutableArray<TypedConstant>[] unionAttrs = type.GetAttributes().Where(x => x.AttributeClass.ApproximatelyEqual(this.typeReferences.UnionAttribute)).Select(x => x.ConstructorArguments).ToArray();
  395|         if (unionAttrs.Length == 0)
  396|         {
  397|             this.reportDiagnostic?.Invoke(Diagnostic.Create(MsgPack00xMessagePackAnalyzer.UnionAttributeRequired, type.DeclaringSyntaxReferences.FirstOrDefault()?.GetSyntax().GetLocation()));
  398|         }
  399| 
  400|         // 0, Int  1, SubType
  401|         UnionSubTypeInfo? UnionSubTypeInfoSelector(ImmutableArray<TypedConstant> x)
  402|         {
  403|             if (!(x[0] is { Value: int key }) || !(x[1] is { Value: ITypeSymbol typeSymbol }))
  404|             {
  405|                 this.reportDiagnostic?.Invoke(Diagnostic.Create(MsgPack00xMessagePackAnalyzer.AotUnionAttributeRequiresTypeArg, GetIdentifierLocation(type)));
  406|                 return null;
  407|             }
  408| 
  409|             CollectCore(typeSymbol);
  410| 
  411|             var typeName = typeSymbol.ToDisplayString(SymbolDisplayFormat.FullyQualifiedFormat);
  412|             return new UnionSubTypeInfo(key, typeName);
  413|         }
  414| 
  415|         var info = UnionSerializationInfo.Create(
  416|             type,
  417|             unionAttrs.Select(UnionSubTypeInfoSelector).Where(i => i is not null).OrderBy(x => x!.Key).ToImmutableArray()!,
  418|             this.options.Generator.Resolver);
  419| 
  420|         this.collectedUnionInfo.Add(info);
  421|     }
  422| 
  423|     private void CollectGenericUnion(INamedTypeSymbol type)
  424|     {
  425|         var unionAttrs = type.GetAttributes().Where(x => x.AttributeClass.ApproximatelyEqual(this.typeReferences.UnionAttribute)).Select(x => x.ConstructorArguments);
  426|         using var enumerator = unionAttrs.GetEnumerator();
  427|         if (!enumerator.MoveNext())
  428|         {
  429|             return;
  430|         }
  431| 
  432|         do
  433|         {
  434|             var x = enumerator.Current;
  435|             if (x[1] is { Value: INamedTypeSymbol unionType } && !this.alreadyCollected.Contains(unionType))
  436|             {
  437|                 this.CollectCore(unionType);
  438|             }
  439|         }
  440|         while (enumerator.MoveNext());
  441|     }
  442| 
  443|     private void CollectArray(IArrayTypeSymbol array, ISymbol? callerSymbol)
  444|     {
  445|         ITypeSymbol elemType = array.ElementType;
  446| 
  447|         this.CollectCore(elemType, callerSymbol);
  448| 
  449|         if (elemType is ITypeParameterSymbol || (elemType is INamedTypeSymbol symbol && IsOpenGenericTypeRecursively(symbol)))
  450|         {
  451|             return;
  452|         }
  453| 
  454|         QualifiedTypeName elementTypeName = QualifiedTypeName.Create(elemType);
  455|         string? formatterName = array.Rank switch
  456|         {
  457|             1 => "ArrayFormatter",
  458|             2 => "TwoDimensionalArrayFormatter",
  459|             3 => "ThreeDimensionalArrayFormatter",
  460|             4 => "FourDimensionalArrayFormatter",
  461|             _ => null,
  462|         };
  463|         if (formatterName is null)
  464|         {
  465|             ////this.reportDiagnostic?.Invoke(Diagnostic.Create(MsgPack00xMessagePackAnalyzer.AotArrayRankTooHigh));
  466|             return;
  467|         }
  468| 
  469|         var info = ResolverRegisterInfo.CreateArray(array, this.options.Generator.Resolver) with
  470|         {
  471|             Formatter = new QualifiedNamedTypeName(TypeKind.Class)
  472|             {
  473|                 Container = new NamespaceTypeContainer("MsgPack::Formatters"),
  474|                 Name = formatterName,
  475|                 TypeParameters = ImmutableArray.Create(new GenericTypeParameterInfo("T")),
  476|                 TypeArguments = ImmutableArray.Create(elementTypeName),
  477|             },
  478|         };
  479|         this.collectedArrayInfo.Add(info);
  480|     }
  481| 
  482|     private ITypeSymbol ToTupleUnderlyingType(ITypeSymbol typeSymbol)
  483|     {
  484|         if (typeSymbol is IArrayTypeSymbol array)
  485|         {
  486|             return this.compilation.CreateArrayTypeSymbol(this.ToTupleUnderlyingType(array.ElementType), array.Rank);
  487|         }
  488| 
  489|         if (typeSymbol is not INamedTypeSymbol namedType || !namedType.IsGenericType)
  490|         {
  491|             return typeSymbol;
  492|         }
  493| 
  494|         namedType = namedType.TupleUnderlyingType ?? namedType;
  495|         var newTypeArguments = namedType.TypeArguments.Select(this.ToTupleUnderlyingType).ToArray();
  496|         if (!namedType.TypeArguments.SequenceEqual(newTypeArguments))
  497|         {
  498|             return namedType.ConstructedFrom.Construct(newTypeArguments);
  499|         }
  500| 
  501|         return namedType;
  502|     }
  503| 
  504|     private void CollectGeneric(INamedTypeSymbol type, ISymbol? callerSymbol)
  505|     {
  506|         INamedTypeSymbol typeDefinition = type.ConstructUnboundGenericType();
  507|         var genericTypeDefinitionString = typeDefinition.ToDisplayString();
  508|         string? genericTypeNamespace = type.ContainingNamespace?.ToDisplayString(SymbolDisplayFormat.MinimallyQualifiedFormat);
  509|         var fullName = type.ToDisplayString(SymbolDisplayFormat.FullyQualifiedFormat);
  510|         var isOpenGenericType = IsOpenGenericTypeRecursively(type);
  511|         string formattedTypeFullName = type.ToDisplayString(SymbolDisplayFormat.FullyQualifiedFormat);
  512|         string? formatterName;
  513| 
  514|         // nullable
  515|         if (genericTypeDefinitionString == "T?")
  516|         {
  517|             var firstTypeArgument = type.TypeArguments[0];
  518| 
  519|             if (EmbeddedTypes.Contains(firstTypeArgument.ToString()!))
  520|             {
  521|                 return;
  522|             }
  523| 
  524|             this.CollectCore(firstTypeArgument, callerSymbol);
  525| 
  526|             if (!isOpenGenericType)
  527|             {
  528|                 formatterName = $"NullableFormatter<{firstTypeArgument.ToDisplayString(SymbolDisplayFormat.FullyQualifiedFormat)}>";
  529|                 var info = GenericSerializationInfo.Create(type, this.options.Generator.Resolver) with
  530|                 {
  531|                     Formatter = new QualifiedNamedTypeName(TypeKind.Class)
  532|                     {
  533|                         Name = formatterName,
  534|                         Container = new NamespaceTypeContainer("MsgPack::Formatters"),
  535|                     },
  536|                 };
  537|                 this.collectedGenericInfo.Add(info);
  538|             }
  539| 
  540|             return;
  541|         }
  542| 
  543|         // collection
  544|         string? formatterFullName;
  545|         if (KnownGenericTypes.TryGetValue(genericTypeDefinitionString, out formatterFullName))
  546|         {
  547|             foreach (ITypeSymbol item in type.TypeArguments)
  548|             {
  549|                 this.CollectCore(item, callerSymbol);
  550|             }
  551| 
  552|             GenericSerializationInfo info;
  553| 
  554|             if (isOpenGenericType)
  555|             {
  556|                 return;
  557|             }
  558|             else
  559|             {
  560|                 info = GenericSerializationInfo.Create(type, this.options.Generator.Resolver);
  561|                 int indexOfLastPeriod = formatterFullName.LastIndexOf('.');
  562|                 info = info with
  563|                 {
  564|                     Formatter = new(TypeKind.Class)
  565|                     {
  566|                         Container = new NamespaceTypeContainer(formatterFullName.Substring(0, indexOfLastPeriod)),
  567|                         Name = formatterFullName.Substring(indexOfLastPeriod + 1),
  568|                         TypeParameters = GetTypeParameters(info.DataType),
  569|                         TypeArguments = GetTypeArguments(info.DataType),
  570|                     },
  571|                 };
  572| 
  573|                 this.collectedGenericInfo.Add(info);
  574|             }
  575| 
  576|             if (genericTypeDefinitionString != "System.Linq.ILookup<,>")
  577|             {
  578|                 return;
  579|             }
  580| 
  581|             formatterName = KnownGenericTypes["System.Linq.IGrouping<,>"];
  582| 
  583|             var groupingInfo = GenericSerializationInfo.Create(type, this.options.Generator.Resolver);
  584|             groupingInfo = groupingInfo with
  585|             {
  586|                 DataType = new QualifiedNamedTypeName(TypeKind.Interface)
  587|                 {
  588|                     Container = new NamespaceTypeContainer("global::System.Linq"),
  589|                     Name = "IGrouping",
  590|                     TypeParameters = GetTypeParameters(info.DataType),
  591|                 },
  592|                 Formatter = groupingInfo.Formatter with { Name = formatterName },
  593|             };
  594|             this.collectedGenericInfo.Add(groupingInfo);
  595| 
  596|             formatterName = KnownGenericTypes["System.Collections.Generic.IEnumerable<>"];
  597| 
  598|             GenericSerializationInfo enumerableInfo = GenericSerializationInfo.Create(type, this.options.Generator.Resolver);
  599|             enumerableInfo = enumerableInfo with
  600|             {
  601|                 DataType = new QualifiedNamedTypeName(TypeKind.Interface)
  602|                 {
  603|                     Container = new NamespaceTypeContainer("System.Collections.Generic"),
  604|                     Name = "IEnumerable",
  605|                     TypeParameters = ImmutableArray.Create(GetTypeParameters(info.DataType)[1]),
  606|                 },
  607|                 Formatter = enumerableInfo.Formatter with { Name = formatterName },
  608|             };
  609|             this.collectedGenericInfo.Add(enumerableInfo);
  610|             return;
  611|         }
  612| 
  613|         if (type.AllInterfaces.FirstOrDefault(x => !x.IsUnboundGenericType && x.ConstructUnboundGenericType() is { Name: nameof(ICollection<int>) }) is INamedTypeSymbol collectionIface
  614|             && type.InstanceConstructors.Any(ctor => ctor.Parameters.Length == 0))
  615|         {
  616|             this.CollectCore(collectionIface.TypeArguments[0], callerSymbol);
  617| 
  618|             if (isOpenGenericType)
  619|             {
  620|                 return;
  621|             }
  622|             else
  623|             {
  624|                 GenericSerializationInfo info = GenericSerializationInfo.Create(type, this.options.Generator.Resolver) with
  625|                 {
  626|                     Formatter = new(TypeKind.Class)
  627|                     {
  628|                         Container = new NamespaceTypeContainer("MsgPack::Formatters"),
  629|                         Name = "GenericCollectionFormatter",
  630|                         TypeParameters = ImmutableArray.Create<GenericTypeParameterInfo>(new("TElement"), new("TCollection")),
  631|                         TypeArguments = ImmutableArray.Create<QualifiedTypeName>(QualifiedTypeName.Create(collectionIface.TypeArguments[0]), QualifiedTypeName.Create(type)),
  632|                     },
  633|                 };
  634| 
  635|                 this.collectedGenericInfo.Add(info);
  636|                 return;
  637|             }
  638|         }
  639| 
  640|         // Generic types
  641|         if (type.IsDefinition)
  642|         {
  643|             this.CollectGenericUnion(type);
  644|             this.CollectObject(type, callerSymbol);
  645|         }
  646|         else
  647|         {
  648|             // Collect substituted types for the properties and fields.
  649|             // NOTE: It is used to register formatters from nested generic type.
  650|             //       However, closed generic types such as `Foo<string>` are not registered as a formatter.
  651|             this.GetObjectInfo(type, callerSymbol);
  652| 
  653|             // Collect generic type definition, that is not collected when it is defined outside target project.
  654|             this.CollectCore(type.OriginalDefinition, callerSymbol);
  655|         }
  656| 
  657|         // Collect substituted types for the type parameters (e.g. Bar in Foo<Bar>)
  658|         foreach (var item in type.TypeArguments)
  659|         {
  660|             this.CollectCore(item, callerSymbol);
  661|         }
  662| 
  663|         if (!isOpenGenericType)
  664|         {
  665|             GenericSerializationInfo genericSerializationInfo = GenericSerializationInfo.Create(type, this.options.Generator.Resolver);
  666|             this.collectedGenericInfo.Add(genericSerializationInfo);
  667|         }
  668| 
  669|         static ImmutableArray<GenericTypeParameterInfo> GetTypeParameters(QualifiedTypeName qtn)
  670|             => qtn is QualifiedNamedTypeName named ? named.TypeParameters : ImmutableArray<GenericTypeParameterInfo>.Empty;
  671| 
  672|         static ImmutableArray<QualifiedTypeName> GetTypeArguments(QualifiedTypeName qtn)
  673|             => qtn is QualifiedNamedTypeName named ? named.TypeArguments : ImmutableArray<QualifiedTypeName>.Empty;
  674|     }
  675| 
  676|     private void CollectObject(INamedTypeSymbol type, ISymbol? callerSymbol)
  677|     {
  678|         ObjectSerializationInfo? info = this.GetObjectInfo(type, callerSymbol);
  679|         if (info is not null)
  680|         {
  681|             this.collectedObjectInfo.Add(info);
  682|         }
  683|     }
  684| 
  685|     private void CheckValidMessagePackFormatterAttribute(AttributeData formatterAttribute)
  686|     {
  687|         if (formatterAttribute.ConstructorArguments[0].Value is ITypeSymbol formatterType)
  688|         {
  689|             // Validate that the typed formatter is actually of `IMessagePackFormatter`
  690|             bool isMessagePackFormatter = formatterType.AllInterfaces.Any(x => SymbolEqualityComparer.Default.Equals(x, this.typeReferences.MessagePackFormatter));
  691|             if (!isMessagePackFormatter)
  692|             {
  693|                 Location? location = ((AttributeSyntax?)formatterAttribute.ApplicationSyntaxReference?.GetSyntax())?.ArgumentList?.Arguments[0].GetLocation();
  694|                 ImmutableDictionary<string, string?> typeInfo = ImmutableDictionary.Create<string, string?>().Add("type", formatterType.ToDisplayString(SymbolDisplayFormat.FullyQualifiedFormat));
  695|                 this.reportDiagnostic?.Invoke(Diagnostic.Create(MsgPack00xMessagePackAnalyzer.MessageFormatterMustBeMessagePackFormatter, location, typeInfo));
  696|             }
  697|         }
  698|     }
  699| 
  700|     private ObjectSerializationInfo? GetObjectInfo(INamedTypeSymbol formattedType, ISymbol? callerSymbol)
  701|     {
  702|         var isClass = !formattedType.IsValueType;
  703|         bool nestedFormatterRequired = false;
  704|         List<IPropertySymbol> nestedFormatterRequiredIfPropertyIsNotSetByDeserializingCtor = new();
  705| 
  706|         AttributeData? contractAttr = formattedType.GetAttributes().FirstOrDefault(x => x.AttributeClass.ApproximatelyEqual(this.typeReferences.MessagePackObjectAttribute));
  707| 
  708|         // Examine properties set on the attribute such that we can discern whether they were explicitly set or not.
  709|         // This is useful when we have assembly-level attributes or other environmentally-controlled defaults that the attribute may override either direction.
  710|         bool? suppressSourceGeneration = (bool?)contractAttr?.NamedArguments.FirstOrDefault(kvp => kvp.Key == Constants.SuppressSourceGenerationPropertyName).Value.Value;
  711|         bool? allowPrivateAttribute = (bool?)contractAttr?.NamedArguments.FirstOrDefault(kvp => kvp.Key == Constants.AllowPrivatePropertyName).Value.Value;
  712| 
  713|         if (contractAttr is null)
  714|         {
  715|             ////this.reportDiagnostic?.Invoke(Diagnostic.Create(MsgPack00xMessagePackAnalyzer.TypeMustBeMessagePackObject, ((BaseTypeDeclarationSyntax)type.DeclaringSyntaxReferences[0].GetSyntax()).Identifier.GetLocation(), type.ToDisplayString(SymbolDisplayFormat.FullyQualifiedFormat)));
  716|         }
  717| 
  718|         bool isIntKey = true;
  719|         Dictionary<int, (MemberSerializationInfo Info, ITypeSymbol TypeSymbol)> intMembers = new();
  720|         Dictionary<string, (MemberSerializationInfo Info, ITypeSymbol TypeSymbol)> stringMembers = new();
  721| 
  722|         // We default to not requiring non-public members to be attributed,
  723|         // but as soon as the first non-public member *is* attributed,
  724|         // we'll require all non-public members to be attributed.
  725|         // Historically, only public members were able to be serialized by default,
  726|         // so the analyzer only highlighted missing attributes on public members.
  727|         // But once it's clear that the developer is serializing non-public members,
  728|         // we need to raise the bar for all non-public members.
  729|         bool nonPublicMembersAreSerialized = false;
  730|         List<Diagnostic> deferredDiagnosticsForNonPublicMembers = new();
  731| 
  732|         FormatterDescriptor? GetSpecialFormatter(ISymbol member)
  733|         {
  734|             INamedTypeSymbol? name = member.GetAttributes().FirstOrDefault(x => x.AttributeClass.ApproximatelyEqual(this.typeReferences.FormatterAttribute))?.ConstructorArguments[0].Value as INamedTypeSymbol;
  735|             if (name is not null)
  736|             {
  737|                 if (FormatterDescriptor.TryCreate(name, out FormatterDescriptor? descriptor))
  738|                 {
  739|                     return descriptor;
  740|                 }
  741|                 else
  742|                 {
  743|                     // Report that the named type is not a formatter.
  744|                     // this.reportDiagnostic();
  745|                 }
  746|             }
  747| 
  748|             return null;
  749|         }
  750| 
  751|         HashSet<Diagnostic> reportedDiagnostics = new();
  752|         IEnumerable<ISymbol> instanceMembers = formattedType.GetAllMembers()
  753|             .Where(m => m is IFieldSymbol or IPropertySymbol && !(m.IsStatic || m.IsOverride || m.IsImplicitlyDeclared));
  754| 
  755|         // The actual member identifiers of each serializable member,
  756|         // such that we'll recognize collisions as we enumerate members in base types
  757|         // and record that that happened so that the emitted source generator can apply the necessary casts.
  758|         // In particular this does NOT store substitute names given by KeyAttribute.Name.
  759|         // Members should be added to this set after they are verified to be accessible, instance, non-override properties,
  760|         // whether or not those members are serialized.
  761|         HashSet<string> collidingMemberNames = new(StringComparer.Ordinal);
  762|         HashSet<string> observedMemberNames = new(StringComparer.Ordinal);
  763|         foreach (ISymbol member in instanceMembers)
  764|         {
  765|             if (!observedMemberNames.Add(member.Name))
  766|             {
  767|                 collidingMemberNames.Add(member.Name);
  768|             }
  769|         }
  770| 
  771|         QualifiedNamedTypeName? GetDeclaringTypeIfColliding(ISymbol symbol) => collidingMemberNames.Contains(symbol.Name) && !SymbolEqualityComparer.Default.Equals(symbol.ContainingType, formattedType) ? new(symbol.ContainingType) : null;
  772| 
  773|         if (this.options.Generator.Formatters.UsesMapMode || (contractAttr?.ConstructorArguments[0] is { Value: true }))
  774|         {
  775|             Dictionary<string, ISymbol> claimedKeys = new(StringComparer.Ordinal);
  776|             void ReportNonUniqueNameIfApplicable(ISymbol item, string stringKey)
  777|             {
  778|                 if (claimedKeys.TryGetValue(stringKey, out ISymbol newSymbol))
  779|                 {
  780|                     SyntaxNode? syntax = newSymbol.DeclaringSyntaxReferences.FirstOrDefault()?.GetSyntax(this.cancellationToken);
  781|                     var location = syntax switch
  782|                     {
  783|                         PropertyDeclarationSyntax { Identifier: SyntaxToken propertyId } => propertyId.GetLocation(),
  784|                         VariableDeclaratorSyntax { Identifier: SyntaxToken fieldId } => fieldId.GetLocation(),
  785|                         not null => syntax.GetLocation(),
  786|                         _ => null,
  787|                     };
  788| 
  789|                     reportDiagnostic?.Invoke(Diagnostic.Create(MsgPack00xMessagePackAnalyzer.CollidingMemberNamesInForceMapMode, location));
  790|                 }
  791| 
  792|                 claimedKeys[stringKey] = item;
  793|             }
  794| 
  795|             // All public members are serialize target except [Ignore] member.
  796|             // Include private members if the type opted into that.
  797|             Accessibility minimumAccessibility = allowPrivateAttribute is true ? Accessibility.Private : Accessibility.Public;
  798|             isIntKey = false;
  799| 
  800|             var hiddenIntKey = 0;
  801| 
  802|             foreach (ISymbol baseItem in instanceMembers)
  803|             {
  804|                 switch (baseItem)
  805|                 {
  806|                     case IPropertySymbol item:
  807|                         {
  808|                             ImmutableArray<AttributeData> attributes = item.GetAttributes();
  809|                             if (attributes.Any(x => (x.AttributeClass.ApproximatelyEqual(this.typeReferences.IgnoreAttribute) || x.AttributeClass?.Name == this.typeReferences.IgnoreDataMemberAttribute?.Name)) ||
  810|                                 item.DeclaredAccessibility < minimumAccessibility)
  811|                             {
  812|                                 continue;
  813|                             }
  814| 
  815|                             bool isReadable = item.GetMethod is not null;
  816|                             bool isWritable = item.SetMethod is not null;
  817|                             if (!isReadable && !isWritable)
  818|                             {
  819|                                 continue;
  820|                             }
  821| 
  822|                             bool isInitOnly = item.SetMethod?.IsInitOnly is true;
  823|                             AttributeData? keyAttribute = attributes.FirstOrDefault(attributes => attributes.AttributeClass.ApproximatelyEqual(this.typeReferences.KeyAttribute));
  824|                             string stringKey = keyAttribute?.ConstructorArguments.Length == 1 && keyAttribute.ConstructorArguments[0].Value is string name ? name : item.Name;
  825|                             ReportNonUniqueNameIfApplicable(item, stringKey);
  826| 
  827|                             nestedFormatterRequired |= item.GetMethod is not null && IsPartialTypeRequired(item.GetMethod.DeclaredAccessibility);
  828|                             nestedFormatterRequired |= item.SetMethod is not null && IsPartialTypeRequired(item.SetMethod.DeclaredAccessibility);
  829|                             FormatterDescriptor? specialFormatter = GetSpecialFormatter(item);
  830|                             MemberSerializationInfo member = new(true, isWritable, isReadable, isInitOnly, item.IsRequired, hiddenIntKey++, stringKey, item.Name, item.Type.ToDisplayString(SymbolDisplayFormat.FullyQualifiedFormat), item.Type.ToDisplayString(BinaryWriteFormat), specialFormatter)
  831|                             {
  832|                                 DeclaringType = GetDeclaringTypeIfColliding(item),
  833|                             };
  834|                             if (!stringMembers.ContainsKey(member.StringKey))
  835|                             {
  836|                                 stringMembers.Add(member.StringKey, (member, item.Type));
  837|                             }
  838| 
  839|                             if (specialFormatter is null)
  840|                             {
  841|                                 this.CollectCore(item.Type, item); // recursive collect
  842|                             }
  843|                         }
  844| 
  845|                         break;
  846|                     case IFieldSymbol item:
  847|                         {
  848|                             ImmutableArray<AttributeData> attributes = item.GetAttributes();
  849|                             if (attributes.Any(x => (x.AttributeClass.ApproximatelyEqual(this.typeReferences.IgnoreAttribute) || x.AttributeClass?.Name == this.typeReferences.IgnoreDataMemberAttribute?.Name)) ||
  850|                                 item.DeclaredAccessibility < minimumAccessibility)
  851|                             {
  852|                                 continue;
  853|                             }
  854| 
  855|                             AttributeData? keyAttribute = attributes.FirstOrDefault(attributes => attributes.AttributeClass.ApproximatelyEqual(this.typeReferences.KeyAttribute));
  856|                             string stringKey = keyAttribute?.ConstructorArguments.Length == 1 && keyAttribute.ConstructorArguments[0].Value is string name ? name : item.Name;
  857|                             ReportNonUniqueNameIfApplicable(item, stringKey);
  858| 
  859|                             nestedFormatterRequired |= IsPartialTypeRequired(item.DeclaredAccessibility);
  860|                             FormatterDescriptor? specialFormatter = GetSpecialFormatter(item);
  861|                             MemberSerializationInfo member = new(false, IsWritable: !item.IsReadOnly, IsReadable: true, IsInitOnly: false, item.IsRequired, hiddenIntKey++, stringKey, item.Name, item.Type.ToDisplayString(SymbolDisplayFormat.FullyQualifiedFormat), item.Type.ToDisplayString(BinaryWriteFormat), specialFormatter)
  862|                             {
  863|                                 DeclaringType = GetDeclaringTypeIfColliding(item),
  864|                             };
  865|                             if (!stringMembers.ContainsKey(member.StringKey))
  866|                             {
  867|                                 stringMembers.Add(member.StringKey, (member, item.Type));
  868|                             }
  869| 
  870|                             if (specialFormatter is null)
  871|                             {
  872|                                 this.CollectCore(item.Type, item); // recursive collect
  873|                             }
  874|                         }
  875| 
  876|                         break;
  877|                 }
  878|             }
  879|         }
  880|         else
  881|         {
  882|             // Only KeyAttribute members
  883|             var searchFirst = true;
  884|             var hiddenIntKey = 0;
  885| 
  886|             foreach (IPropertySymbol item in instanceMembers.OfType<IPropertySymbol>())
  887|             {
  888|                 if (item.IsIndexer)
  889|                 {
  890|                     continue; // .tt files don't generate good code for this yet: https://github.com/neuecc/MessagePack-CSharp/issues/390
  891|                 }
  892| 
  893|                 if (item.GetAttributes().Any(x =>
  894|                 {
  895|                     var typeReferencesIgnoreDataMemberAttribute = this.typeReferences.IgnoreDataMemberAttribute;
  896|                     return typeReferencesIgnoreDataMemberAttribute != null && (x.AttributeClass.ApproximatelyEqual(this.typeReferences.IgnoreAttribute) || x.AttributeClass.ApproximatelyEqual(typeReferencesIgnoreDataMemberAttribute));
  897|                 }))
  898|                 {
  899|                     nonPublicMembersAreSerialized |= (item.DeclaredAccessibility & Accessibility.Public) != Accessibility.Public;
  900|                     continue;
  901|                 }
  902| 
  903|                 bool isReadable = item.GetMethod is not null;
  904|                 bool isWritable = item.SetMethod is not null;
  905|                 bool isInitOnly = item.SetMethod?.IsInitOnly is true;
  906|                 if (!isReadable && !isWritable)
  907|                 {
  908|                     continue;
  909|                 }
  910| 
  911|                 FormatterDescriptor? specialFormatter = GetSpecialFormatter(item);
  912|                 TypedConstant? key = item.GetAttributes().FirstOrDefault(x => x.AttributeClass.ApproximatelyEqual(this.typeReferences.KeyAttribute))?.ConstructorArguments[0];
  913|                 if (key is null)
  914|                 {
  915|                     if (contractAttr is not null)
  916|                     {
  917|                         // If the member is attributed with a type derived from KeyAttribute, that's incompatible with source generation
  918|                         // since we cannot know what the key is using only C# syntax and the semantic model.
  919|                         SyntaxReference? derivedKeyAttribute = item.GetAttributes().FirstOrDefault(att => att.AttributeClass.IsApproximatelyEqualOrDerivedFrom(this.typeReferences.KeyAttribute) == RoslynAnalyzerExtensions.EqualityMatch.LeftDerivesFromRight)?.ApplicationSyntaxReference;
  920| 
  921|                         if (derivedKeyAttribute is null || suppressSourceGeneration is not true)
  922|                         {
  923|                             if (SymbolEqualityComparer.Default.Equals(item.ContainingType, formattedType))
  924|                             {
  925|                                 var syntax = item.DeclaringSyntaxReferences.FirstOrDefault()?.GetSyntax();
  926|                                 var identifier = (syntax as PropertyDeclarationSyntax)?.Identifier ?? (syntax as ParameterSyntax)?.Identifier;
  927| 
  928|                                 Diagnostic diagnostic = derivedKeyAttribute is not null && suppressSourceGeneration is not true
  929|                                     ? Diagnostic.Create(MsgPack00xMessagePackAnalyzer.AOTDerivedKeyAttribute, derivedKeyAttribute.GetSyntax(this.cancellationToken).GetLocation())
  930|                                     : Diagnostic.Create(MsgPack00xMessagePackAnalyzer.MemberNeedsKey, identifier?.GetLocation(), formattedType.ToDisplayString(SymbolDisplayFormat.FullyQualifiedFormat), item.Name);
  931|                                 if (nonPublicMembersAreSerialized || (item.DeclaredAccessibility & Accessibility.Public) == Accessibility.Public)
  932|                                 {
  933|                                     this.reportDiagnostic?.Invoke(diagnostic);
  934|                                 }
  935|                                 else
  936|                                 {
  937|                                     deferredDiagnosticsForNonPublicMembers.Add(diagnostic);
  938|                                 }
  939|                             }
  940|                             else if (formattedType.BaseType is not null)
  941|                             {
  942|                                 // The member was inherited, so we raise a special error at the location of the base type reference.
  943|                                 BaseTypeSyntax? baseSyntax = formattedType.DeclaringSyntaxReferences.SelectMany(sr => (IEnumerable<BaseTypeSyntax>?)((BaseTypeDeclarationSyntax)sr.GetSyntax()).BaseList?.Types ?? Array.Empty<BaseTypeSyntax>())
  944|                                     .FirstOrDefault(bt => SymbolEqualityComparer.Default.Equals(this.compilation.GetSemanticModel(bt.SyntaxTree).GetTypeInfo(bt.Type).Type, item.ContainingType));
  945|                                 if (baseSyntax is not null)
  946|                                 {
  947|                                     Diagnostic diagnostic = derivedKeyAttribute is not null && suppressSourceGeneration is not true
  948|                                         ? Diagnostic.Create(MsgPack00xMessagePackAnalyzer.AOTDerivedKeyAttribute, baseSyntax.GetLocation())
  949|                                         : Diagnostic.Create(
  950|                                             MsgPack00xMessagePackAnalyzer.BaseTypeContainsUnattributedPublicMembers,
  951|                                             baseSyntax.GetLocation(),
  952|                                             item.ContainingType.ToDisplayString(SymbolDisplayFormat.FullyQualifiedFormat),
  953|                                             item.Name);
  954|                                     if (reportedDiagnostics.Add(diagnostic))
  955|                                     {
  956|                                         if (nonPublicMembersAreSerialized || (item.DeclaredAccessibility & Accessibility.Public) == Accessibility.Public)
  957|                                         {
  958|                                             this.reportDiagnostic?.Invoke(diagnostic);
  959|                                         }
  960|                                         else
  961|                                         {
  962|                                             deferredDiagnosticsForNonPublicMembers.Add(diagnostic);
  963|                                         }
  964|                                     }
  965|                                 }
  966|                             }
  967|                         }
  968|                     }
  969|                 }
  970|                 else
  971|                 {
  972|                     // If this attributed member is non-public, then all non-public members should be attributed.
  973|                     nonPublicMembersAreSerialized |= (item.DeclaredAccessibility & Accessibility.Public) != Accessibility.Public;
  974| 
  975|                     nestedFormatterRequired |= item.GetMethod is not null && IsPartialTypeRequired(item.GetMethod.DeclaredAccessibility);
  976|                     if (item.SetMethod is not null && IsPartialTypeRequired(item.SetMethod.DeclaredAccessibility))
  977|                     {
  978|                         nestedFormatterRequiredIfPropertyIsNotSetByDeserializingCtor.Add(item);
  979|                     }
  980| 
  981|                     var intKey = key is { Value: int intKeyValue } ? intKeyValue : default(int?);
  982|                     var stringKey = key is { Value: string stringKeyValue } ? stringKeyValue : default;
  983|                     if (intKey == null && stringKey == null)
  984|                     {
  985|                         this.reportDiagnostic?.Invoke(Diagnostic.Create(MsgPack00xMessagePackAnalyzer.BothStringAndIntKeyAreNull, ((PropertyDeclarationSyntax)item.DeclaringSyntaxReferences[0].GetSyntax()).Identifier.GetLocation(), formattedType.ToDisplayString(SymbolDisplayFormat.FullyQualifiedFormat), item.Name));
  986|                     }
  987| 
  988|                     // A property with an init accessor and an initializer has a default that will be discarded by the deserializer.
  989|                     if (suppressSourceGeneration is not true && isInitOnly)
  990|                     {
  991|                         EqualsValueClauseSyntax? initializer = item.DeclaringSyntaxReferences.Select(s => (s.GetSyntax(this.cancellationToken) as PropertyDeclarationSyntax)?.Initializer).FirstOrDefault(i => i is not null);
  992|                         if (initializer is not null)
  993|                         {
  994|                             this.reportDiagnostic?.Invoke(Diagnostic.Create(MsgPack00xMessagePackAnalyzer.AOTInitProperty, initializer.GetLocation()));
  995|                         }
  996|                     }
  997| 
  998|                     if (searchFirst)
  999|                     {
 1000|                         searchFirst = false;
 1001|                         isIntKey = intKey != null;
 1002|                     }
 1003|                     else
 1004|                     {
 1005|                         if ((isIntKey && intKey == null) || (!isIntKey && stringKey == null))
 1006|                         {
 1007|                             this.reportDiagnostic?.Invoke(Diagnostic.Create(MsgPack00xMessagePackAnalyzer.DoNotMixStringAndIntKeys, item.DeclaringSyntaxReferences.FirstOrDefault()?.GetSyntax().GetLocation()));
 1008|                             continue; // The key kind does not match the other members; the diagnostic is reported, so skip this member.
 1009|                         }
 1010|                     }
 1011| 
 1012|                     if (isIntKey)
 1013|                     {
 1014|                         if (intMembers.ContainsKey(intKey!.Value))
 1015|                         {
 1016|                             this.reportDiagnostic?.Invoke(Diagnostic.Create(MsgPack00xMessagePackAnalyzer.KeysMustBeUnique, item.DeclaringSyntaxReferences.FirstOrDefault()?.GetSyntax().GetLocation()));
 1017|                         }
 1018| 
 1019|                         var member = new MemberSerializationInfo(true, isWritable, isReadable, isInitOnly, item.IsRequired, intKey!.Value, item.Name, item.Name, item.Type.ToDisplayString(SymbolDisplayFormat.FullyQualifiedFormat), item.Type.ToDisplayString(BinaryWriteFormat), specialFormatter)
 1020|                         {
 1021|                             DeclaringType = GetDeclaringTypeIfColliding(item),
 1022|                         };
 1023|                         if (!intMembers.ContainsKey(member.IntKey))
 1024|                         {
 1025|                             intMembers.Add(member.IntKey, (member, item.Type));
 1026|                         }
 1027|                     }
 1028|                     else if (stringKey is not null)
 1029|                     {
 1030|                         if (stringMembers.ContainsKey(stringKey!))
 1031|                         {
 1032|                             this.reportDiagnostic?.Invoke(Diagnostic.Create(MsgPack00xMessagePackAnalyzer.KeysMustBeUnique, item.DeclaringSyntaxReferences.FirstOrDefault()?.GetSyntax().GetLocation()));
 1033|                         }
 1034| 
 1035|                         var member = new MemberSerializationInfo(true, isWritable, isReadable, isInitOnly, item.IsRequired, hiddenIntKey++, stringKey!, item.Name, item.Type.ToDisplayString(SymbolDisplayFormat.FullyQualifiedFormat), item.Type.ToDisplayString(BinaryWriteFormat), specialFormatter)
 1036|                         {
 1037|                             DeclaringType = GetDeclaringTypeIfColliding(item),
 1038|                         };
 1039|                         if (!stringMembers.ContainsKey(member.StringKey))
 1040|                         {
 1041|                             stringMembers.Add(member.StringKey, (member, item.Type));
 1042|                         }
 1043|                     }
 1044| 
 1045|                     var messagePackFormatter = item.GetAttributes().FirstOrDefault(x => x.AttributeClass.ApproximatelyEqual(this.typeReferences.FormatterAttribute))?.ConstructorArguments[0];
 1046| 
 1047|                     if (messagePackFormatter == null)
 1048|                     {
 1049|                         // recursive collect
 1050|                         this.CollectCore(item.Type, item);
 1051|                     }
 1052|                 }
 1053|             }
 1054| 
 1055|             foreach (IFieldSymbol item in formattedType.GetAllMembers().OfType<IFieldSymbol>())
 1056|             {
 1057|                 if (item.IsImplicitlyDeclared || item.IsStatic)
 1058|                 {
 1059|                     continue;
 1060|                 }
 1061| 
 1062|                 if (item.GetAttributes().Any(x => x.AttributeClass.ApproximatelyEqual(this.typeReferences.IgnoreAttribute)))
 1063|                 {
 1064|                     nonPublicMembersAreSerialized |= (item.DeclaredAccessibility & Accessibility.Public) != Accessibility.Public;
 1065|                     continue;
 1066|                 }
 1067| 
 1068|                 FormatterDescriptor? specialFormatter = GetSpecialFormatter(item);
 1069|                 TypedConstant? key = item.GetAttributes().FirstOrDefault(x => x.AttributeClass.ApproximatelyEqual(this.typeReferences.KeyAttribute))?.ConstructorArguments[0];
 1070|                 if (key is null)
 1071|                 {
 1072|                     if (contractAttr is not null)
 1073|                     {
 1074|                         // If the member is attributed with a type derived from KeyAttribute, that's incompatible with source generation
 1075|                         // since we cannot know what the key is using only C# syntax and the semantic model.
 1076|                         SyntaxReference? derivedKeyAttribute = item.GetAttributes().FirstOrDefault(att => att.AttributeClass.IsApproximatelyEqualOrDerivedFrom(this.typeReferences.KeyAttribute) == RoslynAnalyzerExtensions.EqualityMatch.LeftDerivesFromRight)?.ApplicationSyntaxReference;
 1077| 
 1078|                         if (derivedKeyAttribute is null || suppressSourceGeneration is not true)
 1079|                         {
 1080|                             if (SymbolEqualityComparer.Default.Equals(item.ContainingType, formattedType))
 1081|                             {
 1082|                                 Diagnostic diagnostic = derivedKeyAttribute is not null && suppressSourceGeneration is not true
 1083|                                     ? Diagnostic.Create(MsgPack00xMessagePackAnalyzer.AOTDerivedKeyAttribute, derivedKeyAttribute.GetSyntax(this.cancellationToken).GetLocation())
 1084|                                     : Diagnostic.Create(MsgPack00xMessagePackAnalyzer.MemberNeedsKey, item.DeclaringSyntaxReferences[0].GetSyntax().GetLocation(), formattedType.ToDisplayString(SymbolDisplayFormat.FullyQualifiedFormat), item.Name);
 1085|                                 if (nonPublicMembersAreSerialized || (item.DeclaredAccessibility & Accessibility.Public) == Accessibility.Public)
 1086|                                 {
 1087|                                     this.reportDiagnostic?.Invoke(diagnostic);
 1088|                                 }
 1089|                                 else
 1090|                                 {
 1091|                                     deferredDiagnosticsForNonPublicMembers.Add(diagnostic);
 1092|                                 }
 1093|                             }
 1094|                             else if (formattedType.BaseType is not null)
 1095|                             {
 1096|                                 // The member was inherited, so we raise a special error at the location of the base type reference.
 1097|                                 BaseTypeSyntax? baseSyntax = formattedType.DeclaringSyntaxReferences.SelectMany(sr => (IEnumerable<BaseTypeSyntax>?)((BaseTypeDeclarationSyntax)sr.GetSyntax()).BaseList?.Types ?? Array.Empty<BaseTypeSyntax>())
 1098|                                     .FirstOrDefault(bt => SymbolEqualityComparer.Default.Equals(this.compilation.GetSemanticModel(bt.SyntaxTree).GetTypeInfo(bt.Type).Type, item.ContainingType));
 1099|                                 if (baseSyntax is not null)
 1100|                                 {
 1101|                                     Diagnostic diagnostic = derivedKeyAttribute is not null && suppressSourceGeneration is not true
 1102|                                         ? Diagnostic.Create(MsgPack00xMessagePackAnalyzer.AOTDerivedKeyAttribute, baseSyntax.GetLocation())
 1103|                                         : Diagnostic.Create(
 1104|                                             MsgPack00xMessagePackAnalyzer.BaseTypeContainsUnattributedPublicMembers,
 1105|                                             baseSyntax.GetLocation(),
 1106|                                             item.ContainingType.ToDisplayString(SymbolDisplayFormat.FullyQualifiedFormat),
 1107|                                             item.Name);
 1108|                                     if (reportedDiagnostics.Add(diagnostic))
 1109|                                     {
 1110|                                         if (nonPublicMembersAreSerialized || (item.DeclaredAccessibility & Accessibility.Public) == Accessibility.Public)
 1111|                                         {
 1112|                                             this.reportDiagnostic?.Invoke(diagnostic);
 1113|                                         }
 1114|                                         else
 1115|                                         {
 1116|                                             deferredDiagnosticsForNonPublicMembers.Add(diagnostic);
 1117|                                         }
 1118|                                     }
 1119|                                 }
 1120|                             }
 1121|                         }
 1122|                     }
 1123|                 }
 1124|                 else
 1125|                 {
 1126|                     // If this attributed member is non-public, then all non-public members should be attributed.
 1127|                     nonPublicMembersAreSerialized |= (item.DeclaredAccessibility & Accessibility.Public) != Accessibility.Public;
 1128| 
 1129|                     nestedFormatterRequired |= IsPartialTypeRequired(item.DeclaredAccessibility);
 1130| 
 1131|                     var intKey = key is { Value: int intKeyValue } ? intKeyValue : default(int?);
 1132|                     var stringKey = key is { Value: string stringKeyValue } ? stringKeyValue : default;
 1133|                     if (intKey == null && stringKey == null)
 1134|                     {
 1135|                         this.reportDiagnostic?.Invoke(Diagnostic.Create(MsgPack00xMessagePackAnalyzer.BothStringAndIntKeyAreNull, item.DeclaringSyntaxReferences.FirstOrDefault()?.GetSyntax().GetLocation()));
 1136|                     }
 1137| 
 1138|                     if (searchFirst)
 1139|                     {
 1140|                         searchFirst = false;
 1141|                         isIntKey = intKey != null;
 1142|                     }
 1143|                     else
 1144|                     {
 1145|                         if ((isIntKey && intKey == null) || (!isIntKey && stringKey == null))
 1146|                         {
 1147|                             this.reportDiagnostic?.Invoke(Diagnostic.Create(MsgPack00xMessagePackAnalyzer.DoNotMixStringAndIntKeys, item.DeclaringSyntaxReferences.FirstOrDefault()?.GetSyntax().GetLocation()));
 1148|                             continue; // The key kind does not match the other members; the diagnostic is reported, so skip this member.
 1149|                         }
 1150|                     }
 1151| 
 1152|                     if (isIntKey)
 1153|                     {
 1154|                         if (intMembers.ContainsKey(intKey!.Value))
 1155|                         {
 1156|                             this.reportDiagnostic?.Invoke(Diagnostic.Create(MsgPack00xMessagePackAnalyzer.KeysMustBeUnique, item.DeclaringSyntaxReferences.FirstOrDefault()?.GetSyntax().GetLocation()));
 1157|                         }
 1158| 
 1159|                         var member = new MemberSerializationInfo(true, IsWritable: !item.IsReadOnly, IsReadable: true, IsInitOnly: false, item.IsRequired, intKey!.Value, item.Name, item.Name, item.Type.ToDisplayString(SymbolDisplayFormat.FullyQualifiedFormat), item.Type.ToDisplayString(BinaryWriteFormat), specialFormatter)
 1160|                         {
 1161|                             DeclaringType = GetDeclaringTypeIfColliding(item),
 1162|                         };
 1163|                         if (!intMembers.ContainsKey(member.IntKey))
 1164|                         {
 1165|                             intMembers.Add(member.IntKey, (member, item.Type));
 1166|                         }
 1167|                     }
 1168|                     else
 1169|                     {
 1170|                         if (stringMembers.ContainsKey(stringKey!))
 1171|                         {
 1172|                             this.reportDiagnostic?.Invoke(Diagnostic.Create(MsgPack00xMessagePackAnalyzer.KeysMustBeUnique, item.DeclaringSyntaxReferences.FirstOrDefault()?.GetSyntax().GetLocation()));
 1173|                         }
 1174| 
 1175|                         var member = new MemberSerializationInfo(true, IsWritable: !item.IsReadOnly, IsReadable: true, IsInitOnly: false, item.IsRequired, hiddenIntKey++, stringKey!, item.Name, item.Type.ToDisplayString(SymbolDisplayFormat.FullyQualifiedFormat), item.Type.ToDisplayString(BinaryWriteFormat), specialFormatter)
 1176|                         {
 1177|                             DeclaringType = GetDeclaringTypeIfColliding(item),
 1178|                         };
 1179|                         if (!stringMembers.ContainsKey(member.StringKey))
 1180|                         {
 1181|                             stringMembers.Add(member.StringKey, (member, item.Type));
 1182|                         }
 1183|                     }
 1184| 
 1185|                     var messagePackFormatter = item.GetAttributes().FirstOrDefault(x => x.AttributeClass.ApproximatelyEqual(this.typeReferences.FormatterAttribute))?.ConstructorArguments[0];
 1186| 
 1187|                     if (messagePackFormatter == null)
 1188|                     {
 1189|                         // recursive collect
 1190|                         this.CollectCore(item.Type, item);
 1191|                     }
 1192|                 }
 1193|             }
 1194|         }
 1195| 
 1196|         // If we discovered midway through that we should be reporting diagnostics for non-public members,
 1197|         // report the ones we missed along the way.
 1198|         if ((nonPublicMembersAreSerialized || allowPrivateAttribute is true) && this.reportDiagnostic is not null)
 1199|         {
 1200|             foreach (Diagnostic deferred in deferredDiagnosticsForNonPublicMembers)
 1201|             {
 1202|                 this.reportDiagnostic(deferred);
 1203|             }
 1204|         }
 1205| 
 1206|         // GetConstructor
 1207|         var ctorEnumerator = default(IEnumerator<IMethodSymbol>);
 1208|         var ctor = formattedType.Constructors.SingleOrDefault(x => x.GetAttributes().Any(y => y.AttributeClass != null && y.AttributeClass.ApproximatelyEqual(this.typeReferences.SerializationConstructorAttribute)));
 1209|         if (ctor is null)
 1210|         {
 1211|             ctorEnumerator = formattedType.Constructors
 1212|                 .OrderByDescending(x => x.DeclaredAccessibility)
 1213|                 .ThenByDescending(x => x.Parameters.Length)
 1214|                 .GetEnumerator();
 1215| 
 1216|             if (ctorEnumerator.MoveNext())
 1217|             {
 1218|                 ctor = ctorEnumerator.Current;
 1219|             }
 1220|         }
 1221| 
 1222|         // struct allows null ctor
 1223|         if (ctor is null && isClass)
 1224|         {
 1225|             this.reportDiagnostic?.Invoke(Diagnostic.Create(MsgPack00xMessagePackAnalyzer.NoDeserializingConstructor, GetIdentifierLocation(formattedType)));
 1226|             return null;
 1227|         }
 1228| 
 1229|         var constructorParameters = new List<MemberSerializationInfo>();
 1230|         if (ctor is not null)
 1231|         {
 1232|             nestedFormatterRequired |= IsPartialTypeRequired(ctor.DeclaredAccessibility);
 1233| 
 1234|             var constructorLookupDictionary = stringMembers.ToLookup(x => x.Value.Info.Name, x => x, StringComparer.OrdinalIgnoreCase);
 1235|             IReadOnlyDictionary<int, (MemberSerializationInfo Info, ITypeSymbol TypeSymbol)> ctorParamIndexIntMembersDictionary = intMembers
 1236|                 .OrderBy(x => x.Key).Select((x, i) => (Key: x.Value, Index: i))
 1237|                 .ToDictionary(x => x.Index, x => x.Key);
 1238|             do
 1239|             {
 1240|                 constructorParameters.Clear();
 1241|                 var ctorParamIndex = 0;
 1242|                 foreach (IParameterSymbol item in ctor!.Parameters)
 1243|                 {
 1244|                     if (isIntKey)
 1245|                     {
 1246|                         if (ctorParamIndexIntMembersDictionary.TryGetValue(ctorParamIndex, out (MemberSerializationInfo Info, ITypeSymbol TypeSymbol) member))
 1247|                         {
 1248|                             if (this.compilation.ClassifyConversion(member.TypeSymbol, item.Type) is { IsImplicit: true } && member.Info.IsReadable)
 1249|                             {
 1250|                                 constructorParameters.Add(member.Info);
 1251|                             }
 1252|                             else
 1253|                             {
 1254|                                 if (ctorEnumerator != null)
 1255|                                 {
 1256|                                     ctor = null;
 1257|                                     continue;
 1258|                                 }
 1259|                                 else
 1260|                                 {
 1261|                                     this.reportDiagnostic?.Invoke(Diagnostic.Create(MsgPack00xMessagePackAnalyzer.DeserializingConstructorParameterTypeMismatch, GetLocation(item)));
 1262|                                     return null;
 1263|                                 }
 1264|                             }
 1265|                         }
 1266|                         else
 1267|                         {
 1268|                             if (ctorEnumerator != null)
 1269|                             {
 1270|                                 ctor = null;
 1271|                                 continue;
 1272|                             }
 1273|                             else
 1274|                             {
 1275|                                 this.reportDiagnostic?.Invoke(Diagnostic.Create(MsgPack00xMessagePackAnalyzer.DeserializingConstructorParameterIndexMissing, GetParameterListLocation(ctor)));
 1276|                                 return null;
 1277|                             }
 1278|                         }
 1279|                     }
 1280|                     else
 1281|                     {
 1282|                         IEnumerable<KeyValuePair<string, (MemberSerializationInfo Info, ITypeSymbol TypeSymbol)>> hasKey = constructorLookupDictionary[item.Name];
 1283|                         using var enumerator = hasKey.GetEnumerator();
 1284| 
 1285|                         // hasKey.Count() == 0
 1286|                         if (!enumerator.MoveNext())
 1287|                         {
 1288|                             if (ctorEnumerator == null)
 1289|                             {
 1290|                                 this.reportDiagnostic?.Invoke(Diagnostic.Create(MsgPack00xMessagePackAnalyzer.DeserializingConstructorParameterNameMissing, GetParameterListLocation(ctor)));
 1291|                                 return null;
 1292|                             }
 1293| 
 1294|                             ctor = null;
 1295|                             continue;
 1296|                         }
 1297| 
 1298|                         var first = enumerator.Current.Value;
 1299| 
 1300|                         // hasKey.Count() != 1
 1301|                         if (enumerator.MoveNext())
 1302|                         {
 1303|                             if (ctorEnumerator == null)
 1304|                             {
 1305|                                 this.reportDiagnostic?.Invoke(Diagnostic.Create(MsgPack00xMessagePackAnalyzer.DeserializingConstructorParameterNameDuplicate, GetLocation(item)));
 1306|                                 return null;
 1307|                             }
 1308| 
 1309|                             ctor = null;
 1310|                             continue;
 1311|                         }
 1312| 
 1313|                         MemberSerializationInfo paramMember = first.Info;
 1314|                         if (item.Type.ToDisplayString(SymbolDisplayFormat.FullyQualifiedFormat) == paramMember.Type && paramMember.IsReadable)
 1315|                         {
 1316|                             constructorParameters.Add(paramMember);
 1317|                         }
 1318|                         else
 1319|                         {
 1320|                             if (ctorEnumerator == null)
 1321|                             {
 1322|                                 this.reportDiagnostic?.Invoke(Diagnostic.Create(MsgPack00xMessagePackAnalyzer.DeserializingConstructorParameterTypeMismatch, GetLocation(item)));
 1323|                                 return null;
 1324|                             }
 1325| 
 1326|                             ctor = null;
 1327|                             continue;
 1328|                         }
 1329|                     }
 1330| 
 1331|                     ctorParamIndex++;
 1332|                 }
 1333|             }
 1334|             while (TryGetNextConstructor(ctorEnumerator, ref ctor));
 1335| 
 1336|             if (ctor == null)
 1337|             {
 1338|                 this.reportDiagnostic?.Invoke(Diagnostic.Create(MsgPack00xMessagePackAnalyzer.NoDeserializingConstructor, GetIdentifierLocation(formattedType)));
 1339|             }
 1340|         }
 1341| 
 1342|         var hasSerializationConstructor = formattedType.AllInterfaces.Any(x => x.ApproximatelyEqual(this.typeReferences.IMessagePackSerializationCallbackReceiver));
 1343|         var needsCastOnBefore = true;
 1344|         var needsCastOnAfter = true;
 1345|         if (hasSerializationConstructor)
 1346|         {
 1347|             needsCastOnBefore = !formattedType.GetMembers("OnBeforeSerialize").Any();
 1348|             needsCastOnAfter = !formattedType.GetMembers("OnAfterDeserialize").Any();
 1349|         }
 1350| 
 1351|         if (contractAttr is null)
 1352|         {
 1353|             if (formattedType.IsDefinition)
 1354|             {
 1355|                 Location location = callerSymbol is not null ? callerSymbol.Locations[0] : formattedType.Locations[0];
 1356|                 var targetName = callerSymbol is not null ? callerSymbol.ContainingType.Name + "." + callerSymbol.Name : formattedType.Name;
 1357| 
 1358|                 ImmutableDictionary<string, string?> typeInfo = ImmutableDictionary.Create<string, string?>().Add("type", formattedType.ToDisplayString(SymbolDisplayFormat.FullyQualifiedFormat));
 1359|                 this.reportDiagnostic?.Invoke(Diagnostic.Create(MsgPack00xMessagePackAnalyzer.TypeMustBeMessagePackObject, location, typeInfo, targetName));
 1360|             }
 1361| 
 1362|             // Indicate to our caller that we don't have a valid object.
 1363|             return null;
 1364|         }
 1365| 
 1366|         if (allowPrivateAttribute is not true && (nonPublicMembersAreSerialized || ctor is { DeclaredAccessibility: not Accessibility.Public } || formattedType.GetEffectiveAccessibility() is not Accessibility.Public))
 1367|         {
 1368|             if (contractAttr.ApplicationSyntaxReference?.GetSyntax(this.cancellationToken) is AttributeSyntax attSyntax)
 1369|             {
 1370|                 Location location = attSyntax.GetLocation();
 1371| 
 1372|                 // If the user is explicitly setting AllowPrivate = false, set the location more precisely.
 1373|                 if (allowPrivateAttribute is false)
 1374|                 {
 1375|                     location = attSyntax.ArgumentList?.Arguments.First(a => a.NameEquals?.Name.Identifier.ValueText == Constants.AllowPrivatePropertyName)?.Expression.GetLocation() ?? location;
 1376|                 }
 1377| 
 1378|                 this.reportDiagnostic?.Invoke(Diagnostic.Create(MsgPack00xMessagePackAnalyzer.MessagePackObjectAllowPrivateRequired, location));
 1379|             }
 1380|         }
 1381| 
 1382|         // Do not source generate the formatter for this type if the attribute opted out.
 1383|         if (suppressSourceGeneration is true)
 1384|         {
 1385|             // Skip any source generation
 1386|             return null;
 1387|         }
 1388| 
 1389|         // If any property had a private setter and does not appear in the deserializing constructor signature,
 1390|         // we'll need a nested formatter.
 1391|         foreach (IPropertySymbol property in nestedFormatterRequiredIfPropertyIsNotSetByDeserializingCtor)
 1392|         {
 1393|             nestedFormatterRequired |= !constructorParameters.Any(m => m.Name == property.Name);
 1394|         }
 1395| 
 1396|         if (nestedFormatterRequired && nonPublicMembersAreSerialized)
 1397|         {
 1398|             // If the data type or any nesting types are not declared with partial, we cannot emit the formatter as a nested type within the data type
 1399|             // as required in order to access the private members.
 1400|             bool anyNonPartialTypesFound = false;
 1401|             BaseTypeDeclarationSyntax[] nonPartialTypes = FindNonPartialTypes(formattedType).ToArray();
 1402|             if (nonPartialTypes.Length > 0)
 1403|             {
 1404|                 BaseTypeDeclarationSyntax? targetType = formattedType.DeclaringSyntaxReferences.FirstOrDefault()?.GetSyntax() as BaseTypeDeclarationSyntax;
 1405|                 Location? primaryLocation = targetType?.Identifier.GetLocation();
 1406|                 Location[]? addlLocations = nonPartialTypes.Where(t => t != targetType).Select(t => t.Identifier.GetLocation()).ToArray();
 1407|                 this.reportDiagnostic?.Invoke(Diagnostic.Create(MsgPack00xMessagePackAnalyzer.PartialTypeRequired, primaryLocation, (IEnumerable<Location>?)addlLocations));
 1408|                 anyNonPartialTypesFound = true;
 1409|             }
 1410| 
 1411|             if (anyNonPartialTypesFound)
 1412|             {
 1413|                 return null;
 1414|             }
 1415|         }
 1416| 
 1417|         INamedTypeSymbol? formattedTypeDefinition = formattedType.IsGenericType ? formattedType.ConstructUnboundGenericType() : null;
 1418|         ObjectSerializationInfo info = ObjectSerializationInfo.Create(
 1419|             formattedType,
 1420|             isClass: isClass,
 1421|             nestedFormatterRequired: nestedFormatterRequired,
 1422|             genericTypeParameters: formattedType.IsGenericType ? formattedType.TypeParameters.Select(t => GenericTypeParameterInfo.Create(t)).ToArray() : Array.Empty<GenericTypeParameterInfo>(),
 1423|             constructorParameters: constructorParameters.ToArray(),
 1424|             isIntKey: isIntKey,
 1425|             members: isIntKey ? intMembers.Values.Select(v => v.Info).ToArray() : stringMembers.Values.Select(v => v.Info).ToArray(),
 1426|             hasIMessagePackSerializationCallbackReceiver: hasSerializationConstructor,
 1427|             needsCastOnAfter: needsCastOnAfter,
 1428|             needsCastOnBefore: needsCastOnBefore,
 1429|             this.options.Generator.Resolver);
 1430| 
 1431|         return info;
 1432|     }
 1433| 
 1434|     private static IEnumerable<BaseTypeDeclarationSyntax> FindNonPartialTypes(ITypeSymbol target)
 1435|     {
 1436|         return from x in CodeAnalysisUtilities.EnumerateTypeAndContainingTypes(target)
 1437|                where x.FirstDeclaration?.Modifiers.Any(SyntaxKind.PartialKeyword) is false
 1438|                select x.FirstDeclaration;
 1439|     }
 1440| 
 1441|     private static Location? GetIdentifierLocation(INamedTypeSymbol type) => ((BaseTypeDeclarationSyntax?)type.DeclaringSyntaxReferences.FirstOrDefault()?.GetSyntax())?.Identifier.GetLocation();
 1442| 
 1443|     private static Location? GetLocation(IParameterSymbol parameter) => parameter.DeclaringSyntaxReferences.FirstOrDefault()?.GetSyntax().GetLocation();
 1444| 
 1445|     private static Location? GetParameterListLocation(IMethodSymbol? method) => ((BaseMethodDeclarationSyntax?)method?.DeclaringSyntaxReferences.FirstOrDefault()?.GetSyntax())?.ParameterList.GetLocation();
 1446| 
 1447|     private static string GetGenericFormatterClassName(INamedTypeSymbol type)
 1448|     {
 1449|         return type.Name;
 1450|     }
 1451| 
 1452|     private static string GetMinimallyQualifiedClassName(INamedTypeSymbol type)
 1453|     {
 1454|         var name = type.ContainingType is object ? GetMinimallyQualifiedClassName(type.ContainingType) + "_" : string.Empty;
 1455|         name += type.ToDisplayString(SymbolDisplayFormat.MinimallyQualifiedFormat);
 1456|         name = name.Replace('.', '_');
 1457|         name = name.Replace('<', '_');
 1458|         name = name.Replace('>', '_');
 1459|         name = Regex.Replace(name, @"\[([,])*\]", match => $"Array{match.Length - 1}");
 1460|         name = name.Replace("?", string.Empty);
 1461|         return name;
 1462|     }
 1463| 
 1464|     private static bool TryGetNextConstructor(IEnumerator<IMethodSymbol>? ctorEnumerator, ref IMethodSymbol? ctor)
 1465|     {
 1466|         if (ctorEnumerator == null || ctor != null)
 1467|         {
 1468|             return false;
 1469|         }
 1470| 
 1471|         if (ctorEnumerator.MoveNext())
 1472|         {
 1473|             ctor = ctorEnumerator.Current;
 1474|             return true;
 1475|         }
 1476|         else
 1477|         {
 1478|             ctor = null;
 1479|             return false;
 1480|         }
 1481|     }
 1482| 
 1483|     private static bool IsPartialTypeRequired(Accessibility accessibility) => accessibility is not (Accessibility.Public or Accessibility.Internal or Accessibility.ProtectedOrInternal);
 1484| 
 1485|     private static bool IsAllowAccessibility(ITypeSymbol symbol)
 1486|     {
 1487|         do
 1488|         {
 1489|             if (symbol.DeclaredAccessibility is not (Accessibility.Public or Accessibility.Internal))
 1490|             {
 1491|                 return false;
 1492|             }
 1493| 
 1494|             symbol = symbol.ContainingType;
 1495|         }
 1496|         while (symbol is not null);
 1497| 
 1498|         return true;
 1499|     }
 1500| 
 1501|     private static bool IsOpenGenericTypeRecursively(INamedTypeSymbol type)
 1502|     {
 1503|         return type.IsGenericType && type.TypeArguments.Any(x => x is ITypeParameterSymbol || (x is INamedTypeSymbol symbol && IsOpenGenericTypeRecursively(symbol)));
 1504|     }
 1505| }
```

### tests/MessagePack.SourceGenerator.ExecutionTests/SuppressedSourceGenerationTests.cs at head (9007cee1), full file
```
    1| // Copyright (c) All contributors. All rights reserved.
    2| // Licensed under the MIT license. See LICENSE file in the project root for full license information.
    3| 
    4| /// <summary>
    5| /// A type that opts out of source generation (https://github.com/MessagePack-CSharp/MessagePack-CSharp/issues/2234).
    6| /// It must still serialize correctly through the run-time (dynamic) resolver.
    7| /// </summary>
    8| [MessagePackObject(SuppressSourceGeneration = true)]
    9| public class SuppressedSourceGenerationType
   10| {
   11|     [Key(0)]
   12|     public int Id { get; set; }
   13| 
   14|     [Key(1)]
   15|     public string Name { get; set; } = string.Empty;
   16| }
   17| 
   18| public class SuppressedSourceGenerationTests
   19| {
   20|     [Fact]
   21|     public void NoFormatterIsGeneratedForSuppressedType()
   22|     {
   23|         Assert.Null(GeneratedMessagePackResolver.Instance.GetFormatter<SuppressedSourceGenerationType>());
   24|     }
   25| 
   26|     [Fact]
   27|     public void SuppressedTypeRoundTripsThroughDynamicResolver()
   28|     {
   29|         var value = new SuppressedSourceGenerationType { Id = 7, Name = "seven" };
   30| 
   31|         byte[] bytes = MessagePackSerializer.Serialize(value, MessagePackSerializerOptions.Standard);
   32|         SuppressedSourceGenerationType result = MessagePackSerializer.Deserialize<SuppressedSourceGenerationType>(bytes, MessagePackSerializerOptions.Standard);
   33| 
   34|         Assert.Equal(7, result.Id);
   35|         Assert.Equal("seven", result.Name);
   36|     }
   37| }
```

### tests/MessagePack.SourceGenerator.Tests/SuppressSourceGenerationAnalyzerTests.cs at head (9007cee1), full file
```
    1| // Copyright (c) All contributors. All rights reserved.
    2| // Licensed under the MIT license. See LICENSE file in the project root for full license information.
    3| 
    4| using MessagePack.Analyzers.CodeFixes;
    5| using Microsoft.CodeAnalysis.CSharp;
    6| using Microsoft.CodeAnalysis.Testing;
    7| using VerifyCS = CSharpCodeFixVerifier<MessagePack.SourceGenerator.Analyzers.MsgPack00xMessagePackAnalyzer, MessagePack.Analyzers.CodeFixes.MessagePackCodeFixProvider>;
    8| 
    9| /// <summary>
   10| /// Verifies that the analyzer keeps validating <c>[MessagePackObject(SuppressSourceGeneration = true)]</c> types
   11| /// (https://github.com/MessagePack-CSharp/MessagePack-CSharp/issues/2234).
   12| /// Opting out of source generation only skips generation; the type is still serialized at run time, so its contract must still be checked.
   13| /// </summary>
   14| public class SuppressSourceGenerationAnalyzerTests
   15| {
   16|     private const string Preamble = @"
   17| using MessagePack;
   18| ";
   19| 
   20|     [Fact]
   21|     public async Task MemberWithoutKeyIsReported()
   22|     {
   23|         string input = Preamble + @"
   24| [MessagePackObject(SuppressSourceGeneration = true)]
   25| public class Foo
   26| {
   27|     public string {|MsgPack004:Member|} { get; set; }
   28| }
   29| ";
   30| 
   31|         await new VerifyCS.Test
   32|         {
   33|             TestCode = input,
   34|             MarkupOptions = MarkupOptions.UseFirstDescriptor,
   35|         }.RunAsync();
   36|     }
   37| 
   38|     [Fact]
   39|     public async Task AllowPrivateRequiredIsReported()
   40|     {
   41|         string input = Preamble + @"
   42| [{|MsgPack015:MessagePackObject(SuppressSourceGeneration = true)|}]
   43| public class Foo
   44| {
   45|     [Key(0)]
   46|     private string member;
   47| }
   48| ";
   49| 
   50|         await new VerifyCS.Test
   51|         {
   52|             TestCode = input,
   53|             MarkupOptions = MarkupOptions.UseFirstDescriptor,
   54|         }.RunAsync();
   55|     }
   56| 
   57|     [Fact]
   58|     public async Task MemberTypeMustBeMessagePackObjectIsReported()
   59|     {
   60|         string input = Preamble + @"
   61| public class Other
   62| {
   63| }
   64| 
   65| [MessagePackObject(SuppressSourceGeneration = true)]
   66| public class Foo
   67| {
   68|     [Key(0)]
   69|     public Other {|MsgPack003:Member|} { get; set; }
   70| }
   71| ";
   72| 
   73|         await new VerifyCS.Test
   74|         {
   75|             TestCode = input,
   76|             MarkupOptions = MarkupOptions.UseFirstDescriptor,
   77|         }.RunAsync();
   78|     }
   79| 
   80|     [Fact]
   81|     public async Task DuplicateIntKeysAreReportedWithoutAnalyzerFailure()
   82|     {
   83|         string input = Preamble + @"
   84| [MessagePackObject(SuppressSourceGeneration = true)]
   85| public class Foo
   86| {
   87|     [Key(0)]
   88|     public string Member1 { get; set; }
   89| 
   90|     {|MsgPack005:[Key(0)]
   91|     public string Member2 { get; set; }|}
   92| }
   93| ";
   94| 
   95|         await new VerifyCS.Test
   96|         {
   97|             TestCode = input,
   98|             MarkupOptions = MarkupOptions.UseFirstDescriptor,
   99|         }.RunAsync();
  100|     }
  101| 
  102|     [Fact]
  103|     public async Task DuplicateStringKeysAreReportedWithoutAnalyzerFailure()
  104|     {
  105|         string input = Preamble + @"
  106| [MessagePackObject(SuppressSourceGeneration = true)]
  107| public class Foo
  108| {
  109|     [Key(""a"")]
  110|     public string Member1 { get; set; }
  111| 
  112|     {|MsgPack005:[Key(""a"")]
  113|     public string Member2 { get; set; }|}
  114| }
  115| ";
  116| 
  117|         await new VerifyCS.Test
  118|         {
  119|             TestCode = input,
  120|             MarkupOptions = MarkupOptions.UseFirstDescriptor,
  121|         }.RunAsync();
  122|     }
  123| 
  124|     [Fact]
  125|     public async Task MixedKeyKindsAreReportedWithoutAnalyzerFailure()
  126|     {
  127|         string input = Preamble + @"
  128| [MessagePackObject(SuppressSourceGeneration = true)]
  129| public class Foo
  130| {
  131|     [Key(0)]
  132|     public string Member1 { get; set; }
  133| 
  134|     {|MsgPack005:[Key(""Member2"")]
  135|     public string Member2 { get; set; }|}
  136| }
  137| ";
  138| 
  139|         await new VerifyCS.Test
  140|         {
  141|             TestCode = input,
  142|             MarkupOptions = MarkupOptions.UseFirstDescriptor,
  143|         }.RunAsync();
  144|     }
  145| 
  146|     [Fact]
  147|     public async Task DuplicateKeysAreReportedWithoutAnalyzerFailureForGeneratedTypes()
  148|     {
  149|         string input = Preamble + @"
  150| [MessagePackObject]
  151| public class Foo
  152| {
  153|     [Key(0)]
  154|     public string Member1 { get; set; }
  155| 
  156|     {|MsgPack005:[Key(0)]
  157|     public string Member2 { get; set; }|}
  158| }
  159| ";
  160| 
  161|         await new VerifyCS.Test
  162|         {
  163|             TestCode = input,
  164|             MarkupOptions = MarkupOptions.UseFirstDescriptor,
  165|         }.RunAsync();
  166|     }
  167| 
  168|     [Fact]
  169|     public async Task SourceGenerationOnlyDiagnosticsAreNotReportedWhenSuppressed()
  170|     {
  171|         // The partial-class requirement (MsgPack011) and the AOT-only checks (MsgPack016, MsgPack017)
  172|         // only matter when a formatter is generated, so they are not reported for a suppressed type.
  173|         string input = Preamble + @"
  174| [MessagePackObject(AllowPrivate = true, SuppressSourceGeneration = true)]
  175| public class Foo
  176| {
  177|     [Key(0)]
  178|     private string member;
  179| 
  180|     [Key(1)]
  181|     public string Prop1 { get; init; } = ""some default"";
  182| 
  183|     [Key(2)]
  184|     public string Prop2 { get; set; }
  185| }
  186| ";
  187| 
  188|         await new VerifyCS.Test
  189|         {
  190|             TestCode = input,
  191|         }.RunAsync();
  192|     }
  193| }
```

### src/MessagePack.SourceGenerator/CodeAnalysis/TypeCollector.cs at base (32258fdb), around the changed lines
```
  ... lines 1-974 not shown ...
  975|                     nestedFormatterRequired |= item.GetMethod is not null && IsPartialTypeRequired(item.GetMethod.DeclaredAccessibility);
  976|                     if (item.SetMethod is not null && IsPartialTypeRequired(item.SetMethod.DeclaredAccessibility))
  977|                     {
  978|                         nestedFormatterRequiredIfPropertyIsNotSetByDeserializingCtor.Add(item);
  979|                     }
  980| 
  981|                     var intKey = key is { Value: int intKeyValue } ? intKeyValue : default(int?);
  982|                     var stringKey = key is { Value: string stringKeyValue } ? stringKeyValue : default;
  983|                     if (intKey == null && stringKey == null)
  984|                     {
  985|                         this.reportDiagnostic?.Invoke(Diagnostic.Create(MsgPack00xMessagePackAnalyzer.BothStringAndIntKeyAreNull, ((PropertyDeclarationSyntax)item.DeclaringSyntaxReferences[0].GetSyntax()).Identifier.GetLocation(), formattedType.ToDisplayString(SymbolDisplayFormat.FullyQualifiedFormat), item.Name));
  986|                     }
  987| 
  988|                     // A property with an init accessor and an initializer has a default that will be discarded by the deserializer.
  989|                     if (suppressSourceGeneration is not true && isInitOnly)
  990|                     {
  991|                         EqualsValueClauseSyntax? initializer = item.DeclaringSyntaxReferences.Select(s => (s.GetSyntax(this.cancellationToken) as PropertyDeclarationSyntax)?.Initializer).FirstOrDefault(i => i is not null);
  992|                         if (initializer is not null)
  993|                         {
  994|                             this.reportDiagnostic?.Invoke(Diagnostic.Create(MsgPack00xMessagePackAnalyzer.AOTInitProperty, initializer.GetLocation()));
  995|                         }
  996|                     }
  997| 
  998|                     if (searchFirst)
  999|                     {
 1000|                         searchFirst = false;
 1001|                         isIntKey = intKey != null;
 1002|                     }
 1003|                     else
 1004|                     {
 1005|                         if ((isIntKey && intKey == null) || (!isIntKey && stringKey == null))
 1006|                         {
 1007|                             this.reportDiagnostic?.Invoke(Diagnostic.Create(MsgPack00xMessagePackAnalyzer.DoNotMixStringAndIntKeys, item.DeclaringSyntaxReferences.FirstOrDefault()?.GetSyntax().GetLocation()));
 1008|                         }
 1009|                     }
 1010| 
 1011|                     if (isIntKey)
 1012|                     {
 1013|                         if (intMembers.ContainsKey(intKey!.Value))
 1014|                         {
 1015|                             this.reportDiagnostic?.Invoke(Diagnostic.Create(MsgPack00xMessagePackAnalyzer.KeysMustBeUnique, item.DeclaringSyntaxReferences.FirstOrDefault()?.GetSyntax().GetLocation()));
 1016|                         }
 1017| 
 1018|                         var member = new MemberSerializationInfo(true, isWritable, isReadable, isInitOnly, item.IsRequired, intKey!.Value, item.Name, item.Name, item.Type.ToDisplayString(SymbolDisplayFormat.FullyQualifiedFormat), item.Type.ToDisplayString(BinaryWriteFormat), specialFormatter)
 1019|                         {
 1020|                             DeclaringType = GetDeclaringTypeIfColliding(item),
 1021|                         };
 1022|                         intMembers.Add(member.IntKey, (member, item.Type));
 1023|                     }
 1024|                     else if (stringKey is not null)
 1025|                     {
 1026|                         if (stringMembers.ContainsKey(stringKey!))
 1027|                         {
 1028|                             this.reportDiagnostic?.Invoke(Diagnostic.Create(MsgPack00xMessagePackAnalyzer.KeysMustBeUnique, item.DeclaringSyntaxReferences.FirstOrDefault()?.GetSyntax().GetLocation()));
 1029|                         }
 1030| 
 1031|                         var member = new MemberSerializationInfo(true, isWritable, isReadable, isInitOnly, item.IsRequired, hiddenIntKey++, stringKey!, item.Name, item.Type.ToDisplayString(SymbolDisplayFormat.FullyQualifiedFormat), item.Type.ToDisplayString(BinaryWriteFormat), specialFormatter)
 1032|                         {
 1033|                             DeclaringType = GetDeclaringTypeIfColliding(item),
 1034|                         };
 1035|                         stringMembers.Add(member.StringKey, (member, item.Type));
 1036|                     }
 1037| 
 1038|                     var messagePackFormatter = item.GetAttributes().FirstOrDefault(x => x.AttributeClass.ApproximatelyEqual(this.typeReferences.FormatterAttribute))?.ConstructorArguments[0];
 1039| 
 1040|                     if (messagePackFormatter == null)
 1041|                     {
 1042|                         // recursive collect
 1043|                         this.CollectCore(item.Type, item);
 1044|                     }
 1045|                 }
 1046|             }
 1047| 
 1048|             foreach (IFieldSymbol item in formattedType.GetAllMembers().OfType<IFieldSymbol>())
 1049|             {
 1050|                 if (item.IsImplicitlyDeclared || item.IsStatic)
 1051|                 {
 1052|                     continue;
 1053|                 }
 1054| 
 1055|                 if (item.GetAttributes().Any(x => x.AttributeClass.ApproximatelyEqual(this.typeReferences.IgnoreAttribute)))
 1056|                 {
 1057|                     nonPublicMembersAreSerialized |= (item.DeclaredAccessibility & Accessibility.Public) != Accessibility.Public;
 1058|                     continue;
 1059|                 }
 1060| 
 1061|                 FormatterDescriptor? specialFormatter = GetSpecialFormatter(item);
 1062|                 TypedConstant? key = item.GetAttributes().FirstOrDefault(x => x.AttributeClass.ApproximatelyEqual(this.typeReferences.KeyAttribute))?.ConstructorArguments[0];
 1063|                 if (key is null)
 1064|                 {
 1065|                     if (contractAttr is not null)
 1066|                     {
 1067|                         // If the member is attributed with a type derived from KeyAttribute, that's incompatible with source generation
 1068|                         // since we cannot know what the key is using only C# syntax and the semantic model.
  ... lines 1069-1107 not shown ...
 1108|                                         {
 1109|                                             deferredDiagnosticsForNonPublicMembers.Add(diagnostic);
 1110|                                         }
 1111|                                     }
 1112|                                 }
 1113|                             }
 1114|                         }
 1115|                     }
 1116|                 }
 1117|                 else
 1118|                 {
 1119|                     // If this attributed member is non-public, then all non-public members should be attributed.
 1120|                     nonPublicMembersAreSerialized |= (item.DeclaredAccessibility & Accessibility.Public) != Accessibility.Public;
 1121| 
 1122|                     nestedFormatterRequired |= IsPartialTypeRequired(item.DeclaredAccessibility);
 1123| 
 1124|                     var intKey = key is { Value: int intKeyValue } ? intKeyValue : default(int?);
 1125|                     var stringKey = key is { Value: string stringKeyValue } ? stringKeyValue : default;
 1126|                     if (intKey == null && stringKey == null)
 1127|                     {
 1128|                         this.reportDiagnostic?.Invoke(Diagnostic.Create(MsgPack00xMessagePackAnalyzer.BothStringAndIntKeyAreNull, item.DeclaringSyntaxReferences.FirstOrDefault()?.GetSyntax().GetLocation()));
 1129|                     }
 1130| 
 1131|                     if (searchFirst)
 1132|                     {
 1133|                         searchFirst = false;
 1134|                         isIntKey = intKey != null;
 1135|                     }
 1136|                     else
 1137|                     {
 1138|                         if ((isIntKey && intKey == null) || (!isIntKey && stringKey == null))
 1139|                         {
 1140|                             this.reportDiagnostic?.Invoke(Diagnostic.Create(MsgPack00xMessagePackAnalyzer.DoNotMixStringAndIntKeys, item.DeclaringSyntaxReferences.FirstOrDefault()?.GetSyntax().GetLocation()));
 1141|                         }
 1142|                     }
 1143| 
 1144|                     if (isIntKey)
 1145|                     {
 1146|                         if (intMembers.ContainsKey(intKey!.Value))
 1147|                         {
 1148|                             this.reportDiagnostic?.Invoke(Diagnostic.Create(MsgPack00xMessagePackAnalyzer.KeysMustBeUnique, item.DeclaringSyntaxReferences.FirstOrDefault()?.GetSyntax().GetLocation()));
 1149|                         }
 1150| 
 1151|                         var member = new MemberSerializationInfo(true, IsWritable: !item.IsReadOnly, IsReadable: true, IsInitOnly: false, item.IsRequired, intKey!.Value, item.Name, item.Name, item.Type.ToDisplayString(SymbolDisplayFormat.FullyQualifiedFormat), item.Type.ToDisplayString(BinaryWriteFormat), specialFormatter)
 1152|                         {
 1153|                             DeclaringType = GetDeclaringTypeIfColliding(item),
 1154|                         };
 1155|                         intMembers.Add(member.IntKey, (member, item.Type));
 1156|                     }
 1157|                     else
 1158|                     {
 1159|                         if (stringMembers.ContainsKey(stringKey!))
 1160|                         {
 1161|                             this.reportDiagnostic?.Invoke(Diagnostic.Create(MsgPack00xMessagePackAnalyzer.KeysMustBeUnique, item.DeclaringSyntaxReferences.FirstOrDefault()?.GetSyntax().GetLocation()));
 1162|                         }
 1163| 
 1164|                         var member = new MemberSerializationInfo(true, IsWritable: !item.IsReadOnly, IsReadable: true, IsInitOnly: false, item.IsRequired, hiddenIntKey++, stringKey!, item.Name, item.Type.ToDisplayString(SymbolDisplayFormat.FullyQualifiedFormat), item.Type.ToDisplayString(BinaryWriteFormat), specialFormatter)
 1165|                         {
 1166|                             DeclaringType = GetDeclaringTypeIfColliding(item),
 1167|                         };
 1168|                         stringMembers.Add(member.StringKey, (member, item.Type));
 1169|                     }
 1170| 
 1171|                     var messagePackFormatter = item.GetAttributes().FirstOrDefault(x => x.AttributeClass.ApproximatelyEqual(this.typeReferences.FormatterAttribute))?.ConstructorArguments[0];
 1172| 
 1173|                     if (messagePackFormatter == null)
 1174|                     {
 1175|                         // recursive collect
 1176|                         this.CollectCore(item.Type, item);
 1177|                     }
 1178|                 }
 1179|             }
 1180|         }
 1181| 
 1182|         // If we discovered midway through that we should be reporting diagnostics for non-public members,
 1183|         // report the ones we missed along the way.
 1184|         if ((nonPublicMembersAreSerialized || allowPrivateAttribute is true) && this.reportDiagnostic is not null)
 1185|         {
 1186|             foreach (Diagnostic deferred in deferredDiagnosticsForNonPublicMembers)
 1187|             {
 1188|                 this.reportDiagnostic(deferred);
 1189|             }
 1190|         }
 1191| 
 1192|         // GetConstructor
 1193|         var ctorEnumerator = default(IEnumerator<IMethodSymbol>);
 1194|         var ctor = formattedType.Constructors.SingleOrDefault(x => x.GetAttributes().Any(y => y.AttributeClass != null && y.AttributeClass.ApproximatelyEqual(this.typeReferences.SerializationConstructorAttribute)));
 1195|         if (ctor is null)
 1196|         {
 1197|             ctorEnumerator = formattedType.Constructors
 1198|                 .OrderByDescending(x => x.DeclaredAccessibility)
 1199|                 .ThenByDescending(x => x.Parameters.Length)
 1200|                 .GetEnumerator();
 1201| 
  ... lines 1202-1491 not shown ...
```

## What you did NOT get (refuse anything that depends on it)
- src/MessagePack.SourceGenerator/CodeAnalysis/TypeCollector.cs at base: only ±30 lines around the changes (the full file did not fit the budget)
- README.md: diff only, full file not provided (doc)
- the upstream issue page itself (only its URL); other files of the repository; build and test logs (only the facts.json summaries)

Return only the JSON object described in the brief.