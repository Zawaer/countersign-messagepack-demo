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
# Change 2297: branch ju26-issue-2297, base 32258fdbee4bcd653c79f51b4376b5103c6f4d27, head a0aa5ab2de7f5a669d97e37184a89034c1de82b6
Commit message: implement issue #2297 : Add ExcludeFromCodeCoverage attribute to generated code
Upstream issue: https://github.com/MessagePack-CSharp/MessagePack-CSharp/issues/2297

## Requirement set (requirements/2297.yaml)
```yaml
# PLACEHOLDER from upstream issue #2297
change: "2297"
branch: ju26-issue-2297
source: https://github.com/MessagePack-CSharp/MessagePack-CSharp/issues/2297
official: false
requirements:
  - id: REQ-2297-F1
    type: functional
    text: "Add ExcludeFromCodeCoverage attribute to generated code."
```

## facts.json (deterministic checks; cite their ids and test names)
```json
{
 "change": "2297",
 "branch": "ju26-issue-2297",
 "base": "32258fdb",
 "head": "a0aa5ab2",
 "base_full": "32258fdbee4bcd653c79f51b4376b5103c6f4d27",
 "head_full": "a0aa5ab2de7f5a669d97e37184a89034c1de82b6",
 "commit_message": "implement issue #2297 : Add ExcludeFromCodeCoverage attribute to generated code",
 "author": "Stelian Vultur",
 "agent_written": true,
 "diff": {
  "files": 237,
  "insertions": 1383,
  "deletions": 9,
  "by_kind": {
   "doc": 1,
   "generated": 228,
   "source": 7,
   "test": 1
  },
  "by_file": [
   {
    "path": "README.md",
    "ins": 3,
    "del": 0,
    "kind": "doc"
   },
   {
    "path": "src/MessagePack.SourceGenerator/Transforms/CompositeResolverTemplate.cs",
    "ins": 4,
    "del": 1,
    "kind": "generated"
   },
   {
    "path": "src/MessagePack.SourceGenerator/Transforms/CompositeResolverTemplate.tt",
    "ins": 6,
    "del": 0,
    "kind": "source"
   },
   {
    "path": "src/MessagePack.SourceGenerator/Transforms/EnumTemplate.cs",
    "ins": 1,
    "del": 1,
    "kind": "generated"
   },
   {
    "path": "src/MessagePack.SourceGenerator/Transforms/EnumTemplate.tt",
    "ins": 3,
    "del": 0,
    "kind": "source"
   },
   {
    "path": "src/MessagePack.SourceGenerator/Transforms/FormatterTemplate.cs",
    "ins": 1,
    "del": 1,
    "kind": "generated"
   },
   {
    "path": "src/MessagePack.SourceGenerator/Transforms/FormatterTemplate.tt",
    "ins": 3,
    "del": 0,
    "kind": "source"
   },
   {
    "path": "src/MessagePack.SourceGenerator/Transforms/ResolverTemplate.cs",
    "ins": 5,
    "del": 2,
    "kind": "generated"
   },
   {
    "path": "src/MessagePack.SourceGenerator/Transforms/ResolverTemplate.tt",
    "ins": 9,
    "del": 0,
    "kind": "source"
   },
   {
    "path": "src/MessagePack.SourceGenerator/Transforms/StringKey/StringKeyFormatterTemplate.cs",
    "ins": 1,
    "del": 1,
    "kind": "generated"
   },
   {
    "path": "src/MessagePack.SourceGenerator/Transforms/StringKey/StringKeyFormatterTemplate.tt",
    "ins": 3,
    "del": 0,
    "kind": "source"
   },
   {
    "path": "src/MessagePack.SourceGenerator/Transforms/TransformUtilities.cs",
    "ins": 1,
    "del": 1,
    "kind": "source"
   },
   {
    "path": "src/MessagePack.SourceGenerator/Transforms/UnionTemplate.cs",
    "ins": 1,
    "del": 1,
    "kind": "generated"
   },
   {
    "path": "src/MessagePack.SourceGenerator/Transforms/UnionTemplate.tt",
    "ins": 3,
    "del": 0,
    "kind": "source"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/CodeCoverageExclusionTests.cs",
    "ins": 130,
    "del": 0,
    "kind": "test"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/AdditionalAllowTypes/Formatters.MessagePack.GeneratedMessagePackResolver.TypeWithAutoGeneratedFormatterFormatter.g.cs",
    "ins": 3,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/AdditionalAllowTypes/MessagePack.GeneratedMessagePackResolver.g.cs",
    "ins": 9,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/AdditionalFormatterTypes/DefiningProject.MessagePack.GeneratedMessagePackResolver.g.cs",
    "ins": 9,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/AdditionalFormatterTypes/TestProject.Formatters.MessagePack.GeneratedMessagePackResolver.TypeWithAutoGeneratedFormatterFormatter.g.cs",
    "ins": 3,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/AdditionalFormatterTypes/TestProject.MessagePack.GeneratedMessagePackResolver.g.cs",
    "ins": 9,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/AdditionalFormatterTypes_RedundantAttribute/Formatters.MessagePack.GeneratedMessagePackResolver.TypeWithAutoGeneratedFormatterFormatter.g.cs",
    "ins": 3,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/AdditionalFormatterTypes_RedundantAttribute/MessagePack.GeneratedMessagePackResolver.g.cs",
    "ins": 9,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/Array2DJaggedProperty/Formatters.MessagePack.GeneratedMessagePackResolver.ContainerObjectFormatter.g.cs",
    "ins": 3,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/Array2DJaggedProperty/MessagePack.GeneratedMessagePackResolver.g.cs",
    "ins": 9,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/ArrayTypedProperty/Formatters.MessagePack.GeneratedMessagePackResolver.ContainerObjectFormatter.g.cs",
    "ins": 3,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/ArrayTypedProperty/Formatters.MessagePack.GeneratedMessagePackResolver.SubObjectFormatter.g.cs",
    "ins": 3,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/ArrayTypedProperty/MessagePack.GeneratedMessagePackResolver.g.cs",
    "ins": 9,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/CanGenerateMessagePackFormatterAttr/Formatters.MessagePack.GeneratedMessagePackResolver.TempProject.BarFormatter.g.cs",
    "ins": 3,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/CanGenerateMessagePackFormatterAttr/MessagePack.GeneratedMessagePackResolver.g.cs",
    "ins": 9,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/CompositeResolver_MixedResolverTypes/MyResolver.g.cs",
    "ins": 6,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/CompositeResolver_Nested/MyResolver.g.cs",
    "ins": 6,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/CustomFormatterForGenericWithConstraints/Formatters.MessagePack.GeneratedMessagePackResolver.SampleObjectFormatter.g.cs",
    "ins": 3,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/CustomFormatterForGenericWithConstraints/MessagePack.GeneratedMessagePackResolver.g.cs",
    "ins": 9,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/CustomFormatterViaAttributeOnField(False)/Formatters.MessagePack.GeneratedMessagePackResolver.HasFieldWithCustomFormatterAttributeFormatter.g.cs",
    "ins": 3,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/CustomFormatterViaAttributeOnField(False)/MessagePack.GeneratedMessagePackResolver.g.cs",
    "ins": 9,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/CustomFormatterViaAttributeOnField(True)/Formatters.MessagePack.GeneratedMessagePackResolver.HasFieldWithCustomFormatterAttributeFormatter.g.cs",
    "ins": 3,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/CustomFormatterViaAttributeOnField(True)/MessagePack.GeneratedMessagePackResolver.g.cs",
    "ins": 9,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/CustomFormatterViaAttributeOnProperty(False)/Formatters.MessagePack.GeneratedMessagePackResolver.HasPropertyWithCustomFormatterAttributeFormatter.g.cs",
    "ins": 3,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/CustomFormatterViaAttributeOnProperty(False)/MessagePack.GeneratedMessagePackResolver.g.cs",
    "ins": 9,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/CustomFormatterViaAttributeOnProperty(True)/Formatters.MessagePack.GeneratedMessagePackResolver.HasPropertyWithCustomFormatterAttributeFormatter.g.cs",
    "ins": 3,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/CustomFormatterViaAttributeOnProperty(True)/MessagePack.GeneratedMessagePackResolver.g.cs",
    "ins": 9,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/CustomFormatterWithSingletonPattern/Formatters.MessagePack.GeneratedMessagePackResolver.GFormatter.g.cs",
    "ins": 3,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/CustomFormatterWithSingletonPattern/MessagePack.GeneratedMessagePackResolver.g.cs",
    "ins": 9,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/DeserializingConstructorParameterMemberTypeAssignability_Incompatible/MessagePack.GeneratedMessagePackResolver.g.cs",
    "ins": 9,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/DeserializingConstructorParameterMemberTypeAssignability_MemberAssignsToParamType/Formatters.MessagePack.GeneratedMessagePackResolver.AFormatter.g.cs",
    "ins": 3,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/DeserializingConstructorParameterMemberTypeAssignability_MemberAssignsToParamType/MessagePack.GeneratedMessagePackResolver.g.cs",
    "ins": 9,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/EmbeddedTypes/Formatters.MessagePack.GeneratedMessagePackResolver.AFormatter.g.cs",
    "ins": 3,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/EmbeddedTypes/MessagePack.GeneratedMessagePackResolver.g.cs",
    "ins": 9,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/EnumFormatter(Namespace, False)/Formatters.MessagePack.GeneratedMessagePackResolver.MyTestNamespace.MyEnumFormatter.g.cs",
    "ins": 3,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/EnumFormatter(Namespace, False)/Formatters.MessagePack.GeneratedMessagePackResolver.MyTestNamespace.MyMessagePackObjectFormatter.g.cs",
    "ins": 3,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/EnumFormatter(Namespace, False)/MessagePack.GeneratedMessagePackResolver.g.cs",
    "ins": 9,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/EnumFormatter(Namespace, True)/Formatters.MessagePack.GeneratedMessagePackResolver.MyTestNamespace.MyEnumFormatter.g.cs",
    "ins": 3,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/EnumFormatter(Namespace, True)/Formatters.MessagePack.GeneratedMessagePackResolver.MyTestNamespace.MyMessagePackObjectFormatter.g.cs",
    "ins": 3,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/EnumFormatter(Namespace, True)/MessagePack.GeneratedMessagePackResolver.g.cs",
    "ins": 9,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/EnumFormatter(NestingClass, False)/Formatters.MessagePack.GeneratedMessagePackResolver.ContainingClass.MyEnumFormatter.g.cs",
    "ins": 3,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/EnumFormatter(NestingClass, False)/Formatters.MessagePack.GeneratedMessagePackResolver.ContainingClass.MyMessagePackObjectFormatter.g.cs",
    "ins": 3,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/EnumFormatter(NestingClass, False)/MessagePack.GeneratedMessagePackResolver.g.cs",
    "ins": 9,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/EnumFormatter(NestingClass, True)/Formatters.MessagePack.GeneratedMessagePackResolver.ContainingClass.MyEnumFormatter.g.cs",
    "ins": 3,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/EnumFormatter(NestingClass, True)/Formatters.MessagePack.GeneratedMessagePackResolver.ContainingClass.MyMessagePackObjectFormatter.g.cs",
    "ins": 3,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/EnumFormatter(NestingClass, True)/MessagePack.GeneratedMessagePackResolver.g.cs",
    "ins": 9,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/EnumFormatter(None, False)/Formatters.MessagePack.GeneratedMessagePackResolver.MyEnumFormatter.g.cs",
    "ins": 3,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/EnumFormatter(None, False)/Formatters.MessagePack.GeneratedMessagePackResolver.MyMessagePackObjectFormatter.g.cs",
    "ins": 3,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/EnumFormatter(None, False)/MessagePack.GeneratedMessagePackResolver.g.cs",
    "ins": 9,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/EnumFormatter(None, True)/Formatters.MessagePack.GeneratedMessagePackResolver.MyEnumFormatter.g.cs",
    "ins": 3,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/EnumFormatter(None, True)/Formatters.MessagePack.GeneratedMessagePackResolver.MyMessagePackObjectFormatter.g.cs",
    "ins": 3,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/EnumFormatter(None, True)/MessagePack.GeneratedMessagePackResolver.g.cs",
    "ins": 9,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/EnumFormatter_CollidingTypeNames/Formatters.MessagePack.GeneratedMessagePackResolver.MyMessagePackObjectFormatter.g.cs",
    "ins": 3,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/EnumFormatter_CollidingTypeNames/Formatters.MessagePack.GeneratedMessagePackResolver.NS1.MyEnumFormatter.g.cs",
    "ins": 3,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/EnumFormatter_CollidingTypeNames/Formatters.MessagePack.GeneratedMessagePackResolver.NS2.MyEnumFormatter.g.cs",
    "ins": 3,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/EnumFormatter_CollidingTypeNames/MessagePack.GeneratedMessagePackResolver.g.cs",
    "ins": 9,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/FormatterForClassWithPrivateMembers(class)/Formatters.MyObject.MyObjectFormatter.g.cs",
    "ins": 3,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/FormatterForClassWithPrivateMembers(class)/MessagePack.GeneratedMessagePackResolver.g.cs",
    "ins": 9,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/FormatterForClassWithPrivateMembers(record struct)/Formatters.MyObject.MyObjectFormatter.g.cs",
    "ins": 3,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/FormatterForClassWithPrivateMembers(record struct)/MessagePack.GeneratedMessagePackResolver.g.cs",
    "ins": 9,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/FormatterForClassWithPrivateMembers(record)/Formatters.MyObject.MyObjectFormatter.g.cs",
    "ins": 3,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/FormatterForClassWithPrivateMembers(record)/MessagePack.GeneratedMessagePackResolver.g.cs",
    "ins": 9,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/FormatterForClassWithPrivateMembers(struct)/Formatters.MyObject.MyObjectFormatter.g.cs",
    "ins": 3,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/FormatterForClassWithPrivateMembers(struct)/MessagePack.GeneratedMessagePackResolver.g.cs",
    "ins": 9,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/FormatterForClassWithPrivateMembers_MapMode/Formatters.MyObject.MyObjectFormatter.g.cs",
    "ins": 3,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/FormatterForClassWithPrivateMembers_MapMode/MessagePack.GeneratedMessagePackResolver.g.cs",
    "ins": 9,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/FormatterForClassWithPrivateMembers_WithNamespace/Formatters.A.MyObject.MyObjectFormatter.g.cs",
    "ins": 3,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/FormatterForClassWithPrivateMembers_WithNamespace/MessagePack.GeneratedMessagePackResolver.g.cs",
    "ins": 9,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/GenericCustomFormatter/Formatters.SampleObject.SampleObjectFormatter.g.cs",
    "ins": 3,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/GenericCustomFormatter/MessagePack.GeneratedMessagePackResolver.g.cs",
    "ins": 9,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/GenericDataTypeWithPrivateMember/Formatters.HasPrivateSerializedMemberAndIsGenericNamed`1.HasPrivateSerializedMemberAndIsGenericNamedFormatter.g.cs",
    "ins": 5,
    "del": 1,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/GenericDataTypeWithPrivateMember/Formatters.HasPrivateSerializedMemberAndIsGenericOrdinal`1.HasPrivateSerializedMemberAndIsGenericOrdinalFormatter.g.cs",
    "ins": 4,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/GenericDataTypeWithPrivateMember/MessagePack.GeneratedMessagePackResolver.g.cs",
    "ins": 9,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/GenericType/Formatters.MessagePack.GeneratedMessagePackResolver.ContainerObjectFormatter.g.cs",
    "ins": 3,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/GenericType/Formatters.MessagePack.GeneratedMessagePackResolver.MyGenericTypeFormatter`1.g.cs",
    "ins": 3,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/GenericType/MessagePack.GeneratedMessagePackResolver.g.cs",
    "ins": 9,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/GenericTypeArg/Formatters.MessagePack.GeneratedMessagePackResolver.GenericClassFormatter`2.g.cs",
    "ins": 3,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/GenericTypeArg/MessagePack.GeneratedMessagePackResolver.g.cs",
    "ins": 9,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/GenericType_CollidingTypeNames/Formatters.MessagePack.GeneratedMessagePackResolver.MyMessagePackObjectFormatter.g.cs",
    "ins": 3,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/GenericType_CollidingTypeNames/Formatters.MessagePack.GeneratedMessagePackResolver.NS1.MyTypeFormatter`1.g.cs",
    "ins": 3,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/GenericType_CollidingTypeNames/Formatters.MessagePack.GeneratedMessagePackResolver.NS2.MyTypeFormatter`1.g.cs",
    "ins": 3,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/GenericType_CollidingTypeNames/MessagePack.GeneratedMessagePackResolver.g.cs",
    "ins": 9,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/GenericWithConstraintsThatReferenceTypeParameter/Formatters.MessagePack.GeneratedMessagePackResolver.GenericConstrainedClassIntKeyFormatter`2.g.cs",
    "ins": 3,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/GenericWithConstraintsThatReferenceTypeParameter/MessagePack.GeneratedMessagePackResolver.g.cs",
    "ins": 9,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/GenericsOfT1T2Formatter/Formatters.MessagePack.GeneratedMessagePackResolver.TempProject.MyGenericObjectFormatter`2.g.cs",
    "ins": 3,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/GenericsOfT1T2Formatter/Formatters.MessagePack.GeneratedMessagePackResolver.TempProject.MyObjectFormatter.g.cs",
    "ins": 3,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/GenericsOfT1T2Formatter/Formatters.MessagePack.GeneratedMessagePackResolver.TempProject.MyObjectNestedFormatter.g.cs",
    "ins": 3,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/GenericsOfT1T2Formatter/MessagePack.GeneratedMessagePackResolver.g.cs",
    "ins": 9,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/GenericsOfTFormatter/Formatters.MessagePack.GeneratedMessagePackResolver.TempProject.MyGenericObjectFormatter`1.g.cs",
    "ins": 3,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/GenericsOfTFormatter/Formatters.MessagePack.GeneratedMessagePackResolver.TempProject.MyObjectFormatter.g.cs",
    "ins": 3,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/GenericsOfTFormatter/Formatters.MessagePack.GeneratedMessagePackResolver.TempProject.MyObjectNestedFormatter.g.cs",
    "ins": 3,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/GenericsOfTFormatter/MessagePack.GeneratedMessagePackResolver.g.cs",
    "ins": 9,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/GenericsOfTFormatter_FormatterOnly/Formatters.MessagePack.GeneratedMessagePackResolver.TempProject.MyGenericObjectFormatter`1.g.cs",
    "ins": 3,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/GenericsOfTFormatter_FormatterOnly/MessagePack.GeneratedMessagePackResolver.g.cs",
    "ins": 9,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/GenericsOfTFormatter_WithKnownTypes/Formatters.MessagePack.GeneratedMessagePackResolver.TempProject.MyGenericObjectFormatter`1.g.cs",
    "ins": 3,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/GenericsOfTFormatter_WithKnownTypes/Formatters.MessagePack.GeneratedMessagePackResolver.TempProject.MyObject2Formatter.g.cs",
    "ins": 3,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/GenericsOfTFormatter_WithKnownTypes/Formatters.MessagePack.GeneratedMessagePackResolver.TempProject.MyObjectFormatter.g.cs",
    "ins": 3,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/GenericsOfTFormatter_WithKnownTypes/MessagePack.GeneratedMessagePackResolver.g.cs",
    "ins": 9,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/GenericsUnionFormatter/Formatters.MessagePack.GeneratedMessagePackResolver.TempProject.WrapperFormatter`1.g.cs",
    "ins": 3,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/GenericsUnionFormatter/MessagePack.GeneratedMessagePackResolver.g.cs",
    "ins": 9,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/GenericsUnionFormatter_Nested/Formatters.MessagePack.GeneratedMessagePackResolver.TempProject.MyGenericObjectFormatter`1.g.cs",
    "ins": 3,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/GenericsUnionFormatter_Nested/Formatters.MessagePack.GeneratedMessagePackResolver.TempProject.MyInnerGenericObjectFormatter`1.g.cs",
    "ins": 3,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/GenericsUnionFormatter_Nested/Formatters.MessagePack.GeneratedMessagePackResolver.TempProject.WrapperFormatter`1.g.cs",
    "ins": 3,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/GenericsUnionFormatter_Nested/MessagePack.GeneratedMessagePackResolver.g.cs",
    "ins": 9,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/Generics_Constraints_Multiple/Formatters.MessagePack.GeneratedMessagePackResolver.TempProject.MyGenericObjectFormatter`4.g.cs",
    "ins": 3,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/Generics_Constraints_Multiple/MessagePack.GeneratedMessagePackResolver.g.cs",
    "ins": 9,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/Generics_Constraints_NullableReferenceType/Formatters.MessagePack.GeneratedMessagePackResolver.TempProject.MyGenericObjectFormatter`4.g.cs",
    "ins": 3,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/Generics_Constraints_NullableReferenceType/MessagePack.GeneratedMessagePackResolver.g.cs",
    "ins": 9,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/Generics_Constraints_ReferenceType_Nullable/Formatters.MessagePack.GeneratedMessagePackResolver.TempProject.MyGenericObjectFormatter`2.g.cs",
    "ins": 3,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/Generics_Constraints_ReferenceType_Nullable/MessagePack.GeneratedMessagePackResolver.g.cs",
    "ins": 9,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/Generics_Constraints_Struct/Formatters.MessagePack.GeneratedMessagePackResolver.TempProject.MyGenericObjectFormatter`1.g.cs",
    "ins": 3,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/Generics_Constraints_Struct/MessagePack.GeneratedMessagePackResolver.g.cs",
    "ins": 9,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/Generics_Constraints_Type/Formatters.MessagePack.GeneratedMessagePackResolver.TempProject.MyGenericObjectFormatter`1.g.cs",
    "ins": 3,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/Generics_Constraints_Type/MessagePack.GeneratedMessagePackResolver.g.cs",
    "ins": 9,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/Generics_Defined_In_ReferencedProject/DefiningProject.Formatters.TempProject.MyResolver.TempProject.MyGenericObjectFormatter`1.g.cs",
    "ins": 3,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/Generics_Defined_In_ReferencedProject/DefiningProject.TempProject.MyResolver.g.cs",
    "ins": 9,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/Generics_Defined_In_ReferencedProject/TestProject.Formatters.MessagePack.GeneratedMessagePackResolver.TempProject.MyGenericObjectFormatter`1.g.cs",
    "ins": 3,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/Generics_Defined_In_ReferencedProject/TestProject.Formatters.MessagePack.GeneratedMessagePackResolver.TempProject.MyObjectFormatter.g.cs",
    "ins": 3,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/Generics_Defined_In_ReferencedProject/TestProject.Formatters.MessagePack.GeneratedMessagePackResolver.TempProject.MyObjectNestedFormatter.g.cs",
    "ins": 3,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/Generics_Defined_In_ReferencedProject/TestProject.MessagePack.GeneratedMessagePackResolver.g.cs",
    "ins": 9,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/ImplicitFormatterTypes/Formatters.MessagePack.GeneratedMessagePackResolver.TypeWithAutoGeneratedFormatterFormatter.g.cs",
    "ins": 3,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/ImplicitFormatterTypes/MessagePack.GeneratedMessagePackResolver.g.cs",
    "ins": 9,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/InterfaceUnionUsedWithNullableRefAnnotation/Formatters.MessagePack.GeneratedMessagePackResolver.IMyTypeFormatter.g.cs",
    "ins": 3,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/InterfaceUnionUsedWithNullableRefAnnotation/Formatters.MessagePack.GeneratedMessagePackResolver.UnionContainerFormatter.g.cs",
    "ins": 3,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/InterfaceUnionUsedWithNullableRefAnnotation/MessagePack.GeneratedMessagePackResolver.g.cs",
    "ins": 9,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/MixType_CollidingTypeNames/Formatters.MessagePack.GeneratedMessagePackResolver.MyMessagePackObjectFormatter.g.cs",
    "ins": 3,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/MixType_CollidingTypeNames/Formatters.MessagePack.GeneratedMessagePackResolver.NS1.MyTypeFormatter.g.cs",
    "ins": 3,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/MixType_CollidingTypeNames/Formatters.MessagePack.GeneratedMessagePackResolver.NS2.MyTypeFormatter.g.cs",
    "ins": 3,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/MixType_CollidingTypeNames/Formatters.MessagePack.GeneratedMessagePackResolver.NS3.MyTypeFormatter`1.g.cs",
    "ins": 3,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/MixType_CollidingTypeNames/MessagePack.GeneratedMessagePackResolver.g.cs",
    "ins": 9,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/MultipleFunctionalCustomFormattersForType_MultiFormatter/MessagePack.GeneratedMessagePackResolver.g.cs",
    "ins": 9,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/MultipleFunctionalCustomFormattersForType_OnlyOneNonExcluded/MessagePack.GeneratedMessagePackResolver.g.cs",
    "ins": 9,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/NestedGenericTypes/Formatters.MessagePack.GeneratedMessagePackResolver.TempProject.MyGenericObjectFormatter`1.g.cs",
    "ins": 3,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/NestedGenericTypes/Formatters.MessagePack.GeneratedMessagePackResolver.TempProject.MyInnerGenericObjectFormatter`1.g.cs",
    "ins": 3,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/NestedGenericTypes/Formatters.MessagePack.GeneratedMessagePackResolver.TempProject.MyObject2Formatter.g.cs",
    "ins": 3,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/NestedGenericTypes/Formatters.MessagePack.GeneratedMessagePackResolver.TempProject.MyObjectFormatter.g.cs",
    "ins": 3,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/NestedGenericTypes/Formatters.MessagePack.GeneratedMessagePackResolver.TempProject.WrapperFormatter`1.g.cs",
    "ins": 3,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/NestedGenericTypes/MessagePack.GeneratedMessagePackResolver.g.cs",
    "ins": 9,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/NestedMessagePackObjects/Formatters.MessagePack.GeneratedMessagePackResolver.A.B.CFormatter.g.cs",
    "ins": 3,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/NestedMessagePackObjects/Formatters.MessagePack.GeneratedMessagePackResolver.A.BFormatter.g.cs",
    "ins": 3,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/NestedMessagePackObjects/MessagePack.GeneratedMessagePackResolver.g.cs",
    "ins": 9,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/NestedMessagePackObjects_Array/Formatters.MessagePack.GeneratedMessagePackResolver.A.B.CFormatter.g.cs",
    "ins": 3,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/NestedMessagePackObjects_Array/Formatters.MessagePack.GeneratedMessagePackResolver.A.BFormatter.g.cs",
    "ins": 3,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/NestedMessagePackObjects_Array/MessagePack.GeneratedMessagePackResolver.g.cs",
    "ins": 9,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/NoFieldWithCustomFormatterCollected/Formatters.MessagePack.GeneratedMessagePackResolver.TestFormatter.g.cs",
    "ins": 3,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/NoFieldWithCustomFormatterCollected/MessagePack.GeneratedMessagePackResolver.g.cs",
    "ins": 9,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/NoPrivateAccessNeeded/Formatters.MessagePack.GeneratedMessagePackResolver.Test3Formatter.g.cs",
    "ins": 3,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/NoPrivateAccessNeeded/MessagePack.GeneratedMessagePackResolver.g.cs",
    "ins": 9,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/NoPrivateMemberCollected/Formatters.MessagePack.GeneratedMessagePackResolver.TestFormatter.g.cs",
    "ins": 3,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/NoPrivateMemberCollected/MessagePack.GeneratedMessagePackResolver.g.cs",
    "ins": 9,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/NonDefaultDeserializingConstructor_Private/Formatters.A.AFormatter.g.cs",
    "ins": 3,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/NonDefaultDeserializingConstructor_Private/MessagePack.GeneratedMessagePackResolver.g.cs",
    "ins": 9,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/NonGenericType_CollidingTypeNames/Formatters.MessagePack.GeneratedMessagePackResolver.MyMessagePackObjectFormatter.g.cs",
    "ins": 3,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/NonGenericType_CollidingTypeNames/Formatters.MessagePack.GeneratedMessagePackResolver.NS1.MyTypeFormatter.g.cs",
    "ins": 3,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/NonGenericType_CollidingTypeNames/Formatters.MessagePack.GeneratedMessagePackResolver.NS2.MyTypeFormatter.g.cs",
    "ins": 3,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/NonGenericType_CollidingTypeNames/MessagePack.GeneratedMessagePackResolver.g.cs",
    "ins": 9,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/NullableFormatter/Formatters.MessagePack.GeneratedMessagePackResolver.TempProject.MyEnumFormatter.g.cs",
    "ins": 3,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/NullableFormatter/Formatters.MessagePack.GeneratedMessagePackResolver.TempProject.MyObjectFormatter.g.cs",
    "ins": 3,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/NullableFormatter/MessagePack.GeneratedMessagePackResolver.g.cs",
    "ins": 9,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/OpenGenericFormatter/MessagePack.GeneratedMessagePackResolver.g.cs",
    "ins": 9,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/PropertiesGetterOnlyDefaultValue/Formatters.MessagePack.GeneratedMessagePackResolver.TempProject.MyMessagePackObjectFormatter.g.cs",
    "ins": 3,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/PropertiesGetterOnlyDefaultValue/MessagePack.GeneratedMessagePackResolver.g.cs",
    "ins": 9,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/PropertiesGetterOnlyIgnore/Formatters.MessagePack.GeneratedMessagePackResolver.TempProject.MyMessagePackObjectFormatter.g.cs",
    "ins": 3,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/PropertiesGetterOnlyIgnore/MessagePack.GeneratedMessagePackResolver.g.cs",
    "ins": 9,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/PropertiesGetterOnlyMixed/Formatters.MessagePack.GeneratedMessagePackResolver.TempProject.MyMessagePackObjectFormatter.g.cs",
    "ins": 3,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/PropertiesGetterOnlyMixed/MessagePack.GeneratedMessagePackResolver.g.cs",
    "ins": 9,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/PropertiesGetterOnlyWithParameterizedConstructor/Formatters.MessagePack.GeneratedMessagePackResolver.TempProject.MyMessagePackObjectFormatter.g.cs",
    "ins": 3,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/PropertiesGetterOnlyWithParameterizedConstructor/MessagePack.GeneratedMessagePackResolver.g.cs",
    "ins": 9,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/PropertiesGetterOnlyWithParameterizedConstructorDefaultValue/Formatters.MessagePack.GeneratedMessagePackResolver.TempProject.MyMessagePackObjectFormatter.g.cs",
    "ins": 3,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/PropertiesGetterOnlyWithParameterizedConstructorDefaultValue/MessagePack.GeneratedMessagePackResolver.g.cs",
    "ins": 9,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/PropertiesGetterOnlyWithParameterizedConstructorPartially/Formatters.MessagePack.GeneratedMessagePackResolver.TempProject.MyMessagePackObjectFormatter.g.cs",
    "ins": 3,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/PropertiesGetterOnlyWithParameterizedConstructorPartially/MessagePack.GeneratedMessagePackResolver.g.cs",
    "ins": 9,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/PropertiesGetterSetter/Formatters.MessagePack.GeneratedMessagePackResolver.TempProject.MyMessagePackObjectFormatter.g.cs",
    "ins": 3,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/PropertiesGetterSetter/MessagePack.GeneratedMessagePackResolver.g.cs",
    "ins": 9,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/PropertiesGetterSetterWithDefaultValue/Formatters.MessagePack.GeneratedMessagePackResolver.TempProject.MyMessagePackObjectFormatter.g.cs",
    "ins": 3,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/PropertiesGetterSetterWithDefaultValue/MessagePack.GeneratedMessagePackResolver.g.cs",
    "ins": 9,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/PropertiesGetterSetterWithDefaultValueInputPartially/Formatters.MessagePack.GeneratedMessagePackResolver.TempProject.MyMessagePackObjectFormatter.g.cs",
    "ins": 3,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/PropertiesGetterSetterWithDefaultValueInputPartially/MessagePack.GeneratedMessagePackResolver.g.cs",
    "ins": 9,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/PropertiesGetterSetterWithParameterizedConstructor/Formatters.MessagePack.GeneratedMessagePackResolver.TempProject.MyMessagePackObjectFormatter.g.cs",
    "ins": 3,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/PropertiesGetterSetterWithParameterizedConstructor/MessagePack.GeneratedMessagePackResolver.g.cs",
    "ins": 9,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/PropertiesGetterSetterWithParameterizedConstructorAndDefaultValue/Formatters.MessagePack.GeneratedMessagePackResolver.TempProject.MyMessagePackObjectFormatter.g.cs",
    "ins": 3,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/PropertiesGetterSetterWithParameterizedConstructorAndDefaultValue/MessagePack.GeneratedMessagePackResolver.g.cs",
    "ins": 9,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/PropertiesGetterSetterWithParameterizedConstructorDoNotUseSetter/Formatters.MessagePack.GeneratedMessagePackResolver.TempProject.MyMessagePackObjectFormatter.g.cs",
    "ins": 3,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/PropertiesGetterSetterWithParameterizedConstructorDoNotUseSetter/MessagePack.GeneratedMessagePackResolver.g.cs",
    "ins": 9,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/PropertiesGetterSetterWithParameterizedConstructorPartially/Formatters.MessagePack.GeneratedMessagePackResolver.TempProject.MyMessagePackObjectFormatter.g.cs",
    "ins": 3,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/PropertiesGetterSetterWithParameterizedConstructorPartially/MessagePack.GeneratedMessagePackResolver.g.cs",
    "ins": 9,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/RecordWithPrimaryConstructor/Formatters.MessagePack.GeneratedMessagePackResolver.TempProject.MyMessagePackObjectFormatter.g.cs",
    "ins": 3,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/RecordWithPrimaryConstructor/MessagePack.GeneratedMessagePackResolver.g.cs",
    "ins": 9,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/RecordWithWithInitOnlyProps/Formatters.MessagePack.GeneratedMessagePackResolver.TempProject.MyMessagePackObjectFormatter.g.cs",
    "ins": 3,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/RecordWithWithInitOnlyProps/MessagePack.GeneratedMessagePackResolver.g.cs",
    "ins": 9,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/RecursiveGenerics_Direct/Formatters.MessagePack.GeneratedMessagePackResolver.AFormatter`1.g.cs",
    "ins": 3,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/RecursiveGenerics_Direct/MessagePack.GeneratedMessagePackResolver.g.cs",
    "ins": 9,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/SimplifiedNameForKeywordsAndSyntaxSugar/Formatters.MessagePack.GeneratedMessagePackResolver.SampleObjectFormatter.g.cs",
    "ins": 3,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/SimplifiedNameForKeywordsAndSyntaxSugar/MessagePack.GeneratedMessagePackResolver.g.cs",
    "ins": 9,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/SpecifyFormatterFromStockSet/Formatters.MessagePack.GeneratedMessagePackResolver.GFormatter.g.cs",
    "ins": 3,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/SpecifyFormatterFromStockSet/MessagePack.GeneratedMessagePackResolver.g.cs",
    "ins": 9,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/SystemCollectionsObjectModelCollection/Formatters.MessagePack.GeneratedMessagePackResolver.AFormatter.g.cs",
    "ins": 3,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/SystemCollectionsObjectModelCollection/MessagePack.GeneratedMessagePackResolver.g.cs",
    "ins": 9,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/SystemMemoryTypes/Formatters.MessagePack.GeneratedMessagePackResolver.AFormatter.g.cs",
    "ins": 3,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/SystemMemoryTypes/MessagePack.GeneratedMessagePackResolver.g.cs",
    "ins": 9,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/TwoTypes(False)/Formatters.MessagePack.GeneratedMessagePackResolver.Object1Formatter.g.cs",
    "ins": 3,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/TwoTypes(False)/Formatters.MessagePack.GeneratedMessagePackResolver.Object2Formatter.g.cs",
    "ins": 3,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/TwoTypes(False)/MessagePack.GeneratedMessagePackResolver.g.cs",
    "ins": 9,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/TwoTypes(True)/Formatters.MessagePack.GeneratedMessagePackResolver.Object1Formatter.g.cs",
    "ins": 3,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/TwoTypes(True)/Formatters.MessagePack.GeneratedMessagePackResolver.Object2Formatter.g.cs",
    "ins": 3,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/TwoTypes(True)/MessagePack.GeneratedMessagePackResolver.g.cs",
    "ins": 9,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/UnionFormatter(Namespace)/Formatters.MessagePack.GeneratedMessagePackResolver.MyTestNamespace.Derived1Formatter.g.cs",
    "ins": 3,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/UnionFormatter(Namespace)/Formatters.MessagePack.GeneratedMessagePackResolver.MyTestNamespace.Derived2Formatter.g.cs",
    "ins": 3,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/UnionFormatter(Namespace)/Formatters.MessagePack.GeneratedMessagePackResolver.MyTestNamespace.IMyTypeFormatter.g.cs",
    "ins": 3,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/UnionFormatter(Namespace)/Formatters.MessagePack.GeneratedMessagePackResolver.MyTestNamespace.MyMessagePackObjectFormatter.g.cs",
    "ins": 3,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/UnionFormatter(Namespace)/MessagePack.GeneratedMessagePackResolver.g.cs",
    "ins": 9,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/UnionFormatter(NestingClass)/Formatters.MessagePack.GeneratedMessagePackResolver.ContainingClass.Derived1Formatter.g.cs",
    "ins": 3,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/UnionFormatter(NestingClass)/Formatters.MessagePack.GeneratedMessagePackResolver.ContainingClass.Derived2Formatter.g.cs",
    "ins": 3,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/UnionFormatter(NestingClass)/Formatters.MessagePack.GeneratedMessagePackResolver.ContainingClass.IMyTypeFormatter.g.cs",
    "ins": 3,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/UnionFormatter(NestingClass)/Formatters.MessagePack.GeneratedMessagePackResolver.ContainingClass.MyMessagePackObjectFormatter.g.cs",
    "ins": 3,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/UnionFormatter(NestingClass)/MessagePack.GeneratedMessagePackResolver.g.cs",
    "ins": 9,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/UnionFormatter(None)/Formatters.MessagePack.GeneratedMessagePackResolver.Derived1Formatter.g.cs",
    "ins": 3,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/UnionFormatter(None)/Formatters.MessagePack.GeneratedMessagePackResolver.Derived2Formatter.g.cs",
    "ins": 3,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/UnionFormatter(None)/Formatters.MessagePack.GeneratedMessagePackResolver.IMyTypeFormatter.g.cs",
    "ins": 3,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/UnionFormatter(None)/Formatters.MessagePack.GeneratedMessagePackResolver.MyMessagePackObjectFormatter.g.cs",
    "ins": 3,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/UnionFormatter(None)/MessagePack.GeneratedMessagePackResolver.g.cs",
    "ins": 9,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/WellKnownGenericsFormatter/Formatters.MessagePack.GeneratedMessagePackResolver.TempProject.MyObjectFormatter.g.cs",
    "ins": 3,
    "del": 0,
    "kind": "generated"
   },
   {
    "path": "tests/MessagePack.SourceGenerator.Tests/Resources/WellKnownGenericsFormatter/MessagePack.GeneratedMessagePackResolver.g.cs",
    "ins": 9,
    "del": 0,
    "kind": "generated"
   }
  ]
 },
 "new_tests_in_diff": [
  "CodeCoverageExclusionTests.AllGeneratedTypesAreExcludedFromCodeCoverage",
  "CodeCoverageExclusionTests.ExcludeAttributeIsGuardedForTargetsWhereItIsUnavailable"
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
   "log": "evidence/2297/logs/build.log",
   "duration_s": 5.0
  },
  {
   "id": "tests.targeted",
   "tool": "dotnet test",
   "tool_version": "8.0.402",
   "status": "pass",
   "summary": "2 passed, 0 failed, 0 skipped (2 new tests in run)",
   "tests": [
    {
     "name": "CodeCoverageExclusionTests.AllGeneratedTypesAreExcludedFromCodeCoverage",
     "outcome": "passed",
     "new": true
    },
    {
     "name": "CodeCoverageExclusionTests.ExcludeAttributeIsGuardedForTargetsWhereItIsUnavailable",
     "outcome": "passed",
     "new": true
    }
   ],
   "log": "evidence/2297/logs/tests_targeted.1.log",
   "duration_s": 1.0,
   "filter": [
    "FullyQualifiedName~CodeCoverageExclusionTests."
   ],
   "project": "tests/MessagePack.SourceGenerator.Tests"
  },
  {
   "id": "tests.fail_without_fix",
   "tool": "dotnet test (source reverted, tests kept)",
   "tool_version": "8.0.402",
   "status": "pass",
   "summary": "new tests fail on base source: 2/2 failed -> tests do cover the change",
   "tests": [
    {
     "name": "CodeCoverageExclusionTests.AllGeneratedTypesAreExcludedFromCodeCoverage",
     "outcome": "failed",
     "new": true,
     "error": "Generated file 'MessagePack.SourceGenerator/MessagePack.SourceGenerator.MessagePackGenerator/MessagePack.GeneratedMessagePackResolver.g.cs' is missing [global::System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverage]."
    },
    {
     "name": "CodeCoverageExclusionTests.ExcludeAttributeIsGuardedForTargetsWhereItIsUnavailable",
     "outcome": "failed",
     "new": true,
     "error": "Generated file 'MessagePack.SourceGenerator/MessagePack.SourceGenerator.MessagePackGenerator/MessagePack.GeneratedMessagePackResolver.g.cs' has no [global::System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverage]."
    }
   ],
   "log": "evidence/2297/logs/tests_fail_without_fix.1.log",
   "duration_s": 2.0,
   "reverted_files": [
    "src/MessagePack.SourceGenerator/Transforms/*Template.{tt,cs}",
    "src/MessagePack.SourceGenerator/Transforms/TransformUtilities.cs (13 files)"
   ],
   "full_suite_with_source_reverted": {
    "total": 169,
    "failed": 91,
    "failed_tests": [
     "CodeCoverageExclusionTests.AllGeneratedTypesAreExcludedFromCodeCoverage",
     "CodeCoverageExclusionTests.ExcludeAttributeIsGuardedForTargetsWhereItIsUnavailable",
     "CompositeResolverGeneratorTests.CompositeResolver_MixedResolverTypes",
     "CompositeResolverGeneratorTests.CompositeResolver_Nested",
     "CustomStringKeyFormatterTests.RecordWithPrimaryConstructor",
     "CustomStringKeyFormatterTests.RecordWithWithInitOnlyProps",
     "GenerationTests.AdditionalAllowTypes",
     "GenerationTests.AdditionalFormatterTypes",
     "GenerationTests.AdditionalFormatterTypes_RedundantAttribute",
     "GenerationTests.Array2DJaggedProperty",
     "GenerationTests.ArrayTypedProperty",
     "GenerationTests.CustomFormatterForGenericWithConstraints",
     "GenerationTests.CustomFormatterViaAttributeOnField(usesMapMode: False)",
     "GenerationTests.CustomFormatterViaAttributeOnField(usesMapMode: True)",
     "GenerationTests.CustomFormatterViaAttributeOnProperty(usesMapMode: False)",
     "GenerationTests.CustomFormatterViaAttributeOnProperty(usesMapMode: True)",
     "GenerationTests.CustomFormatterWithSingletonPattern",
     "GenerationTests.DeserializingConstructorParameterMemberTypeAssignability_Incompatible",
     "GenerationTests.DeserializingConstructorParameterMemberTypeAssignability_MemberAssignsToParamType",
     "GenerationTests.EmbeddedTypes",
     "GenerationTests.EnumFormatter(container: Namespace, usesMapMode: False)",
     "GenerationTests.EnumFormatter(container: Namespace, usesMapMode: True)",
     "GenerationTests.EnumFormatter(container: NestingClass, usesMapMode: False)",
     "GenerationTests.EnumFormatter(container: NestingClass, usesMapMode: True)",
     "GenerationTests.EnumFormatter(container: None, usesMapMode: False)",
     "GenerationTests.EnumFormatter(container: None, usesMapMode: True)",
     "GenerationTests.EnumFormatter_CollidingTypeNames",
     "GenerationTests.GenericCustomFormatter",
     "GenerationTests.GenericDataTypeWithPrivateMember",
     "GenerationTests.GenericType",
     "GenerationTests.GenericTypeArg",
     "GenerationTests.GenericType_CollidingTypeNames",
     "GenerationTests.GenericWithConstraintsThatReferenceTypeParameter",
     "GenerationTests.ImplicitFormatterTypes",
     "GenerationTests.InterfaceUnionUsedWithNullableRefAnnotation",
     "GenerationTests.MixType_CollidingTypeNames",
     "GenerationTests.NestedMessagePackObjects",
     "GenerationTests.NestedMessagePackObjects_Array",
     "GenerationTests.NoFieldWithCustomFormatterCollected",
     "GenerationTests.NoPrivateAccessNeeded",
     "GenerationTests.NoPrivateMemberCollected",
     "GenerationTests.NonDefaultDeserializingConstructor_Private",
     "GenerationTests.NonGenericType_CollidingTypeNames",
     "GenerationTests.SimplifiedNameForKeywordsAndSyntaxSugar",
     "GenerationTests.SpecifyFormatterFromStockSet",
     "GenerationTests.SystemCollectionsObjectModelCollection",
     "GenerationTests.SystemMemoryTypes",
     "GenerationTests.UnionFormatter(container: Namespace)",
     "GenerationTests.UnionFormatter(container: NestingClass)",
     "GenerationTests.UnionFormatter(container: None)",
     "GenericsFormatterTests.GenericsOfT1T2Formatter",
     "GenericsFormatterTests.GenericsOfTFormatter",
     "GenericsFormatterTests.GenericsOfTFormatter_FormatterOnly",
     "GenericsFormatterTests.GenericsOfTFormatter_WithKnownTypes",
     "GenericsFormatterTests.GenericsUnionFormatter",
     "GenericsFormatterTests.GenericsUnionFormatter_Nested",
     "GenericsFormatterTests.Generics_Constraints_Multiple",
     "GenericsFormatterTests.Generics_Constraints_NullableReferenceType",
     "GenericsFormatterTests.Generics_Constraints_ReferenceType_Nullable",
     "GenericsFormatterTests.Generics_Constraints_Struct",
     "GenericsFormatterTests.Generics_Constraints_Type",
     "GenericsFormatterTests.Generics_Defined_In_ReferencedProject",
     "GenericsFormatterTests.NestedGenericTypes",
     "GenericsFormatterTests.NullableFormatter",
     "GenericsFormatterTests.RecursiveGenerics_Direct",
     "GenericsFormatterTests.WellKnownGenericsFormatter",
     "ImplicitResolverForCustomFormattersTests.MultipleFunctionalCustomFormattersForType_MultiFormatter",
     "ImplicitResolverForCustomFormattersTests.MultipleFunctionalCustomFormattersForType_OnlyOneNonExcluded",
     "ImplicitResolverForCustomFormattersTests.OpenGenericFormatter",
     "MessagePackFormatterAttributeTests.CanGenerateMessagePackFormatterAttr",
     "MultipleTypesTests.TwoTypes(usesMapMode: False)",
     "MultipleTypesTests.TwoTypes(usesMapMode: True)",
     "PrivateMemberAccessTests.FormatterForClassWithPrivateMembers(type: \"class\", version: CSharp7_3)",
     "PrivateMemberAccessTests.FormatterForClassWithPrivateMembers(type: \"record struct\", version: CSharp10)",
     "PrivateMemberAccessTests.FormatterForClassWithPrivateMembers(type: \"record\", version: CSharp9)",
     "PrivateMemberAccessTests.FormatterForClassWithPrivateMembers(type: \"struct\", version: CSharp7_3)",
     "PrivateMemberAccessTests.FormatterForClassWithPrivateMembers_MapMode",
     "PrivateMemberAccessTests.FormatterForClassWithPrivateMembers_WithNamespace",
     "StringKeyedFormatterTests.PropertiesGetterOnlyDefaultValue",
     "StringKeyedFormatterTests.PropertiesGetterOnlyIgnore",
     "StringKeyedFormatterTests.PropertiesGetterOnlyMixed",
     "StringKeyedFormatterTests.PropertiesGetterOnlyWithParameterizedConstructor",
     "StringKeyedFormatterTests.PropertiesGetterOnlyWithParameterizedConstructorDefaultValue",
     "StringKeyedFormatterTests.PropertiesGetterOnlyWithParameterizedConstructorPartially",
     "StringKeyedFormatterTests.PropertiesGetterSetter",
     "StringKeyedFormatterTests.PropertiesGetterSetterWithDefaultValue",
     "StringKeyedFormatterTests.PropertiesGetterSetterWithDefaultValueInputPartially",
     "StringKeyedFormatterTests.PropertiesGetterSetterWithParameterizedConstructor",
     "StringKeyedFormatterTests.PropertiesGetterSetterWithParameterizedConstructorAndDefaultValue",
     "StringKeyedFormatterTests.PropertiesGetterSetterWithParameterizedConstructorDoNotUseSetter",
     "StringKeyedFormatterTests.PropertiesGetterSetterWithParameterizedConstructorPartially"
    ],
    "log": "evidence/2297/logs/fail_without_fix.full_suite.log"
   },
   "new_failed": 2,
   "new_total": 2
  },
  {
   "id": "tests.full_suite",
   "tool": "dotnet test",
   "tool_version": "8.0.402",
   "status": "pass",
   "summary": "tests/MessagePack.SourceGenerator.Tests: 169 tests, 169 passed, 0 failed (0 not failing on base, 0 also failing on base)",
   "project": "tests/MessagePack.SourceGenerator.Tests",
   "total": 169,
   "passed": 169,
   "failed": 0,
   "failures_not_on_base": [],
   "failures_also_on_base": [],
   "log": "evidence/2297/logs/tests_full_suite.log",
   "duration_s": 4.0
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
  }
 ],
 "not_run": [
  {
   "id": "tests.execution",
   "reason": "SDK 8.0.402 ships Roslyn 4.11 but MessagePack.SourceGenerator references Microsoft.CodeAnalysis 4.12.0, so csc refuses to load the generator (warning CS9057) and projects that consume it as an analyzer (tests/MessagePack.SourceGenerator.ExecutionTests, MapModeExecutionTests) fail to compile (CS0117 'GeneratedMessagePackResolver' does not contain 'Instance'). This also happens on base 32258fdb, so it is an environment/toolchain mismatch, not caused by the change. Needs an SDK with Roslyn >= 4.12 (e.g. .NET SDK 9.0.1xx); swapping in a newer compiler toolset was not permitted in this run."
  },
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
  "os": "linux-x64 (container)",
  "configuration": "Debug",
  "max_cpu": 8
 }
}
```

## Files changed (237: 9 non-generated, 228 generated)
- README.md (+3 -0, doc)
- src/MessagePack.SourceGenerator/Transforms/CompositeResolverTemplate.tt (+6 -0, source)
- src/MessagePack.SourceGenerator/Transforms/EnumTemplate.tt (+3 -0, source)
- src/MessagePack.SourceGenerator/Transforms/FormatterTemplate.tt (+3 -0, source)
- src/MessagePack.SourceGenerator/Transforms/ResolverTemplate.tt (+9 -0, source)
- src/MessagePack.SourceGenerator/Transforms/StringKey/StringKeyFormatterTemplate.tt (+3 -0, source)
- src/MessagePack.SourceGenerator/Transforms/TransformUtilities.cs (+1 -1, source)
- src/MessagePack.SourceGenerator/Transforms/UnionTemplate.tt (+3 -0, source)
- tests/MessagePack.SourceGenerator.Tests/CodeCoverageExclusionTests.cs (+130 -0, test)

Generated files (228; contents and diffs NOT provided):
- src/MessagePack.SourceGenerator/Transforms/CompositeResolverTemplate.cs (+4 -1)
- src/MessagePack.SourceGenerator/Transforms/EnumTemplate.cs (+1 -1)
- src/MessagePack.SourceGenerator/Transforms/FormatterTemplate.cs (+1 -1)
- src/MessagePack.SourceGenerator/Transforms/ResolverTemplate.cs (+5 -2)
- src/MessagePack.SourceGenerator/Transforms/StringKey/StringKeyFormatterTemplate.cs (+1 -1)
- src/MessagePack.SourceGenerator/Transforms/UnionTemplate.cs (+1 -1)
- tests/MessagePack.SourceGenerator.Tests/Resources/AdditionalAllowTypes/Formatters.MessagePack.GeneratedMessagePackResolver.TypeWithAutoGeneratedFormatterFormatter.g.cs (+3 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/AdditionalAllowTypes/MessagePack.GeneratedMessagePackResolver.g.cs (+9 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/AdditionalFormatterTypes/DefiningProject.MessagePack.GeneratedMessagePackResolver.g.cs (+9 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/AdditionalFormatterTypes/TestProject.Formatters.MessagePack.GeneratedMessagePackResolver.TypeWithAutoGeneratedFormatterFormatter.g.cs (+3 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/AdditionalFormatterTypes/TestProject.MessagePack.GeneratedMessagePackResolver.g.cs (+9 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/AdditionalFormatterTypes_RedundantAttribute/Formatters.MessagePack.GeneratedMessagePackResolver.TypeWithAutoGeneratedFormatterFormatter.g.cs (+3 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/AdditionalFormatterTypes_RedundantAttribute/MessagePack.GeneratedMessagePackResolver.g.cs (+9 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/Array2DJaggedProperty/Formatters.MessagePack.GeneratedMessagePackResolver.ContainerObjectFormatter.g.cs (+3 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/Array2DJaggedProperty/MessagePack.GeneratedMessagePackResolver.g.cs (+9 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/ArrayTypedProperty/Formatters.MessagePack.GeneratedMessagePackResolver.ContainerObjectFormatter.g.cs (+3 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/ArrayTypedProperty/Formatters.MessagePack.GeneratedMessagePackResolver.SubObjectFormatter.g.cs (+3 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/ArrayTypedProperty/MessagePack.GeneratedMessagePackResolver.g.cs (+9 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/CanGenerateMessagePackFormatterAttr/Formatters.MessagePack.GeneratedMessagePackResolver.TempProject.BarFormatter.g.cs (+3 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/CanGenerateMessagePackFormatterAttr/MessagePack.GeneratedMessagePackResolver.g.cs (+9 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/CompositeResolver_MixedResolverTypes/MyResolver.g.cs (+6 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/CompositeResolver_Nested/MyResolver.g.cs (+6 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/CustomFormatterForGenericWithConstraints/Formatters.MessagePack.GeneratedMessagePackResolver.SampleObjectFormatter.g.cs (+3 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/CustomFormatterForGenericWithConstraints/MessagePack.GeneratedMessagePackResolver.g.cs (+9 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/CustomFormatterViaAttributeOnField(False)/Formatters.MessagePack.GeneratedMessagePackResolver.HasFieldWithCustomFormatterAttributeFormatter.g.cs (+3 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/CustomFormatterViaAttributeOnField(False)/MessagePack.GeneratedMessagePackResolver.g.cs (+9 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/CustomFormatterViaAttributeOnField(True)/Formatters.MessagePack.GeneratedMessagePackResolver.HasFieldWithCustomFormatterAttributeFormatter.g.cs (+3 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/CustomFormatterViaAttributeOnField(True)/MessagePack.GeneratedMessagePackResolver.g.cs (+9 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/CustomFormatterViaAttributeOnProperty(False)/Formatters.MessagePack.GeneratedMessagePackResolver.HasPropertyWithCustomFormatterAttributeFormatter.g.cs (+3 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/CustomFormatterViaAttributeOnProperty(False)/MessagePack.GeneratedMessagePackResolver.g.cs (+9 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/CustomFormatterViaAttributeOnProperty(True)/Formatters.MessagePack.GeneratedMessagePackResolver.HasPropertyWithCustomFormatterAttributeFormatter.g.cs (+3 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/CustomFormatterViaAttributeOnProperty(True)/MessagePack.GeneratedMessagePackResolver.g.cs (+9 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/CustomFormatterWithSingletonPattern/Formatters.MessagePack.GeneratedMessagePackResolver.GFormatter.g.cs (+3 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/CustomFormatterWithSingletonPattern/MessagePack.GeneratedMessagePackResolver.g.cs (+9 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/DeserializingConstructorParameterMemberTypeAssignability_Incompatible/MessagePack.GeneratedMessagePackResolver.g.cs (+9 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/DeserializingConstructorParameterMemberTypeAssignability_MemberAssignsToParamType/Formatters.MessagePack.GeneratedMessagePackResolver.AFormatter.g.cs (+3 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/DeserializingConstructorParameterMemberTypeAssignability_MemberAssignsToParamType/MessagePack.GeneratedMessagePackResolver.g.cs (+9 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/EmbeddedTypes/Formatters.MessagePack.GeneratedMessagePackResolver.AFormatter.g.cs (+3 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/EmbeddedTypes/MessagePack.GeneratedMessagePackResolver.g.cs (+9 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/EnumFormatter(Namespace, False)/Formatters.MessagePack.GeneratedMessagePackResolver.MyTestNamespace.MyEnumFormatter.g.cs (+3 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/EnumFormatter(Namespace, False)/Formatters.MessagePack.GeneratedMessagePackResolver.MyTestNamespace.MyMessagePackObjectFormatter.g.cs (+3 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/EnumFormatter(Namespace, False)/MessagePack.GeneratedMessagePackResolver.g.cs (+9 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/EnumFormatter(Namespace, True)/Formatters.MessagePack.GeneratedMessagePackResolver.MyTestNamespace.MyEnumFormatter.g.cs (+3 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/EnumFormatter(Namespace, True)/Formatters.MessagePack.GeneratedMessagePackResolver.MyTestNamespace.MyMessagePackObjectFormatter.g.cs (+3 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/EnumFormatter(Namespace, True)/MessagePack.GeneratedMessagePackResolver.g.cs (+9 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/EnumFormatter(NestingClass, False)/Formatters.MessagePack.GeneratedMessagePackResolver.ContainingClass.MyEnumFormatter.g.cs (+3 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/EnumFormatter(NestingClass, False)/Formatters.MessagePack.GeneratedMessagePackResolver.ContainingClass.MyMessagePackObjectFormatter.g.cs (+3 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/EnumFormatter(NestingClass, False)/MessagePack.GeneratedMessagePackResolver.g.cs (+9 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/EnumFormatter(NestingClass, True)/Formatters.MessagePack.GeneratedMessagePackResolver.ContainingClass.MyEnumFormatter.g.cs (+3 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/EnumFormatter(NestingClass, True)/Formatters.MessagePack.GeneratedMessagePackResolver.ContainingClass.MyMessagePackObjectFormatter.g.cs (+3 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/EnumFormatter(NestingClass, True)/MessagePack.GeneratedMessagePackResolver.g.cs (+9 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/EnumFormatter(None, False)/Formatters.MessagePack.GeneratedMessagePackResolver.MyEnumFormatter.g.cs (+3 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/EnumFormatter(None, False)/Formatters.MessagePack.GeneratedMessagePackResolver.MyMessagePackObjectFormatter.g.cs (+3 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/EnumFormatter(None, False)/MessagePack.GeneratedMessagePackResolver.g.cs (+9 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/EnumFormatter(None, True)/Formatters.MessagePack.GeneratedMessagePackResolver.MyEnumFormatter.g.cs (+3 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/EnumFormatter(None, True)/Formatters.MessagePack.GeneratedMessagePackResolver.MyMessagePackObjectFormatter.g.cs (+3 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/EnumFormatter(None, True)/MessagePack.GeneratedMessagePackResolver.g.cs (+9 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/EnumFormatter_CollidingTypeNames/Formatters.MessagePack.GeneratedMessagePackResolver.MyMessagePackObjectFormatter.g.cs (+3 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/EnumFormatter_CollidingTypeNames/Formatters.MessagePack.GeneratedMessagePackResolver.NS1.MyEnumFormatter.g.cs (+3 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/EnumFormatter_CollidingTypeNames/Formatters.MessagePack.GeneratedMessagePackResolver.NS2.MyEnumFormatter.g.cs (+3 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/EnumFormatter_CollidingTypeNames/MessagePack.GeneratedMessagePackResolver.g.cs (+9 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/FormatterForClassWithPrivateMembers(class)/Formatters.MyObject.MyObjectFormatter.g.cs (+3 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/FormatterForClassWithPrivateMembers(class)/MessagePack.GeneratedMessagePackResolver.g.cs (+9 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/FormatterForClassWithPrivateMembers(record struct)/Formatters.MyObject.MyObjectFormatter.g.cs (+3 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/FormatterForClassWithPrivateMembers(record struct)/MessagePack.GeneratedMessagePackResolver.g.cs (+9 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/FormatterForClassWithPrivateMembers(record)/Formatters.MyObject.MyObjectFormatter.g.cs (+3 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/FormatterForClassWithPrivateMembers(record)/MessagePack.GeneratedMessagePackResolver.g.cs (+9 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/FormatterForClassWithPrivateMembers(struct)/Formatters.MyObject.MyObjectFormatter.g.cs (+3 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/FormatterForClassWithPrivateMembers(struct)/MessagePack.GeneratedMessagePackResolver.g.cs (+9 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/FormatterForClassWithPrivateMembers_MapMode/Formatters.MyObject.MyObjectFormatter.g.cs (+3 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/FormatterForClassWithPrivateMembers_MapMode/MessagePack.GeneratedMessagePackResolver.g.cs (+9 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/FormatterForClassWithPrivateMembers_WithNamespace/Formatters.A.MyObject.MyObjectFormatter.g.cs (+3 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/FormatterForClassWithPrivateMembers_WithNamespace/MessagePack.GeneratedMessagePackResolver.g.cs (+9 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/GenericCustomFormatter/Formatters.SampleObject.SampleObjectFormatter.g.cs (+3 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/GenericCustomFormatter/MessagePack.GeneratedMessagePackResolver.g.cs (+9 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/GenericDataTypeWithPrivateMember/Formatters.HasPrivateSerializedMemberAndIsGenericNamed`1.HasPrivateSerializedMemberAndIsGenericNamedFormatter.g.cs (+5 -1)
- tests/MessagePack.SourceGenerator.Tests/Resources/GenericDataTypeWithPrivateMember/Formatters.HasPrivateSerializedMemberAndIsGenericOrdinal`1.HasPrivateSerializedMemberAndIsGenericOrdinalFormatter.g.cs (+4 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/GenericDataTypeWithPrivateMember/MessagePack.GeneratedMessagePackResolver.g.cs (+9 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/GenericType/Formatters.MessagePack.GeneratedMessagePackResolver.ContainerObjectFormatter.g.cs (+3 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/GenericType/Formatters.MessagePack.GeneratedMessagePackResolver.MyGenericTypeFormatter`1.g.cs (+3 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/GenericType/MessagePack.GeneratedMessagePackResolver.g.cs (+9 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/GenericTypeArg/Formatters.MessagePack.GeneratedMessagePackResolver.GenericClassFormatter`2.g.cs (+3 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/GenericTypeArg/MessagePack.GeneratedMessagePackResolver.g.cs (+9 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/GenericType_CollidingTypeNames/Formatters.MessagePack.GeneratedMessagePackResolver.MyMessagePackObjectFormatter.g.cs (+3 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/GenericType_CollidingTypeNames/Formatters.MessagePack.GeneratedMessagePackResolver.NS1.MyTypeFormatter`1.g.cs (+3 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/GenericType_CollidingTypeNames/Formatters.MessagePack.GeneratedMessagePackResolver.NS2.MyTypeFormatter`1.g.cs (+3 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/GenericType_CollidingTypeNames/MessagePack.GeneratedMessagePackResolver.g.cs (+9 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/GenericWithConstraintsThatReferenceTypeParameter/Formatters.MessagePack.GeneratedMessagePackResolver.GenericConstrainedClassIntKeyFormatter`2.g.cs (+3 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/GenericWithConstraintsThatReferenceTypeParameter/MessagePack.GeneratedMessagePackResolver.g.cs (+9 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/GenericsOfT1T2Formatter/Formatters.MessagePack.GeneratedMessagePackResolver.TempProject.MyGenericObjectFormatter`2.g.cs (+3 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/GenericsOfT1T2Formatter/Formatters.MessagePack.GeneratedMessagePackResolver.TempProject.MyObjectFormatter.g.cs (+3 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/GenericsOfT1T2Formatter/Formatters.MessagePack.GeneratedMessagePackResolver.TempProject.MyObjectNestedFormatter.g.cs (+3 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/GenericsOfT1T2Formatter/MessagePack.GeneratedMessagePackResolver.g.cs (+9 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/GenericsOfTFormatter/Formatters.MessagePack.GeneratedMessagePackResolver.TempProject.MyGenericObjectFormatter`1.g.cs (+3 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/GenericsOfTFormatter/Formatters.MessagePack.GeneratedMessagePackResolver.TempProject.MyObjectFormatter.g.cs (+3 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/GenericsOfTFormatter/Formatters.MessagePack.GeneratedMessagePackResolver.TempProject.MyObjectNestedFormatter.g.cs (+3 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/GenericsOfTFormatter/MessagePack.GeneratedMessagePackResolver.g.cs (+9 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/GenericsOfTFormatter_FormatterOnly/Formatters.MessagePack.GeneratedMessagePackResolver.TempProject.MyGenericObjectFormatter`1.g.cs (+3 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/GenericsOfTFormatter_FormatterOnly/MessagePack.GeneratedMessagePackResolver.g.cs (+9 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/GenericsOfTFormatter_WithKnownTypes/Formatters.MessagePack.GeneratedMessagePackResolver.TempProject.MyGenericObjectFormatter`1.g.cs (+3 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/GenericsOfTFormatter_WithKnownTypes/Formatters.MessagePack.GeneratedMessagePackResolver.TempProject.MyObject2Formatter.g.cs (+3 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/GenericsOfTFormatter_WithKnownTypes/Formatters.MessagePack.GeneratedMessagePackResolver.TempProject.MyObjectFormatter.g.cs (+3 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/GenericsOfTFormatter_WithKnownTypes/MessagePack.GeneratedMessagePackResolver.g.cs (+9 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/GenericsUnionFormatter/Formatters.MessagePack.GeneratedMessagePackResolver.TempProject.WrapperFormatter`1.g.cs (+3 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/GenericsUnionFormatter/MessagePack.GeneratedMessagePackResolver.g.cs (+9 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/GenericsUnionFormatter_Nested/Formatters.MessagePack.GeneratedMessagePackResolver.TempProject.MyGenericObjectFormatter`1.g.cs (+3 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/GenericsUnionFormatter_Nested/Formatters.MessagePack.GeneratedMessagePackResolver.TempProject.MyInnerGenericObjectFormatter`1.g.cs (+3 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/GenericsUnionFormatter_Nested/Formatters.MessagePack.GeneratedMessagePackResolver.TempProject.WrapperFormatter`1.g.cs (+3 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/GenericsUnionFormatter_Nested/MessagePack.GeneratedMessagePackResolver.g.cs (+9 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/Generics_Constraints_Multiple/Formatters.MessagePack.GeneratedMessagePackResolver.TempProject.MyGenericObjectFormatter`4.g.cs (+3 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/Generics_Constraints_Multiple/MessagePack.GeneratedMessagePackResolver.g.cs (+9 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/Generics_Constraints_NullableReferenceType/Formatters.MessagePack.GeneratedMessagePackResolver.TempProject.MyGenericObjectFormatter`4.g.cs (+3 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/Generics_Constraints_NullableReferenceType/MessagePack.GeneratedMessagePackResolver.g.cs (+9 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/Generics_Constraints_ReferenceType_Nullable/Formatters.MessagePack.GeneratedMessagePackResolver.TempProject.MyGenericObjectFormatter`2.g.cs (+3 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/Generics_Constraints_ReferenceType_Nullable/MessagePack.GeneratedMessagePackResolver.g.cs (+9 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/Generics_Constraints_Struct/Formatters.MessagePack.GeneratedMessagePackResolver.TempProject.MyGenericObjectFormatter`1.g.cs (+3 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/Generics_Constraints_Struct/MessagePack.GeneratedMessagePackResolver.g.cs (+9 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/Generics_Constraints_Type/Formatters.MessagePack.GeneratedMessagePackResolver.TempProject.MyGenericObjectFormatter`1.g.cs (+3 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/Generics_Constraints_Type/MessagePack.GeneratedMessagePackResolver.g.cs (+9 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/Generics_Defined_In_ReferencedProject/DefiningProject.Formatters.TempProject.MyResolver.TempProject.MyGenericObjectFormatter`1.g.cs (+3 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/Generics_Defined_In_ReferencedProject/DefiningProject.TempProject.MyResolver.g.cs (+9 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/Generics_Defined_In_ReferencedProject/TestProject.Formatters.MessagePack.GeneratedMessagePackResolver.TempProject.MyGenericObjectFormatter`1.g.cs (+3 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/Generics_Defined_In_ReferencedProject/TestProject.Formatters.MessagePack.GeneratedMessagePackResolver.TempProject.MyObjectFormatter.g.cs (+3 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/Generics_Defined_In_ReferencedProject/TestProject.Formatters.MessagePack.GeneratedMessagePackResolver.TempProject.MyObjectNestedFormatter.g.cs (+3 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/Generics_Defined_In_ReferencedProject/TestProject.MessagePack.GeneratedMessagePackResolver.g.cs (+9 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/ImplicitFormatterTypes/Formatters.MessagePack.GeneratedMessagePackResolver.TypeWithAutoGeneratedFormatterFormatter.g.cs (+3 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/ImplicitFormatterTypes/MessagePack.GeneratedMessagePackResolver.g.cs (+9 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/InterfaceUnionUsedWithNullableRefAnnotation/Formatters.MessagePack.GeneratedMessagePackResolver.IMyTypeFormatter.g.cs (+3 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/InterfaceUnionUsedWithNullableRefAnnotation/Formatters.MessagePack.GeneratedMessagePackResolver.UnionContainerFormatter.g.cs (+3 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/InterfaceUnionUsedWithNullableRefAnnotation/MessagePack.GeneratedMessagePackResolver.g.cs (+9 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/MixType_CollidingTypeNames/Formatters.MessagePack.GeneratedMessagePackResolver.MyMessagePackObjectFormatter.g.cs (+3 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/MixType_CollidingTypeNames/Formatters.MessagePack.GeneratedMessagePackResolver.NS1.MyTypeFormatter.g.cs (+3 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/MixType_CollidingTypeNames/Formatters.MessagePack.GeneratedMessagePackResolver.NS2.MyTypeFormatter.g.cs (+3 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/MixType_CollidingTypeNames/Formatters.MessagePack.GeneratedMessagePackResolver.NS3.MyTypeFormatter`1.g.cs (+3 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/MixType_CollidingTypeNames/MessagePack.GeneratedMessagePackResolver.g.cs (+9 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/MultipleFunctionalCustomFormattersForType_MultiFormatter/MessagePack.GeneratedMessagePackResolver.g.cs (+9 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/MultipleFunctionalCustomFormattersForType_OnlyOneNonExcluded/MessagePack.GeneratedMessagePackResolver.g.cs (+9 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/NestedGenericTypes/Formatters.MessagePack.GeneratedMessagePackResolver.TempProject.MyGenericObjectFormatter`1.g.cs (+3 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/NestedGenericTypes/Formatters.MessagePack.GeneratedMessagePackResolver.TempProject.MyInnerGenericObjectFormatter`1.g.cs (+3 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/NestedGenericTypes/Formatters.MessagePack.GeneratedMessagePackResolver.TempProject.MyObject2Formatter.g.cs (+3 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/NestedGenericTypes/Formatters.MessagePack.GeneratedMessagePackResolver.TempProject.MyObjectFormatter.g.cs (+3 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/NestedGenericTypes/Formatters.MessagePack.GeneratedMessagePackResolver.TempProject.WrapperFormatter`1.g.cs (+3 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/NestedGenericTypes/MessagePack.GeneratedMessagePackResolver.g.cs (+9 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/NestedMessagePackObjects/Formatters.MessagePack.GeneratedMessagePackResolver.A.B.CFormatter.g.cs (+3 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/NestedMessagePackObjects/Formatters.MessagePack.GeneratedMessagePackResolver.A.BFormatter.g.cs (+3 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/NestedMessagePackObjects/MessagePack.GeneratedMessagePackResolver.g.cs (+9 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/NestedMessagePackObjects_Array/Formatters.MessagePack.GeneratedMessagePackResolver.A.B.CFormatter.g.cs (+3 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/NestedMessagePackObjects_Array/Formatters.MessagePack.GeneratedMessagePackResolver.A.BFormatter.g.cs (+3 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/NestedMessagePackObjects_Array/MessagePack.GeneratedMessagePackResolver.g.cs (+9 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/NoFieldWithCustomFormatterCollected/Formatters.MessagePack.GeneratedMessagePackResolver.TestFormatter.g.cs (+3 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/NoFieldWithCustomFormatterCollected/MessagePack.GeneratedMessagePackResolver.g.cs (+9 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/NoPrivateAccessNeeded/Formatters.MessagePack.GeneratedMessagePackResolver.Test3Formatter.g.cs (+3 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/NoPrivateAccessNeeded/MessagePack.GeneratedMessagePackResolver.g.cs (+9 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/NoPrivateMemberCollected/Formatters.MessagePack.GeneratedMessagePackResolver.TestFormatter.g.cs (+3 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/NoPrivateMemberCollected/MessagePack.GeneratedMessagePackResolver.g.cs (+9 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/NonDefaultDeserializingConstructor_Private/Formatters.A.AFormatter.g.cs (+3 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/NonDefaultDeserializingConstructor_Private/MessagePack.GeneratedMessagePackResolver.g.cs (+9 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/NonGenericType_CollidingTypeNames/Formatters.MessagePack.GeneratedMessagePackResolver.MyMessagePackObjectFormatter.g.cs (+3 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/NonGenericType_CollidingTypeNames/Formatters.MessagePack.GeneratedMessagePackResolver.NS1.MyTypeFormatter.g.cs (+3 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/NonGenericType_CollidingTypeNames/Formatters.MessagePack.GeneratedMessagePackResolver.NS2.MyTypeFormatter.g.cs (+3 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/NonGenericType_CollidingTypeNames/MessagePack.GeneratedMessagePackResolver.g.cs (+9 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/NullableFormatter/Formatters.MessagePack.GeneratedMessagePackResolver.TempProject.MyEnumFormatter.g.cs (+3 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/NullableFormatter/Formatters.MessagePack.GeneratedMessagePackResolver.TempProject.MyObjectFormatter.g.cs (+3 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/NullableFormatter/MessagePack.GeneratedMessagePackResolver.g.cs (+9 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/OpenGenericFormatter/MessagePack.GeneratedMessagePackResolver.g.cs (+9 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/PropertiesGetterOnlyDefaultValue/Formatters.MessagePack.GeneratedMessagePackResolver.TempProject.MyMessagePackObjectFormatter.g.cs (+3 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/PropertiesGetterOnlyDefaultValue/MessagePack.GeneratedMessagePackResolver.g.cs (+9 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/PropertiesGetterOnlyIgnore/Formatters.MessagePack.GeneratedMessagePackResolver.TempProject.MyMessagePackObjectFormatter.g.cs (+3 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/PropertiesGetterOnlyIgnore/MessagePack.GeneratedMessagePackResolver.g.cs (+9 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/PropertiesGetterOnlyMixed/Formatters.MessagePack.GeneratedMessagePackResolver.TempProject.MyMessagePackObjectFormatter.g.cs (+3 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/PropertiesGetterOnlyMixed/MessagePack.GeneratedMessagePackResolver.g.cs (+9 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/PropertiesGetterOnlyWithParameterizedConstructor/Formatters.MessagePack.GeneratedMessagePackResolver.TempProject.MyMessagePackObjectFormatter.g.cs (+3 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/PropertiesGetterOnlyWithParameterizedConstructor/MessagePack.GeneratedMessagePackResolver.g.cs (+9 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/PropertiesGetterOnlyWithParameterizedConstructorDefaultValue/Formatters.MessagePack.GeneratedMessagePackResolver.TempProject.MyMessagePackObjectFormatter.g.cs (+3 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/PropertiesGetterOnlyWithParameterizedConstructorDefaultValue/MessagePack.GeneratedMessagePackResolver.g.cs (+9 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/PropertiesGetterOnlyWithParameterizedConstructorPartially/Formatters.MessagePack.GeneratedMessagePackResolver.TempProject.MyMessagePackObjectFormatter.g.cs (+3 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/PropertiesGetterOnlyWithParameterizedConstructorPartially/MessagePack.GeneratedMessagePackResolver.g.cs (+9 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/PropertiesGetterSetter/Formatters.MessagePack.GeneratedMessagePackResolver.TempProject.MyMessagePackObjectFormatter.g.cs (+3 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/PropertiesGetterSetter/MessagePack.GeneratedMessagePackResolver.g.cs (+9 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/PropertiesGetterSetterWithDefaultValue/Formatters.MessagePack.GeneratedMessagePackResolver.TempProject.MyMessagePackObjectFormatter.g.cs (+3 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/PropertiesGetterSetterWithDefaultValue/MessagePack.GeneratedMessagePackResolver.g.cs (+9 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/PropertiesGetterSetterWithDefaultValueInputPartially/Formatters.MessagePack.GeneratedMessagePackResolver.TempProject.MyMessagePackObjectFormatter.g.cs (+3 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/PropertiesGetterSetterWithDefaultValueInputPartially/MessagePack.GeneratedMessagePackResolver.g.cs (+9 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/PropertiesGetterSetterWithParameterizedConstructor/Formatters.MessagePack.GeneratedMessagePackResolver.TempProject.MyMessagePackObjectFormatter.g.cs (+3 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/PropertiesGetterSetterWithParameterizedConstructor/MessagePack.GeneratedMessagePackResolver.g.cs (+9 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/PropertiesGetterSetterWithParameterizedConstructorAndDefaultValue/Formatters.MessagePack.GeneratedMessagePackResolver.TempProject.MyMessagePackObjectFormatter.g.cs (+3 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/PropertiesGetterSetterWithParameterizedConstructorAndDefaultValue/MessagePack.GeneratedMessagePackResolver.g.cs (+9 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/PropertiesGetterSetterWithParameterizedConstructorDoNotUseSetter/Formatters.MessagePack.GeneratedMessagePackResolver.TempProject.MyMessagePackObjectFormatter.g.cs (+3 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/PropertiesGetterSetterWithParameterizedConstructorDoNotUseSetter/MessagePack.GeneratedMessagePackResolver.g.cs (+9 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/PropertiesGetterSetterWithParameterizedConstructorPartially/Formatters.MessagePack.GeneratedMessagePackResolver.TempProject.MyMessagePackObjectFormatter.g.cs (+3 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/PropertiesGetterSetterWithParameterizedConstructorPartially/MessagePack.GeneratedMessagePackResolver.g.cs (+9 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/RecordWithPrimaryConstructor/Formatters.MessagePack.GeneratedMessagePackResolver.TempProject.MyMessagePackObjectFormatter.g.cs (+3 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/RecordWithPrimaryConstructor/MessagePack.GeneratedMessagePackResolver.g.cs (+9 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/RecordWithWithInitOnlyProps/Formatters.MessagePack.GeneratedMessagePackResolver.TempProject.MyMessagePackObjectFormatter.g.cs (+3 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/RecordWithWithInitOnlyProps/MessagePack.GeneratedMessagePackResolver.g.cs (+9 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/RecursiveGenerics_Direct/Formatters.MessagePack.GeneratedMessagePackResolver.AFormatter`1.g.cs (+3 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/RecursiveGenerics_Direct/MessagePack.GeneratedMessagePackResolver.g.cs (+9 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/SimplifiedNameForKeywordsAndSyntaxSugar/Formatters.MessagePack.GeneratedMessagePackResolver.SampleObjectFormatter.g.cs (+3 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/SimplifiedNameForKeywordsAndSyntaxSugar/MessagePack.GeneratedMessagePackResolver.g.cs (+9 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/SpecifyFormatterFromStockSet/Formatters.MessagePack.GeneratedMessagePackResolver.GFormatter.g.cs (+3 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/SpecifyFormatterFromStockSet/MessagePack.GeneratedMessagePackResolver.g.cs (+9 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/SystemCollectionsObjectModelCollection/Formatters.MessagePack.GeneratedMessagePackResolver.AFormatter.g.cs (+3 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/SystemCollectionsObjectModelCollection/MessagePack.GeneratedMessagePackResolver.g.cs (+9 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/SystemMemoryTypes/Formatters.MessagePack.GeneratedMessagePackResolver.AFormatter.g.cs (+3 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/SystemMemoryTypes/MessagePack.GeneratedMessagePackResolver.g.cs (+9 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/TwoTypes(False)/Formatters.MessagePack.GeneratedMessagePackResolver.Object1Formatter.g.cs (+3 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/TwoTypes(False)/Formatters.MessagePack.GeneratedMessagePackResolver.Object2Formatter.g.cs (+3 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/TwoTypes(False)/MessagePack.GeneratedMessagePackResolver.g.cs (+9 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/TwoTypes(True)/Formatters.MessagePack.GeneratedMessagePackResolver.Object1Formatter.g.cs (+3 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/TwoTypes(True)/Formatters.MessagePack.GeneratedMessagePackResolver.Object2Formatter.g.cs (+3 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/TwoTypes(True)/MessagePack.GeneratedMessagePackResolver.g.cs (+9 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/UnionFormatter(Namespace)/Formatters.MessagePack.GeneratedMessagePackResolver.MyTestNamespace.Derived1Formatter.g.cs (+3 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/UnionFormatter(Namespace)/Formatters.MessagePack.GeneratedMessagePackResolver.MyTestNamespace.Derived2Formatter.g.cs (+3 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/UnionFormatter(Namespace)/Formatters.MessagePack.GeneratedMessagePackResolver.MyTestNamespace.IMyTypeFormatter.g.cs (+3 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/UnionFormatter(Namespace)/Formatters.MessagePack.GeneratedMessagePackResolver.MyTestNamespace.MyMessagePackObjectFormatter.g.cs (+3 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/UnionFormatter(Namespace)/MessagePack.GeneratedMessagePackResolver.g.cs (+9 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/UnionFormatter(NestingClass)/Formatters.MessagePack.GeneratedMessagePackResolver.ContainingClass.Derived1Formatter.g.cs (+3 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/UnionFormatter(NestingClass)/Formatters.MessagePack.GeneratedMessagePackResolver.ContainingClass.Derived2Formatter.g.cs (+3 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/UnionFormatter(NestingClass)/Formatters.MessagePack.GeneratedMessagePackResolver.ContainingClass.IMyTypeFormatter.g.cs (+3 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/UnionFormatter(NestingClass)/Formatters.MessagePack.GeneratedMessagePackResolver.ContainingClass.MyMessagePackObjectFormatter.g.cs (+3 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/UnionFormatter(NestingClass)/MessagePack.GeneratedMessagePackResolver.g.cs (+9 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/UnionFormatter(None)/Formatters.MessagePack.GeneratedMessagePackResolver.Derived1Formatter.g.cs (+3 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/UnionFormatter(None)/Formatters.MessagePack.GeneratedMessagePackResolver.Derived2Formatter.g.cs (+3 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/UnionFormatter(None)/Formatters.MessagePack.GeneratedMessagePackResolver.IMyTypeFormatter.g.cs (+3 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/UnionFormatter(None)/Formatters.MessagePack.GeneratedMessagePackResolver.MyMessagePackObjectFormatter.g.cs (+3 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/UnionFormatter(None)/MessagePack.GeneratedMessagePackResolver.g.cs (+9 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/WellKnownGenericsFormatter/Formatters.MessagePack.GeneratedMessagePackResolver.TempProject.MyObjectFormatter.g.cs (+3 -0)
- tests/MessagePack.SourceGenerator.Tests/Resources/WellKnownGenericsFormatter/MessagePack.GeneratedMessagePackResolver.g.cs (+9 -0)

## Diff (non-generated files)
```diff
diff --git a/README.md b/README.md
index c52f1088..b09bde25 100644
--- a/README.md
+++ b/README.md
@@ -1636,6 +1636,9 @@ Two assembly-level attributes exist to help with mixing in your own custom forma
 
 Learn more about using a mix of your own custom formatters and automatically generated ones in [the Analyzer section](#analyzer).
 
+All generated formatters and resolvers are decorated with `[ExcludeFromCodeCoverage]`, so generated code does not skew code coverage reports.
+The attribute is only emitted for targets where it is available (not `netstandard2.0` or .NET Framework).
+
 ### MagicOnion
 
 [MagicOnion](https://github.com/Cysharp/MagicOnion) is a code-first gRPC framework based on grpc-dotnet and MessagePack. gRPC usually communicates with Protocol Buffers using IDL. But MagicOnion uses MessagePack for C# and does not need IDL. When communicating C# to C#, schemaless (or rather C# classes as schema) is better than using IDL.

diff --git a/src/MessagePack.SourceGenerator/Transforms/CompositeResolverTemplate.tt b/src/MessagePack.SourceGenerator/Transforms/CompositeResolverTemplate.tt
index 6e44be11..6242707c 100644
--- a/src/MessagePack.SourceGenerator/Transforms/CompositeResolverTemplate.tt
+++ b/src/MessagePack.SourceGenerator/Transforms/CompositeResolverTemplate.tt
@@ -4,6 +4,9 @@ using MsgPack = global::MessagePack;
 
 <# using (TransformUtilities.EmitNestingTypesAndNamespaces(this.ResolverName, this.Write)) { #>
 
+#if !NETSTANDARD2_0 && !NETFRAMEWORK
+[global::System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverage]
+#endif
 partial class <#= ResolverName.Name #> : MsgPack::IFormatterResolver
 {
 	public static readonly <#= ResolverName.Name #> Instance = new <#= ResolverName.Name #>();
@@ -29,6 +32,9 @@ partial class <#= ResolverName.Name #> : MsgPack::IFormatterResolver
 		return FormatterCache<T>.Formatter;
 	}
 
+#if !NETSTANDARD2_0 && !NETFRAMEWORK
+	[global::System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverage]
+#endif
 	static class FormatterCache<T>
 	{
 		internal static readonly MsgPack::Formatters.IMessagePackFormatter<T> Formatter;

diff --git a/src/MessagePack.SourceGenerator/Transforms/EnumTemplate.tt b/src/MessagePack.SourceGenerator/Transforms/EnumTemplate.tt
index 11ebf077..7cc5835a 100644
--- a/src/MessagePack.SourceGenerator/Transforms/EnumTemplate.tt
+++ b/src/MessagePack.SourceGenerator/Transforms/EnumTemplate.tt
@@ -5,6 +5,9 @@ using MsgPack = global::MessagePack;
 
 <# using (this.EmitNestingTypesAndNamespaces(this.Write)) { #>
 
+#if !NETSTANDARD2_0 && !NETFRAMEWORK
+	[global::System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverage]
+#endif
 	internal sealed class <#= Info.Formatter.Name #> : MsgPack::Formatters.IMessagePackFormatter<<#= Info.DataType.GetQualifiedName() #>>
 	{
 		public void Serialize(ref MsgPack::MessagePackWriter writer, <#= Info.DataType.GetQualifiedName() #> value, MsgPack::MessagePackSerializerOptions options)

diff --git a/src/MessagePack.SourceGenerator/Transforms/FormatterTemplate.tt b/src/MessagePack.SourceGenerator/Transforms/FormatterTemplate.tt
index 2bd9a8a6..d09094bb 100644
--- a/src/MessagePack.SourceGenerator/Transforms/FormatterTemplate.tt
+++ b/src/MessagePack.SourceGenerator/Transforms/FormatterTemplate.tt
@@ -11,6 +11,9 @@ using MsgPack = global::MessagePack;
 <# using (this.EmitNestingTypesAndNamespaces(this.Write)) { #>
 
 <#  bool isFormatterResolverNecessary = GeneratorUtilities.ShouldUseFormatterResolver(Info.Members);#>
+#if !NETSTANDARD2_0 && !NETFRAMEWORK
+	[global::System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverage]
+#endif
 	internal sealed class <#= Info.Formatter.GetQualifiedName(Qualifiers.None) #> : MsgPack::Formatters.IMessagePackFormatter<<#= Info.DataType.GetQualifiedName(genericStyle: GenericParameterStyle.Identifiers) #>>
 <# TransformUtilities.EmitTypeConstraints(Info.Formatter, this.Write); #>
 	{

diff --git a/src/MessagePack.SourceGenerator/Transforms/ResolverTemplate.tt b/src/MessagePack.SourceGenerator/Transforms/ResolverTemplate.tt
index 4a816aa9..792c4b24 100644
--- a/src/MessagePack.SourceGenerator/Transforms/ResolverTemplate.tt
+++ b/src/MessagePack.SourceGenerator/Transforms/ResolverTemplate.tt
@@ -11,6 +11,9 @@ using MsgPack = global::MessagePack;
 <# using (TransformUtilities.EmitNestingTypesAndNamespaces(this.ResolverName, this.Write)) { #>
 
 /// <summary>A MessagePack resolver that uses generated formatters for types in this assembly.</summary>
+#if !NETSTANDARD2_0 && !NETFRAMEWORK
+[global::System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverage]
+#endif
 partial class <#= ResolverName.Name #> : MsgPack::IFormatterResolver
 {
 	/// <summary>An instance of this resolver that only returns formatters specifically generated for types in this assembly.</summary>
@@ -25,6 +28,9 @@ partial class <#= ResolverName.Name #> : MsgPack::IFormatterResolver
 		return FormatterCache<T>.Formatter;
 	}
 
+#if !NETSTANDARD2_0 && !NETFRAMEWORK
+	[global::System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverage]
+#endif
 	private static class FormatterCache<T>
 	{
 		internal static readonly MsgPack::Formatters.IMessagePackFormatter<T> Formatter;
@@ -39,6 +45,9 @@ partial class <#= ResolverName.Name #> : MsgPack::IFormatterResolver
 		}
 	}
 
+#if !NETSTANDARD2_0 && !NETFRAMEWORK
+	[global::System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverage]
+#endif
 	private static class <#= ResolverName.Name #>GetFormatterHelper
 	{
 <#

diff --git a/src/MessagePack.SourceGenerator/Transforms/StringKey/StringKeyFormatterTemplate.tt b/src/MessagePack.SourceGenerator/Transforms/StringKey/StringKeyFormatterTemplate.tt
index c81a3c37..db3f36f3 100644
--- a/src/MessagePack.SourceGenerator/Transforms/StringKey/StringKeyFormatterTemplate.tt
+++ b/src/MessagePack.SourceGenerator/Transforms/StringKey/StringKeyFormatterTemplate.tt
@@ -15,6 +15,9 @@ using MsgPack = global::MessagePack;
 
 	bool isFormatterResolverNecessary = GeneratorUtilities.ShouldUseFormatterResolver(Info.Members); #>
 <# using (this.EmitNestingTypesAndNamespaces(this.Write)) { #>
+#if !NETSTANDARD2_0 && !NETFRAMEWORK
+	[global::System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverage]
+#endif
 	internal sealed class <#= Info.Formatter.GetQualifiedName(Qualifiers.None) #> : global::MessagePack.Formatters.IMessagePackFormatter<<#= Info.DataType.GetQualifiedName() #>>
 <# TransformUtilities.EmitTypeConstraints(Info.Formatter, this.Write); #>
 	{

diff --git a/src/MessagePack.SourceGenerator/Transforms/TransformUtilities.cs b/src/MessagePack.SourceGenerator/Transforms/TransformUtilities.cs
index 78518831..a7aa265a 100644
--- a/src/MessagePack.SourceGenerator/Transforms/TransformUtilities.cs
+++ b/src/MessagePack.SourceGenerator/Transforms/TransformUtilities.cs
@@ -55,7 +55,7 @@ internal static class TransformUtilities
                 writer($"partial {kind} {nestingType.GetQualifiedName(Qualifiers.None, GenericParameterStyle.Identifiers)}");
                 bool anyConstraints = EmitTypeConstraints(nestingType, writer, leadingLineFeedIfAny: true);
 
-                writer(anyConstraints ? "{" : " {\r\n");
+                writer(anyConstraints ? "{\r\n" : " {\r\n");
                 reverseAction.Push(new DisposeAction(() => writer("}\r\n")));
 
                 return new DisposeAction(() =>

diff --git a/src/MessagePack.SourceGenerator/Transforms/UnionTemplate.tt b/src/MessagePack.SourceGenerator/Transforms/UnionTemplate.tt
index 67b78a53..7408b66f 100644
--- a/src/MessagePack.SourceGenerator/Transforms/UnionTemplate.tt
+++ b/src/MessagePack.SourceGenerator/Transforms/UnionTemplate.tt
@@ -7,6 +7,9 @@
 using MsgPack = global::MessagePack;
 
 <# using (this.EmitNestingTypesAndNamespaces(this.Write)) { #>
+#if !NETSTANDARD2_0 && !NETFRAMEWORK
+	[global::System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverage]
+#endif
 	internal sealed class <#= Info.Formatter.GetQualifiedName(Qualifiers.None) #>: MsgPack::Formatters.IMessagePackFormatter<<#= Info.DataType.GetQualifiedName() #>>
 	{
 		private readonly global::System.Collections.Generic.Dictionary<global::System.RuntimeTypeHandle, global::System.Collections.Generic.KeyValuePair<int, int>> typeToKeyAndJumpMap;

diff --git a/tests/MessagePack.SourceGenerator.Tests/CodeCoverageExclusionTests.cs b/tests/MessagePack.SourceGenerator.Tests/CodeCoverageExclusionTests.cs
new file mode 100644
index 00000000..84045c55
--- /dev/null
+++ b/tests/MessagePack.SourceGenerator.Tests/CodeCoverageExclusionTests.cs
@@ -0,0 +1,130 @@
+// Copyright (c) All contributors. All rights reserved.
+// Licensed under the MIT license. See LICENSE file in the project root for full license information.
+
+using MessagePack.SourceGenerator;
+using MessagePack.SourceGenerator.Tests;
+using Microsoft.CodeAnalysis;
+using Microsoft.CodeAnalysis.CSharp;
+using Microsoft.CodeAnalysis.Testing;
+
+/// <summary>
+/// Verifies that every type emitted by the source generator is decorated with <c>ExcludeFromCodeCoverage</c>
+/// (see https://github.com/MessagePack-CSharp/MessagePack-CSharp/issues/2297).
+/// </summary>
+public class CodeCoverageExclusionTests
+{
+    private const string ExcludeAttribute = "[global::System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverage]";
+
+    // The attribute is not available on netstandard2.0 or .NET Framework, so it is only emitted where it exists.
+    private const string Guard = "#if !NETSTANDARD2_0 && !NETFRAMEWORK";
+
+    private const string TestSource = """
+        using MessagePack;
+
+        [MessagePackObject]
+        public class MyObject
+        {
+            [Key(0)]
+            public int Value { get; set; }
+        }
+
+        [MessagePackObject(keyAsPropertyName: true)]
+        public class MyStringKeyObject
+        {
+            public string Name { get; set; }
+        }
+
+        public enum MyEnum
+        {
+            A,
+            B,
+        }
+
+        [Union(0, typeof(MyUnionMember))]
+        public interface IMyUnion
+        {
+        }
+
+        [MessagePackObject]
+        public class MyUnionMember : IMyUnion
+        {
+            [Key(0)]
+            public int Value { get; set; }
+        }
+
+        namespace MessagePack
+        {
+            [GeneratedMessagePackResolver]
+            partial class GeneratedMessagePackResolver
+            {
+            }
+        }
+        """;
+
+    [Fact]
+    public async Task AllGeneratedTypesAreExcludedFromCodeCoverage()
+    {
+        IReadOnlyList<(string Path, string Text)> generated = await RunGeneratorAsync(TestSource);
+
+        // Formatters for objects (both integer and string keyed), the enum and union, plus the resolver.
+        string paths = string.Join(Environment.NewLine, generated.Select(g => g.Path));
+        Assert.True(generated.Count >= 5, $"Expected generated formatters and resolver, got:{Environment.NewLine}{paths}");
+
+        foreach ((string path, string text) in generated)
+        {
+            Assert.True(
+                text.Contains(ExcludeAttribute),
+                $"Generated file '{path}' is missing {ExcludeAttribute}.");
+        }
+    }
+
+    [Fact]
+    public async Task ExcludeAttributeIsGuardedForTargetsWhereItIsUnavailable()
+    {
+        IReadOnlyList<(string Path, string Text)> generated = await RunGeneratorAsync(TestSource);
+
+        foreach ((string path, string text) in generated)
+        {
+            string normalized = text.Replace("\r\n", "\n");
+
+            // Every occurrence of the attribute must be wrapped by the guard, so netstandard2.0 consumers still compile.
+            int attributeCount = CountOccurrences(normalized, ExcludeAttribute);
+            int guardedCount = CountOccurrences(normalized, $"{Guard}\n\t{ExcludeAttribute}\n#endif\n")
+                + CountOccurrences(normalized, $"{Guard}\n{ExcludeAttribute}\n#endif\n");
+            Assert.True(attributeCount > 0, $"Generated file '{path}' has no {ExcludeAttribute}.");
+            Assert.Equal(attributeCount, guardedCount);
+        }
+    }
+
+    private static int CountOccurrences(string text, string value)
+    {
+        int count = 0;
+        int index = 0;
+        while ((index = text.IndexOf(value, index, StringComparison.Ordinal)) >= 0)
+        {
+            count++;
+            index += value.Length;
+        }
+
+        return count;
+    }
+
+    private static async Task<IReadOnlyList<(string Path, string Text)>> RunGeneratorAsync(string source)
+    {
+        ImmutableArray<MetadataReference> frameworkReferences = await ReferencesHelper.DefaultTargetFrameworkReferences.ResolveAsync(LanguageNames.CSharp, CancellationToken.None);
+
+        CSharpCompilation compilation = CSharpCompilation.Create(
+            assemblyName: "CodeCoverageExclusionTests",
+            syntaxTrees: [CSharpSyntaxTree.ParseText(source, new CSharpParseOptions(LanguageVersion.Latest))],
+            references: frameworkReferences.Concat(ReferencesHelper.GetReferences(ReferencesSet.MessagePack)),
+            options: new CSharpCompilationOptions(OutputKind.DynamicallyLinkedLibrary));
+
+        var driver = CSharpGeneratorDriver.Create(new MessagePackGenerator());
+        driver = (CSharpGeneratorDriver)driver.RunGeneratorsAndUpdateCompilation(compilation, out _, out _);
+        GeneratorDriverRunResult result = driver.GetRunResult();
+
+        return result.GeneratedTrees
+            .Select(tree => (tree.FilePath, tree.GetText().ToString()))
+            .ToList();
+    }
+}

```

## File contents (line numbers in the gutter; quote the text after '| ')

### src/MessagePack.SourceGenerator/Transforms/CompositeResolverTemplate.tt at head (a0aa5ab2), full file
```
    1| <#@ template debug="false" hostspecific="false" linePragmas="false" language="C#" #>
    2| 
    3| using MsgPack = global::MessagePack;
    4| 
    5| <# using (TransformUtilities.EmitNestingTypesAndNamespaces(this.ResolverName, this.Write)) { #>
    6| 
    7| #if !NETSTANDARD2_0 && !NETFRAMEWORK
    8| [global::System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverage]
    9| #endif
   10| partial class <#= ResolverName.Name #> : MsgPack::IFormatterResolver
   11| {
   12| 	public static readonly <#= ResolverName.Name #> Instance = new <#= ResolverName.Name #>();
   13| 
   14| 	private static readonly MsgPack::Formatters.IMessagePackFormatter[] formatterList = new MsgPack::Formatters.IMessagePackFormatter[]
   15| 	{
   16| <# foreach (string expr in FormatterInstanceExpressions) { #>
   17| 		<#= expr #>,
   18| <# } #>
   19| 	};
   20| 
   21| 	private static readonly MsgPack::IFormatterResolver[] resolverList = new MsgPack::IFormatterResolver[]
   22| 	{
   23| <# foreach (string expr in ResolverInstanceExpressions) { #>
   24| 		<#= expr #>,
   25| <# } #>
   26| 	};
   27| 
   28| 	private <#= ResolverName.Name #>() { }
   29| 
   30| 	public MsgPack::Formatters.IMessagePackFormatter<T> GetFormatter<T>()
   31| 	{
   32| 		return FormatterCache<T>.Formatter;
   33| 	}
   34| 
   35| #if !NETSTANDARD2_0 && !NETFRAMEWORK
   36| 	[global::System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverage]
   37| #endif
   38| 	static class FormatterCache<T>
   39| 	{
   40| 		internal static readonly MsgPack::Formatters.IMessagePackFormatter<T> Formatter;
   41| 
   42| 		static FormatterCache()
   43| 		{
   44| 			foreach (var formatter in formatterList)
   45| 			{
   46| 				if (formatter is MsgPack::Formatters.IMessagePackFormatter<T> f)
   47| 				{
   48| 					Formatter = f;
   49| 					return;
   50| 				}
   51| 			}
   52| 
   53| 			foreach (var resolver in resolverList)
   54| 			{
   55| 				var f = resolver.GetFormatter<T>();
   56| 				if (f != null)
   57| 				{
   58| 					Formatter = f;
   59| 					return;
   60| 				}
   61| 			}
   62| 		}
   63| 	}
   64| }
   65| 
   66| <# } #>
```

### src/MessagePack.SourceGenerator/Transforms/EnumTemplate.tt at head (a0aa5ab2), full file
```
    1| ﻿<#@ template debug="false" hostspecific="false" linePragmas="false" language="C#" #>
    2| <#@ assembly name="System.Core" #>
    3| 
    4| using MsgPack = global::MessagePack;
    5| 
    6| <# using (this.EmitNestingTypesAndNamespaces(this.Write)) { #>
    7| 
    8| #if !NETSTANDARD2_0 && !NETFRAMEWORK
    9| 	[global::System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverage]
   10| #endif
   11| 	internal sealed class <#= Info.Formatter.Name #> : MsgPack::Formatters.IMessagePackFormatter<<#= Info.DataType.GetQualifiedName() #>>
   12| 	{
   13| 		public void Serialize(ref MsgPack::MessagePackWriter writer, <#= Info.DataType.GetQualifiedName() #> value, MsgPack::MessagePackSerializerOptions options)
   14| 		{
   15| 			writer.Write((<#= Info.UnderlyingTypeKeyword #>)value);
   16| 		}
   17| 
   18| 		public <#= Info.DataType.GetQualifiedName() #> Deserialize(ref MsgPack::MessagePackReader reader, MsgPack::MessagePackSerializerOptions options)
   19| 		{
   20| 			return (<#= Info.DataType.GetQualifiedName() #>)reader.Read<#= Info.UnderlyingTypeName #>();
   21| 		}
   22| 	}
   23| 
   24| <# } #>
```

### src/MessagePack.SourceGenerator/Transforms/FormatterTemplate.tt at head (a0aa5ab2), full file
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
   14| #if !NETSTANDARD2_0 && !NETFRAMEWORK
   15| 	[global::System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverage]
   16| #endif
   17| 	internal sealed class <#= Info.Formatter.GetQualifiedName(Qualifiers.None) #> : MsgPack::Formatters.IMessagePackFormatter<<#= Info.DataType.GetQualifiedName(genericStyle: GenericParameterStyle.Identifiers) #>>
   18| <# TransformUtilities.EmitTypeConstraints(Info.Formatter, this.Write); #>
   19| 	{
   20| <# foreach (var item in Info.Members) { #>
   21| <# if (item.CustomFormatter != null) { #>
   22| 		private readonly <#= item.CustomFormatter.InstanceTypeName.GetQualifiedName(genericStyle: GenericParameterStyle.Arguments) #> __<#= item.Name #>CustomFormatter__ = <#= item.CustomFormatter.InstanceExpression #>;
   23| <# } #>
   24| <# } #>
   25| 
   26| 		public void Serialize(ref MsgPack::MessagePackWriter writer, <#= Info.DataType.GetQualifiedName(genericStyle: GenericParameterStyle.Identifiers) #> value, MsgPack::MessagePackSerializerOptions options)
   27| 		{
   28| <# if (Info.IsClass) { #>
   29| 			if (value == null)
   30| 			{
   31| 				writer.WriteNil();
   32| 				return;
   33| 			}
   34| 
   35| <# }
   36| 
   37|   if (isFormatterResolverNecessary) { #>
   38| 			MsgPack::IFormatterResolver formatterResolver = options.Resolver;
   39| <# }
   40| 
   41|  if (Info.HasIMessagePackSerializationCallbackReceiver) {
   42|   if (Info.NeedsCastOnBefore) { #>
   43| 			((MsgPack::IMessagePackSerializationCallbackReceiver)value).OnBeforeSerialize();
   44| <# } else { #>
   45| 			value.OnBeforeSerialize();
   46| <# } #>
   47| <# } #>
   48| 			writer.WriteArrayHeader(<#= Info.MaxKey + 1 #>);
   49| <# for (var i = 0; i <= Info.MaxKey; i++) {
   50|   var member = Info.GetMember(i);
   51|   if (member == null) { #>
   52| 			writer.WriteNil();
   53| <# } else { #>
   54| 			<#= member.GetSerializeMethodString() #>;
   55| <# } #>
   56| <# } #>
   57| 		}
   58| 
   59| 		public <#= Info.DataType.GetQualifiedName(genericStyle: GenericParameterStyle.Identifiers) #> Deserialize(ref MsgPack::MessagePackReader reader, MsgPack::MessagePackSerializerOptions options)
   60| 		{
   61| 			if (reader.TryReadNil())
   62| 			{
   63| <# if (Info.IsClass) { #>
   64| 				return null;
   65| <# } else { #>
   66| 				throw new global::System.InvalidOperationException("typecode is null, struct not supported");
   67| <# } #>
   68| 			}
   69| 
   70| <# if (Info.MaxKey == -1 && !Info.HasIMessagePackSerializationCallbackReceiver) { #>
   71| 			reader.Skip();
   72| 			return new <#= Info.GetConstructorString()  #>;
   73| <# } else { #>
   74| 			options.Security.DepthStep(ref reader);
   75| <# if (isFormatterResolverNecessary) { #>
   76| 			MsgPack::IFormatterResolver formatterResolver = options.Resolver;
   77| <# } #>
   78| 			var length = reader.ReadArrayHeader();
   79| <# if (Info.MustDeserializeFieldsFirst) { 
   80| 	foreach (var member in Info.Members) { #>
   81| 			var <#= member.LocalVariableName #> = default(<#= member.Type #>);
   82| <#	}
   83| } else { #>
   84| 			var ____result = new <#= Info.GetConstructorString()  #>;
   85| <# } #>
   86| 
   87| 			for (int i = 0; i < length; i++)
   88| 			{
   89| 				switch (i)
   90| 				{
   91| <# for (var memberIndex = 0; memberIndex <= Info.MaxKey; memberIndex++) {
   92|   var member = Info.GetMember(memberIndex);
   93|   if (member == null) { continue; } #>
   94| 					case <#= member.IntKey #>:
   95| <# if (Info.MustDeserializeFieldsFirst) { #>
   96| 						<#= member.LocalVariableName #> = <#= member.GetDeserializeMethodString() #>;
   97| <# } else {
   98|   if (member.IsWritable) { #>
   99| 						<#= member.GetMemberAccess("____result") #> = <#= member.GetDeserializeMethodString() #>;
  100| <# } else { #>
  101| 						reader.Skip();
  102| <# } #>
  103| <# } #>
  104| 						break;
  105| <# } #>
  106| 					default:
  107| 						reader.Skip();
  108| 						break;
  109| 				}
  110| 			}
  111| 
  112| <# if (Info.MustDeserializeFieldsFirst) { #>
  113| 			var ____result = new <#= Info.GetConstructorString() #>;
  114| <# bool memberAssignExists = false;
  115|   for (var memberIndex = 0; memberIndex <= Info.MaxKey; memberIndex++) {
  116|   var member = Info.GetMember(memberIndex);
  117|   if (member == null || !member.IsWritable || member.IsInitOnly || member.IsRequired || Info.ConstructorParameters.Any(p => p.Equals(member))) { continue; }
  118|   memberAssignExists = true;#>
  119| 			if (length <= <#= memberIndex #>)
  120| 			{
  121| 				goto MEMBER_ASSIGNMENT_END;
  122| 			}
  123| 
  124| 			<#= member.GetMemberAccess("____result") #> = <#= member.LocalVariableName #>;
  125| <# } #>
  126| <# if (memberAssignExists) { #>
  127| 
  128| 		MEMBER_ASSIGNMENT_END:
  129| <# }
  130|  }
  131| 
  132|  if (Info.HasIMessagePackSerializationCallbackReceiver) {
  133|   if (Info.NeedsCastOnAfter) { #>
  134| 			((MsgPack::IMessagePackSerializationCallbackReceiver)____result).OnAfterDeserialize();
  135| <# } else { #>
  136| 			____result.OnAfterDeserialize();
  137| <# } #>
  138| <# } #>
  139| 			reader.Depth--;
  140| 			return ____result;
  141| <# } #>
  142| 		}
  143| 	}
  144| <# } #>
```

### src/MessagePack.SourceGenerator/Transforms/ResolverTemplate.tt at head (a0aa5ab2), full file
```
    1| ﻿<#@ template debug="false" hostspecific="false" linePragmas="false" language="C#" #>
    2| <#@ assembly name="System.Core" #>
    3| <#@ import namespace="System.Linq" #>
    4| <#@ import namespace="System.Text" #>
    5| <#@ import namespace="System.Collections.Generic" #>
    6| 
    7| using MsgPack = global::MessagePack;
    8| 
    9| [assembly: MsgPack::Internal.GeneratedAssemblyMessagePackResolverAttribute(typeof(<#= this.ResolverName.GetQualifiedName(Qualifiers.Namespace) #>), <#= Version.Parse(ThisAssembly.AssemblyFileVersion).Major #>, <#= Version.Parse(ThisAssembly.AssemblyFileVersion).Minor #>)]
   10| 
   11| <# using (TransformUtilities.EmitNestingTypesAndNamespaces(this.ResolverName, this.Write)) { #>
   12| 
   13| /// <summary>A MessagePack resolver that uses generated formatters for types in this assembly.</summary>
   14| #if !NETSTANDARD2_0 && !NETFRAMEWORK
   15| [global::System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverage]
   16| #endif
   17| partial class <#= ResolverName.Name #> : MsgPack::IFormatterResolver
   18| {
   19| 	/// <summary>An instance of this resolver that only returns formatters specifically generated for types in this assembly.</summary>
   20| 	public static readonly MsgPack::IFormatterResolver Instance = new <#= ResolverName.Name #>();
   21| 
   22| 	private <#= ResolverName.Name #>()
   23| 	{
   24| 	}
   25| 
   26| 	public MsgPack::Formatters.IMessagePackFormatter<T> GetFormatter<T>()
   27| 	{
   28| 		return FormatterCache<T>.Formatter;
   29| 	}
   30| 
   31| #if !NETSTANDARD2_0 && !NETFRAMEWORK
   32| 	[global::System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverage]
   33| #endif
   34| 	private static class FormatterCache<T>
   35| 	{
   36| 		internal static readonly MsgPack::Formatters.IMessagePackFormatter<T> Formatter;
   37| 
   38| 		static FormatterCache()
   39| 		{
   40| 			var f = <#= ResolverName.Name #>GetFormatterHelper.GetFormatter(typeof(T));
   41| 			if (f != null)
   42| 			{
   43| 				Formatter = (MsgPack::Formatters.IMessagePackFormatter<T>)f;
   44| 			}
   45| 		}
   46| 	}
   47| 
   48| #if !NETSTANDARD2_0 && !NETFRAMEWORK
   49| 	[global::System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverage]
   50| #endif
   51| 	private static class <#= ResolverName.Name #>GetFormatterHelper
   52| 	{
   53| <#
   54|    var constructedRegistrations = ConstructedTypeRegistrations.ToArray();
   55|    if (constructedRegistrations.Length > 0) { #>
   56| 		private static readonly global::System.Collections.Generic.Dictionary<global::System.Type, int> closedTypeLookup = new global::System.Collections.Generic.Dictionary<global::System.Type, int>(<#= constructedRegistrations.Length #>)
   57| 		{
   58| <# for(var i = 0; i < constructedRegistrations.Length; i++) { #>
   59| 			{ typeof(<#= constructedRegistrations[i].DataType.GetQualifiedName(genericStyle: GenericParameterStyle.Arguments) #>), <#= i #> },
   60| <# } #>
   61| 		};
   62| <# }
   63|    var openGenericRegistrations = OpenGenericRegistrations.ToArray();
   64|    if (openGenericRegistrations.Length > 0) { #>
   65| 		private static readonly global::System.Collections.Generic.Dictionary<global::System.Type, int> openTypeLookup = new global::System.Collections.Generic.Dictionary<global::System.Type, int>(<#= openGenericRegistrations.Length #>)
   66| 		{
   67| <# for(var i = 0; i < openGenericRegistrations.Length; i++) { #>
   68| 			{ typeof(<#= openGenericRegistrations[i].DataType.GetQualifiedName(genericStyle: GenericParameterStyle.TypeDefinition) #>), <#= i #> },
   69| <# } #>
   70| 		};
   71| <# } #>
   72| 
   73| 		internal static object GetFormatter(global::System.Type t)
   74| 		{
   75| <# if (constructedRegistrations.Length > 0) { #>
   76| 			if (closedTypeLookup.TryGetValue(t, out int closedKey))
   77| 			{
   78| 				switch (closedKey)
   79| 				{
   80| <# for(var i = 0; i < constructedRegistrations.Length; i++) { var x = constructedRegistrations[i]; #>
   81| 					case <#= i #>: return <#= x.GetFormatterInstanceForResolver() #>;
   82| <# } #>
   83| 					default: return null; // unreachable
   84| 				};
   85| 			}
   86| <# }
   87| 
   88|    if (openGenericRegistrations.Length > 0) { #>
   89| 			if (t.IsGenericType && openTypeLookup.TryGetValue(t.GetGenericTypeDefinition(), out int openKey))
   90| 			{
   91| 				switch (openKey)
   92| 				{
   93| <#     for(var i = 0; i < openGenericRegistrations.Length; i++) { var x = openGenericRegistrations[i]; #>
   94| 					case <#= i #>: return global::System.Activator.CreateInstance(typeof(<#= x.GetFormatterNameForResolver(GenericParameterStyle.TypeDefinition) #>).MakeGenericType(t.GenericTypeArguments));
   95| <#     } #>
   96| 					default: return null; // unreachable
   97| 				};
   98| 			}
   99| <# } #>
  100| 
  101| 			return null;
  102| 		}
  103| 	}
  104| }
  105| 
  106| <# } #>
```

### src/MessagePack.SourceGenerator/Transforms/StringKey/StringKeyFormatterTemplate.tt at head (a0aa5ab2), full file
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
   18| #if !NETSTANDARD2_0 && !NETFRAMEWORK
   19| 	[global::System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverage]
   20| #endif
   21| 	internal sealed class <#= Info.Formatter.GetQualifiedName(Qualifiers.None) #> : global::MessagePack.Formatters.IMessagePackFormatter<<#= Info.DataType.GetQualifiedName() #>>
   22| <# TransformUtilities.EmitTypeConstraints(Info.Formatter, this.Write); #>
   23| 	{
   24| <# foreach (var item in Info.Members) { #>
   25| <# if (item.CustomFormatter != null) { #>
   26| 		private readonly <#= item.CustomFormatter.Name.GetQualifiedName() #> __<#= item.Name #>CustomFormatter__ = <#= item.CustomFormatter.InstanceExpression #>;
   27| <# } #>
   28| <# } #>
   29| <# for (var i = 0; i < list.Count; i++) {
   30| 		var member = list[i].Item1;
   31| 		var binary = list[i].Item2; #>
   32| 		// <#= member.StringKey #>
   33| 		private static global::System.ReadOnlySpan<byte> GetSpan_<#= member.UniqueIdentifier #>() => <#= EmbedStringHelper.ToByteArrayString(binary) #>;
   34| <# } #>
   35| <# if (list.Count != 0) { #>
   36| 
   37| <# } #>
   38| 		public void Serialize(ref global::MessagePack.MessagePackWriter writer, <#= Info.DataType.GetQualifiedName() #> value, global::MessagePack.MessagePackSerializerOptions options)
   39| 		{
   40| <# if (Info.IsClass) { #>
   41| 			if (value is null)
   42| 			{
   43| 				writer.WriteNil();
   44| 				return;
   45| 			}
   46| 
   47| <# }
   48| 
   49| 	if (isFormatterResolverNecessary) { #>
   50| 			var formatterResolver = options.Resolver;
   51| <# }
   52| 
   53| 	if (Info.HasIMessagePackSerializationCallbackReceiver) {
   54| 		if (Info.NeedsCastOnBefore) { #>
   55| 			((global::MessagePack.IMessagePackSerializationCallbackReceiver)value).OnBeforeSerialize();
   56| <# } else { #>
   57| 			value.OnBeforeSerialize();
   58| <# } #>
   59| <# } #>
   60| 			writer.WriteMapHeader(<#= list.Count #>);
   61| <# foreach (var memberAndBinary in list) {
   62| 		var member = memberAndBinary.Item1; #>
   63| 			writer.WriteRaw(GetSpan_<#= member.UniqueIdentifier #>());
   64| 			<#= member.GetSerializeMethodString() #>;
   65| <# } #>
   66| 		}
   67| 
   68| 		public <#= Info.DataType.GetQualifiedName() #> Deserialize(ref global::MessagePack.MessagePackReader reader, global::MessagePack.MessagePackSerializerOptions options)
   69| 		{
   70| 			if (reader.TryReadNil())
   71| 			{
   72| <# if (Info.IsClass) { #>
   73| 				return null;
   74| <# } else { #>
   75| 				throw new global::System.InvalidOperationException("typecode is null, struct not supported");
   76| <# } #>
   77| 			}
   78| 
   79| <# if (Info.Members.Length == 0) { #>
   80| 			reader.Skip();
   81| 			var ____result = new <#= Info.GetConstructorString() #>;
   82| <# } else { #>
   83| 			options.Security.DepthStep(ref reader);
   84| <# if (isFormatterResolverNecessary) { #>
   85| 			var formatterResolver = options.Resolver;
   86| <# } #>
   87| 			var length = reader.ReadMapHeader();
   88| <# if (Info.MustDeserializeFieldsFirst) {
   89| 	foreach (var member in Info.Members.Where(x => x.IsWritable || Info.ConstructorParameters.Any(p => p.Equals(x)))) {
   90| 		// Until C# allows for optionally setting init-only properties (https://github.com/dotnet/csharplang/issues/6117)
   91| 		// we will unconditionally set them, and thus have no reason to track whether the local variable has been initialized.
   92| 		if (!member.IsInitOnly && !member.IsRequired && !Info.ConstructorParameters.Any(p => p.Equals(member))) { #>
   93| 			var <#= member.LocalVariableName #>IsInitialized = false;
   94| <#		} #>
   95| 			var <#= member.LocalVariableName #> = default(<#= member.Type #>);
   96| <#	} #>
   97| <# } else { #>
   98| 			var ____result = new <#= Info.GetConstructorString() #>;
   99| <# } #>
  100| 
  101| 			for (int i = 0; i < length; i++)
  102| 			{
  103| 				var stringKey = global::MessagePack.Internal.CodeGenHelpers.ReadStringSpan(ref reader);
  104| 				switch (stringKey.Length)
  105| 				{
  106| 					default:
  107| 					FAIL:
  108| 					  reader.Skip();
  109| 					  continue;
  110| <#= StringKeyFormatterDeserializeHelper.Classify(Info, "					", !Info.MustDeserializeFieldsFirst) #>
  111| 				}
  112| 			}
  113| 
  114| <# if (Info.MustDeserializeFieldsFirst) { #>
  115| 			var ____result = new <#= Info.GetConstructorString() #>;
  116| <# foreach (var member in Info.Members.Where(x => x.IsWritable && !x.IsInitOnly && !x.IsRequired && !Info.ConstructorParameters.Any(p => p.Equals(x)))) { #>
  117| 			if (<#= member.LocalVariableName #>IsInitialized)
  118| 			{
  119| 				<#= member.GetMemberAccess("____result") #> = <#= member.LocalVariableName #>;
  120| 			}
  121| 
  122| <# } #>
  123| <# } #>
  124| <# } #>
  125| <# if (Info.HasIMessagePackSerializationCallbackReceiver) {
  126| 		if (Info.NeedsCastOnAfter) { #>
  127| 			((global::MessagePack.IMessagePackSerializationCallbackReceiver)____result).OnAfterDeserialize();
  128| <# } else { #>
  129| 			____result.OnAfterDeserialize();
  130| <# } #>
  131| <# } #>
  132| <# if (Info.Members.Length != 0) { #>
  133| 			reader.Depth--;
  134| <# } #>
  135| 			return ____result;
  136| 		}
  137| 	}
  138| 
  139| <# } #>
```

### src/MessagePack.SourceGenerator/Transforms/TransformUtilities.cs at head (a0aa5ab2), full file
```
    1| ﻿// Copyright (c) All contributors. All rights reserved.
    2| // Licensed under the MIT license. See LICENSE file in the project root for full license information.
    3| 
    4| using Microsoft.CodeAnalysis;
    5| 
    6| namespace MessagePack.SourceGenerator.Transforms;
    7| 
    8| internal static class TransformUtilities
    9| {
   10|     internal static IDisposable? EmitNestingTypesAndNamespaces(this IFormatterTemplate template, Action<string> writer)
   11|         => EmitNestingTypesAndNamespaces(template.Info.Formatter, writer);
   12| 
   13|     internal static IDisposable? EmitNestingTypesAndNamespaces(QualifiedTypeName nestedType, Action<string> writer)
   14|         => nestedType is QualifiedNamedTypeName { Container: { } container } ? EmitNestingTypesAndNamespaces(container, writer) : null;
   15| 
   16|     internal static IDisposable? EmitNestingTypesAndNamespaces(TypeContainer container, Action<string> writer)
   17|     {
   18|         switch (container)
   19|         {
   20|             case NamespaceTypeContainer { Namespace: string ns }:
   21|                 writer($"namespace {ns} {{\r\n");
   22|                 return new DisposeAction(() => writer("}\r\n"));
   23|             case NestingTypeContainer { NestingType: { } nestingType }:
   24|                 Stack<IDisposable?> reverseAction = new();
   25| 
   26|                 // Start with outer-most type.
   27|                 if (nestingType.Container is not null)
   28|                 {
   29|                     reverseAction.Push(EmitNestingTypesAndNamespaces(nestingType.Container, writer));
   30|                 }
   31| 
   32|                 var kind = nestingType.Kind switch
   33|                 {
   34|                     TypeKind.Class when nestingType.IsRecord => "record", // C# 9 doesn't want to see `record class`.
   35|                     TypeKind.Class => "class",
   36|                     TypeKind.Struct when nestingType.IsRecord => "record struct",
   37|                     TypeKind.Struct => "struct",
   38|                     TypeKind.Interface => "interface",
   39|                     _ => throw new NotSupportedException("Unsupported kind: " + nestingType.Kind),
   40|                 };
   41| 
   42|                 var accessModifier = nestingType.AccessModifier switch
   43|                 {
   44|                     Accessibility.Public => "public",
   45|                     Accessibility.Internal => "internal",
   46|                     Accessibility.Private => "private",
   47|                     _ => null,
   48|                 };
   49|                 if (accessModifier is not null)
   50|                 {
   51|                     writer(accessModifier);
   52|                     writer($" ");
   53|                 }
   54| 
   55|                 writer($"partial {kind} {nestingType.GetQualifiedName(Qualifiers.None, GenericParameterStyle.Identifiers)}");
   56|                 bool anyConstraints = EmitTypeConstraints(nestingType, writer, leadingLineFeedIfAny: true);
   57| 
   58|                 writer(anyConstraints ? "{\r\n" : " {\r\n");
   59|                 reverseAction.Push(new DisposeAction(() => writer("}\r\n")));
   60| 
   61|                 return new DisposeAction(() =>
   62|                 {
   63|                     while (reverseAction.Count > 0)
   64|                     {
   65|                         reverseAction.Pop()?.Dispose();
   66|                     }
   67|                 });
   68|             default:
   69|                 throw new NotSupportedException();
   70|         }
   71|     }
   72| 
   73|     internal static bool EmitTypeConstraints(QualifiedNamedTypeName target, Action<string> writer, bool leadingLineFeedIfAny = false)
   74|     {
   75|         bool anyConstraints = false;
   76|         foreach (GenericTypeParameterInfo typeParameter in target.TypeParameters)
   77|         {
   78|             if (typeParameter.HasConstraints)
   79|             {
   80|                 if (leadingLineFeedIfAny && !anyConstraints)
   81|                 {
   82|                     writer("\r\n");
   83|                 }
   84| 
   85|                 anyConstraints = true;
   86|                 writer($"\t\twhere {typeParameter.Name} : {typeParameter.Constraints}\r\n");
   87|             }
   88|         }
   89| 
   90|         return anyConstraints;
   91|     }
   92| 
   93|     internal static IDisposable? EmitClassesForNamespace(this IFormatterTemplate template, out string formatterVisibility, Action<string> writer)
   94|     {
   95|         if (template.Info.DataType is not QualifiedNamedTypeName { Container: NamespaceTypeContainer { Namespace: string ns } })
   96|         {
   97|             formatterVisibility = "private";
   98|             return null;
   99|         }
  100| 
  101|         int depth = 0;
  102|         foreach (string segment in ns.Split('.'))
  103|         {
  104|             string visibility = depth == 0 ? "private" : "internal";
  105|             writer($"{visibility} partial class {segment} {{ ");
  106|             depth++;
  107|         }
  108| 
  109|         writer("\r\n");
  110| 
  111|         formatterVisibility = "internal";
  112|         return new DisposeAction(() =>
  113|         {
  114|             for (int i = 0; i < depth; i++)
  115|             {
  116|                 writer("}");
  117|             }
  118|         });
  119|     }
  120| 
  121|     private class DisposeAction : IDisposable
  122|     {
  123|         private Action? disposeAction;
  124| 
  125|         internal DisposeAction(Action? action)
  126|         {
  127|             this.disposeAction = action;
  128|         }
  129| 
  130|         public void Dispose()
  131|         {
  132|             this.disposeAction?.Invoke();
  133|             this.disposeAction = null;
  134|         }
  135|     }
  136| }
```

### src/MessagePack.SourceGenerator/Transforms/UnionTemplate.tt at head (a0aa5ab2), full file
```
    1| ﻿<#@ template debug="false" hostspecific="false" linePragmas="false" language="C#" #>
    2| <#@ assembly name="System.Core" #>
    3| <#@ import namespace="System.Linq" #>
    4| <#@ import namespace="System.Text" #>
    5| <#@ import namespace="System.Collections.Generic" #>
    6| 
    7| using MsgPack = global::MessagePack;
    8| 
    9| <# using (this.EmitNestingTypesAndNamespaces(this.Write)) { #>
   10| #if !NETSTANDARD2_0 && !NETFRAMEWORK
   11| 	[global::System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverage]
   12| #endif
   13| 	internal sealed class <#= Info.Formatter.GetQualifiedName(Qualifiers.None) #>: MsgPack::Formatters.IMessagePackFormatter<<#= Info.DataType.GetQualifiedName() #>>
   14| 	{
   15| 		private readonly global::System.Collections.Generic.Dictionary<global::System.RuntimeTypeHandle, global::System.Collections.Generic.KeyValuePair<int, int>> typeToKeyAndJumpMap;
   16| 		private readonly global::System.Collections.Generic.Dictionary<int, int> keyToJumpMap;
   17| 
   18| 		public <#= Info.Formatter.Name #>()
   19| 		{
   20| 			this.typeToKeyAndJumpMap = new global::System.Collections.Generic.Dictionary<global::System.RuntimeTypeHandle, global::System.Collections.Generic.KeyValuePair<int, int>>(<#= Info.SubTypes.Length #>, MsgPack::Internal.RuntimeTypeHandleEqualityComparer.Default)
   21| 			{
   22| <# for(var i = 0; i < Info.SubTypes.Length; i++) { var item = Info.SubTypes[i]; #>
   23| 				{ typeof(<#= item.Type #>).TypeHandle, new global::System.Collections.Generic.KeyValuePair<int, int>(<#= item.Key #>, <#= i #>) },
   24| <# } #>
   25| 			};
   26| 			this.keyToJumpMap = new global::System.Collections.Generic.Dictionary<int, int>(<#= Info.SubTypes.Length #>)
   27| 			{
   28| <# for(var i = 0; i < Info.SubTypes.Length; i++) { var item = Info.SubTypes[i]; #>
   29| 				{ <#= item.Key #>, <#= i #> },
   30| <# } #>
   31| 			};
   32| 		}
   33| 
   34| 		public void Serialize(ref MsgPack::MessagePackWriter writer, <#= Info.DataType.GetQualifiedName() #> value, MsgPack::MessagePackSerializerOptions options)
   35| 		{
   36| 			global::System.Collections.Generic.KeyValuePair<int, int> keyValuePair;
   37| 			if (value != null && this.typeToKeyAndJumpMap.TryGetValue(value.GetType().TypeHandle, out keyValuePair))
   38| 			{
   39| 				writer.WriteArrayHeader(2);
   40| 				writer.WriteInt32(keyValuePair.Key);
   41| 				switch (keyValuePair.Value)
   42| 				{
   43| <# for(var i = 0; i < Info.SubTypes.Length; i++) { var item = Info.SubTypes[i]; #>
   44| 					case <#= i #>:
   45| 						MsgPack::FormatterResolverExtensions.GetFormatterWithVerify<<#= item.Type #>>(options.Resolver).Serialize(ref writer, (<#= item.Type #>)value, options);
   46| 						break;
   47| <# } #>
   48| 					default:
   49| 						break;
   50| 				}
   51| 
   52| 				return;
   53| 			}
   54| 
   55| 			writer.WriteNil();
   56| 		}
   57| 
   58| 		public <#= Info.DataType.GetQualifiedName() #> Deserialize(ref MsgPack::MessagePackReader reader, MsgPack::MessagePackSerializerOptions options)
   59| 		{
   60| 			if (reader.TryReadNil())
   61| 			{
   62| 				return null;
   63| 			}
   64| 
   65| 			if (reader.ReadArrayHeader() != 2)
   66| 			{
   67| 				throw new global::System.InvalidOperationException("Invalid Union data was detected. Type:<#= Info.DataType.GetQualifiedName() #>");
   68| 			}
   69| 
   70| 			options.Security.DepthStep(ref reader);
   71| 			var key = reader.ReadInt32();
   72| 
   73| 			if (!this.keyToJumpMap.TryGetValue(key, out key))
   74| 			{
   75| 				key = -1;
   76| 			}
   77| 
   78| 			<#= Info.DataType.GetQualifiedName() #> result = null;
   79| 			switch (key)
   80| 			{
   81| <# for(var i = 0; i < Info.SubTypes.Length; i++) { var item = Info.SubTypes[i]; #>
   82| 				case <#= i #>:
   83| 					result = (<#= Info.DataType.GetQualifiedName() #>)MsgPack::FormatterResolverExtensions.GetFormatterWithVerify<<#= item.Type #>>(options.Resolver).Deserialize(ref reader, options);
   84| 					break;
   85| <# } #>
   86| 				default:
   87| 					reader.Skip();
   88| 					break;
   89| 			}
   90| 
   91| 			reader.Depth--;
   92| 			return result;
   93| 		}
   94| 	}
   95| 
   96| <# } #>
```

### tests/MessagePack.SourceGenerator.Tests/CodeCoverageExclusionTests.cs at head (a0aa5ab2), full file
```
    1| // Copyright (c) All contributors. All rights reserved.
    2| // Licensed under the MIT license. See LICENSE file in the project root for full license information.
    3| 
    4| using MessagePack.SourceGenerator;
    5| using MessagePack.SourceGenerator.Tests;
    6| using Microsoft.CodeAnalysis;
    7| using Microsoft.CodeAnalysis.CSharp;
    8| using Microsoft.CodeAnalysis.Testing;
    9| 
   10| /// <summary>
   11| /// Verifies that every type emitted by the source generator is decorated with <c>ExcludeFromCodeCoverage</c>
   12| /// (see https://github.com/MessagePack-CSharp/MessagePack-CSharp/issues/2297).
   13| /// </summary>
   14| public class CodeCoverageExclusionTests
   15| {
   16|     private const string ExcludeAttribute = "[global::System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverage]";
   17| 
   18|     // The attribute is not available on netstandard2.0 or .NET Framework, so it is only emitted where it exists.
   19|     private const string Guard = "#if !NETSTANDARD2_0 && !NETFRAMEWORK";
   20| 
   21|     private const string TestSource = """
   22|         using MessagePack;
   23| 
   24|         [MessagePackObject]
   25|         public class MyObject
   26|         {
   27|             [Key(0)]
   28|             public int Value { get; set; }
   29|         }
   30| 
   31|         [MessagePackObject(keyAsPropertyName: true)]
   32|         public class MyStringKeyObject
   33|         {
   34|             public string Name { get; set; }
   35|         }
   36| 
   37|         public enum MyEnum
   38|         {
   39|             A,
   40|             B,
   41|         }
   42| 
   43|         [Union(0, typeof(MyUnionMember))]
   44|         public interface IMyUnion
   45|         {
   46|         }
   47| 
   48|         [MessagePackObject]
   49|         public class MyUnionMember : IMyUnion
   50|         {
   51|             [Key(0)]
   52|             public int Value { get; set; }
   53|         }
   54| 
   55|         namespace MessagePack
   56|         {
   57|             [GeneratedMessagePackResolver]
   58|             partial class GeneratedMessagePackResolver
   59|             {
   60|             }
   61|         }
   62|         """;
   63| 
   64|     [Fact]
   65|     public async Task AllGeneratedTypesAreExcludedFromCodeCoverage()
   66|     {
   67|         IReadOnlyList<(string Path, string Text)> generated = await RunGeneratorAsync(TestSource);
   68| 
   69|         // Formatters for objects (both integer and string keyed), the enum and union, plus the resolver.
   70|         string paths = string.Join(Environment.NewLine, generated.Select(g => g.Path));
   71|         Assert.True(generated.Count >= 5, $"Expected generated formatters and resolver, got:{Environment.NewLine}{paths}");
   72| 
   73|         foreach ((string path, string text) in generated)
   74|         {
   75|             Assert.True(
   76|                 text.Contains(ExcludeAttribute),
   77|                 $"Generated file '{path}' is missing {ExcludeAttribute}.");
   78|         }
   79|     }
   80| 
   81|     [Fact]
   82|     public async Task ExcludeAttributeIsGuardedForTargetsWhereItIsUnavailable()
   83|     {
   84|         IReadOnlyList<(string Path, string Text)> generated = await RunGeneratorAsync(TestSource);
   85| 
   86|         foreach ((string path, string text) in generated)
   87|         {
   88|             string normalized = text.Replace("\r\n", "\n");
   89| 
   90|             // Every occurrence of the attribute must be wrapped by the guard, so netstandard2.0 consumers still compile.
   91|             int attributeCount = CountOccurrences(normalized, ExcludeAttribute);
   92|             int guardedCount = CountOccurrences(normalized, $"{Guard}\n\t{ExcludeAttribute}\n#endif\n")
   93|                 + CountOccurrences(normalized, $"{Guard}\n{ExcludeAttribute}\n#endif\n");
   94|             Assert.True(attributeCount > 0, $"Generated file '{path}' has no {ExcludeAttribute}.");
   95|             Assert.Equal(attributeCount, guardedCount);
   96|         }
   97|     }
   98| 
   99|     private static int CountOccurrences(string text, string value)
  100|     {
  101|         int count = 0;
  102|         int index = 0;
  103|         while ((index = text.IndexOf(value, index, StringComparison.Ordinal)) >= 0)
  104|         {
  105|             count++;
  106|             index += value.Length;
  107|         }
  108| 
  109|         return count;
  110|     }
  111| 
  112|     private static async Task<IReadOnlyList<(string Path, string Text)>> RunGeneratorAsync(string source)
  113|     {
  114|         ImmutableArray<MetadataReference> frameworkReferences = await ReferencesHelper.DefaultTargetFrameworkReferences.ResolveAsync(LanguageNames.CSharp, CancellationToken.None);
  115| 
  116|         CSharpCompilation compilation = CSharpCompilation.Create(
  117|             assemblyName: "CodeCoverageExclusionTests",
  118|             syntaxTrees: [CSharpSyntaxTree.ParseText(source, new CSharpParseOptions(LanguageVersion.Latest))],
  119|             references: frameworkReferences.Concat(ReferencesHelper.GetReferences(ReferencesSet.MessagePack)),
  120|             options: new CSharpCompilationOptions(OutputKind.DynamicallyLinkedLibrary));
  121| 
  122|         var driver = CSharpGeneratorDriver.Create(new MessagePackGenerator());
  123|         driver = (CSharpGeneratorDriver)driver.RunGeneratorsAndUpdateCompilation(compilation, out _, out _);
  124|         GeneratorDriverRunResult result = driver.GetRunResult();
  125| 
  126|         return result.GeneratedTrees
  127|             .Select(tree => (tree.FilePath, tree.GetText().ToString()))
  128|             .ToList();
  129|     }
  130| }
```

### src/MessagePack.SourceGenerator/Transforms/CompositeResolverTemplate.tt at base (32258fdb), full file
```
    1| <#@ template debug="false" hostspecific="false" linePragmas="false" language="C#" #>
    2| 
    3| using MsgPack = global::MessagePack;
    4| 
    5| <# using (TransformUtilities.EmitNestingTypesAndNamespaces(this.ResolverName, this.Write)) { #>
    6| 
    7| partial class <#= ResolverName.Name #> : MsgPack::IFormatterResolver
    8| {
    9| 	public static readonly <#= ResolverName.Name #> Instance = new <#= ResolverName.Name #>();
   10| 
   11| 	private static readonly MsgPack::Formatters.IMessagePackFormatter[] formatterList = new MsgPack::Formatters.IMessagePackFormatter[]
   12| 	{
   13| <# foreach (string expr in FormatterInstanceExpressions) { #>
   14| 		<#= expr #>,
   15| <# } #>
   16| 	};
   17| 
   18| 	private static readonly MsgPack::IFormatterResolver[] resolverList = new MsgPack::IFormatterResolver[]
   19| 	{
   20| <# foreach (string expr in ResolverInstanceExpressions) { #>
   21| 		<#= expr #>,
   22| <# } #>
   23| 	};
   24| 
   25| 	private <#= ResolverName.Name #>() { }
   26| 
   27| 	public MsgPack::Formatters.IMessagePackFormatter<T> GetFormatter<T>()
   28| 	{
   29| 		return FormatterCache<T>.Formatter;
   30| 	}
   31| 
   32| 	static class FormatterCache<T>
   33| 	{
   34| 		internal static readonly MsgPack::Formatters.IMessagePackFormatter<T> Formatter;
   35| 
   36| 		static FormatterCache()
   37| 		{
   38| 			foreach (var formatter in formatterList)
   39| 			{
   40| 				if (formatter is MsgPack::Formatters.IMessagePackFormatter<T> f)
   41| 				{
   42| 					Formatter = f;
   43| 					return;
   44| 				}
   45| 			}
   46| 
   47| 			foreach (var resolver in resolverList)
   48| 			{
   49| 				var f = resolver.GetFormatter<T>();
   50| 				if (f != null)
   51| 				{
   52| 					Formatter = f;
   53| 					return;
   54| 				}
   55| 			}
   56| 		}
   57| 	}
   58| }
   59| 
   60| <# } #>
```

### src/MessagePack.SourceGenerator/Transforms/EnumTemplate.tt at base (32258fdb), full file
```
    1| ﻿<#@ template debug="false" hostspecific="false" linePragmas="false" language="C#" #>
    2| <#@ assembly name="System.Core" #>
    3| 
    4| using MsgPack = global::MessagePack;
    5| 
    6| <# using (this.EmitNestingTypesAndNamespaces(this.Write)) { #>
    7| 
    8| 	internal sealed class <#= Info.Formatter.Name #> : MsgPack::Formatters.IMessagePackFormatter<<#= Info.DataType.GetQualifiedName() #>>
    9| 	{
   10| 		public void Serialize(ref MsgPack::MessagePackWriter writer, <#= Info.DataType.GetQualifiedName() #> value, MsgPack::MessagePackSerializerOptions options)
   11| 		{
   12| 			writer.Write((<#= Info.UnderlyingTypeKeyword #>)value);
   13| 		}
   14| 
   15| 		public <#= Info.DataType.GetQualifiedName() #> Deserialize(ref MsgPack::MessagePackReader reader, MsgPack::MessagePackSerializerOptions options)
   16| 		{
   17| 			return (<#= Info.DataType.GetQualifiedName() #>)reader.Read<#= Info.UnderlyingTypeName #>();
   18| 		}
   19| 	}
   20| 
   21| <# } #>
```

### src/MessagePack.SourceGenerator/Transforms/FormatterTemplate.tt at base (32258fdb), full file
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
   48|   if (member == null) { #>
   49| 			writer.WriteNil();
   50| <# } else { #>
   51| 			<#= member.GetSerializeMethodString() #>;
   52| <# } #>
   53| <# } #>
   54| 		}
   55| 
   56| 		public <#= Info.DataType.GetQualifiedName(genericStyle: GenericParameterStyle.Identifiers) #> Deserialize(ref MsgPack::MessagePackReader reader, MsgPack::MessagePackSerializerOptions options)
   57| 		{
   58| 			if (reader.TryReadNil())
   59| 			{
   60| <# if (Info.IsClass) { #>
   61| 				return null;
   62| <# } else { #>
   63| 				throw new global::System.InvalidOperationException("typecode is null, struct not supported");
   64| <# } #>
   65| 			}
   66| 
   67| <# if (Info.MaxKey == -1 && !Info.HasIMessagePackSerializationCallbackReceiver) { #>
   68| 			reader.Skip();
   69| 			return new <#= Info.GetConstructorString()  #>;
   70| <# } else { #>
   71| 			options.Security.DepthStep(ref reader);
   72| <# if (isFormatterResolverNecessary) { #>
   73| 			MsgPack::IFormatterResolver formatterResolver = options.Resolver;
   74| <# } #>
   75| 			var length = reader.ReadArrayHeader();
   76| <# if (Info.MustDeserializeFieldsFirst) { 
   77| 	foreach (var member in Info.Members) { #>
   78| 			var <#= member.LocalVariableName #> = default(<#= member.Type #>);
   79| <#	}
   80| } else { #>
   81| 			var ____result = new <#= Info.GetConstructorString()  #>;
   82| <# } #>
   83| 
   84| 			for (int i = 0; i < length; i++)
   85| 			{
   86| 				switch (i)
   87| 				{
   88| <# for (var memberIndex = 0; memberIndex <= Info.MaxKey; memberIndex++) {
   89|   var member = Info.GetMember(memberIndex);
   90|   if (member == null) { continue; } #>
   91| 					case <#= member.IntKey #>:
   92| <# if (Info.MustDeserializeFieldsFirst) { #>
   93| 						<#= member.LocalVariableName #> = <#= member.GetDeserializeMethodString() #>;
   94| <# } else {
   95|   if (member.IsWritable) { #>
   96| 						<#= member.GetMemberAccess("____result") #> = <#= member.GetDeserializeMethodString() #>;
   97| <# } else { #>
   98| 						reader.Skip();
   99| <# } #>
  100| <# } #>
  101| 						break;
  102| <# } #>
  103| 					default:
  104| 						reader.Skip();
  105| 						break;
  106| 				}
  107| 			}
  108| 
  109| <# if (Info.MustDeserializeFieldsFirst) { #>
  110| 			var ____result = new <#= Info.GetConstructorString() #>;
  111| <# bool memberAssignExists = false;
  112|   for (var memberIndex = 0; memberIndex <= Info.MaxKey; memberIndex++) {
  113|   var member = Info.GetMember(memberIndex);
  114|   if (member == null || !member.IsWritable || member.IsInitOnly || member.IsRequired || Info.ConstructorParameters.Any(p => p.Equals(member))) { continue; }
  115|   memberAssignExists = true;#>
  116| 			if (length <= <#= memberIndex #>)
  117| 			{
  118| 				goto MEMBER_ASSIGNMENT_END;
  119| 			}
  120| 
  121| 			<#= member.GetMemberAccess("____result") #> = <#= member.LocalVariableName #>;
  122| <# } #>
  123| <# if (memberAssignExists) { #>
  124| 
  125| 		MEMBER_ASSIGNMENT_END:
  126| <# }
  127|  }
  128| 
  129|  if (Info.HasIMessagePackSerializationCallbackReceiver) {
  130|   if (Info.NeedsCastOnAfter) { #>
  131| 			((MsgPack::IMessagePackSerializationCallbackReceiver)____result).OnAfterDeserialize();
  132| <# } else { #>
  133| 			____result.OnAfterDeserialize();
  134| <# } #>
  135| <# } #>
  136| 			reader.Depth--;
  137| 			return ____result;
  138| <# } #>
  139| 		}
  140| 	}
  141| <# } #>
```

### src/MessagePack.SourceGenerator/Transforms/ResolverTemplate.tt at base (32258fdb), full file
```
    1| ﻿<#@ template debug="false" hostspecific="false" linePragmas="false" language="C#" #>
    2| <#@ assembly name="System.Core" #>
    3| <#@ import namespace="System.Linq" #>
    4| <#@ import namespace="System.Text" #>
    5| <#@ import namespace="System.Collections.Generic" #>
    6| 
    7| using MsgPack = global::MessagePack;
    8| 
    9| [assembly: MsgPack::Internal.GeneratedAssemblyMessagePackResolverAttribute(typeof(<#= this.ResolverName.GetQualifiedName(Qualifiers.Namespace) #>), <#= Version.Parse(ThisAssembly.AssemblyFileVersion).Major #>, <#= Version.Parse(ThisAssembly.AssemblyFileVersion).Minor #>)]
   10| 
   11| <# using (TransformUtilities.EmitNestingTypesAndNamespaces(this.ResolverName, this.Write)) { #>
   12| 
   13| /// <summary>A MessagePack resolver that uses generated formatters for types in this assembly.</summary>
   14| partial class <#= ResolverName.Name #> : MsgPack::IFormatterResolver
   15| {
   16| 	/// <summary>An instance of this resolver that only returns formatters specifically generated for types in this assembly.</summary>
   17| 	public static readonly MsgPack::IFormatterResolver Instance = new <#= ResolverName.Name #>();
   18| 
   19| 	private <#= ResolverName.Name #>()
   20| 	{
   21| 	}
   22| 
   23| 	public MsgPack::Formatters.IMessagePackFormatter<T> GetFormatter<T>()
   24| 	{
   25| 		return FormatterCache<T>.Formatter;
   26| 	}
   27| 
   28| 	private static class FormatterCache<T>
   29| 	{
   30| 		internal static readonly MsgPack::Formatters.IMessagePackFormatter<T> Formatter;
   31| 
   32| 		static FormatterCache()
   33| 		{
   34| 			var f = <#= ResolverName.Name #>GetFormatterHelper.GetFormatter(typeof(T));
   35| 			if (f != null)
   36| 			{
   37| 				Formatter = (MsgPack::Formatters.IMessagePackFormatter<T>)f;
   38| 			}
   39| 		}
   40| 	}
   41| 
   42| 	private static class <#= ResolverName.Name #>GetFormatterHelper
   43| 	{
   44| <#
   45|    var constructedRegistrations = ConstructedTypeRegistrations.ToArray();
   46|    if (constructedRegistrations.Length > 0) { #>
   47| 		private static readonly global::System.Collections.Generic.Dictionary<global::System.Type, int> closedTypeLookup = new global::System.Collections.Generic.Dictionary<global::System.Type, int>(<#= constructedRegistrations.Length #>)
   48| 		{
   49| <# for(var i = 0; i < constructedRegistrations.Length; i++) { #>
   50| 			{ typeof(<#= constructedRegistrations[i].DataType.GetQualifiedName(genericStyle: GenericParameterStyle.Arguments) #>), <#= i #> },
   51| <# } #>
   52| 		};
   53| <# }
   54|    var openGenericRegistrations = OpenGenericRegistrations.ToArray();
   55|    if (openGenericRegistrations.Length > 0) { #>
   56| 		private static readonly global::System.Collections.Generic.Dictionary<global::System.Type, int> openTypeLookup = new global::System.Collections.Generic.Dictionary<global::System.Type, int>(<#= openGenericRegistrations.Length #>)
   57| 		{
   58| <# for(var i = 0; i < openGenericRegistrations.Length; i++) { #>
   59| 			{ typeof(<#= openGenericRegistrations[i].DataType.GetQualifiedName(genericStyle: GenericParameterStyle.TypeDefinition) #>), <#= i #> },
   60| <# } #>
   61| 		};
   62| <# } #>
   63| 
   64| 		internal static object GetFormatter(global::System.Type t)
   65| 		{
   66| <# if (constructedRegistrations.Length > 0) { #>
   67| 			if (closedTypeLookup.TryGetValue(t, out int closedKey))
   68| 			{
   69| 				switch (closedKey)
   70| 				{
   71| <# for(var i = 0; i < constructedRegistrations.Length; i++) { var x = constructedRegistrations[i]; #>
   72| 					case <#= i #>: return <#= x.GetFormatterInstanceForResolver() #>;
   73| <# } #>
   74| 					default: return null; // unreachable
   75| 				};
   76| 			}
   77| <# }
   78| 
   79|    if (openGenericRegistrations.Length > 0) { #>
   80| 			if (t.IsGenericType && openTypeLookup.TryGetValue(t.GetGenericTypeDefinition(), out int openKey))
   81| 			{
   82| 				switch (openKey)
   83| 				{
   84| <#     for(var i = 0; i < openGenericRegistrations.Length; i++) { var x = openGenericRegistrations[i]; #>
   85| 					case <#= i #>: return global::System.Activator.CreateInstance(typeof(<#= x.GetFormatterNameForResolver(GenericParameterStyle.TypeDefinition) #>).MakeGenericType(t.GenericTypeArguments));
   86| <#     } #>
   87| 					default: return null; // unreachable
   88| 				};
   89| 			}
   90| <# } #>
   91| 
   92| 			return null;
   93| 		}
   94| 	}
   95| }
   96| 
   97| <# } #>
```

### src/MessagePack.SourceGenerator/Transforms/StringKey/StringKeyFormatterTemplate.tt at base (32258fdb), full file
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
   18| 	internal sealed class <#= Info.Formatter.GetQualifiedName(Qualifiers.None) #> : global::MessagePack.Formatters.IMessagePackFormatter<<#= Info.DataType.GetQualifiedName() #>>
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
   52| 			((global::MessagePack.IMessagePackSerializationCallbackReceiver)value).OnBeforeSerialize();
   53| <# } else { #>
   54| 			value.OnBeforeSerialize();
   55| <# } #>
   56| <# } #>
   57| 			writer.WriteMapHeader(<#= list.Count #>);
   58| <# foreach (var memberAndBinary in list) {
   59| 		var member = memberAndBinary.Item1; #>
   60| 			writer.WriteRaw(GetSpan_<#= member.UniqueIdentifier #>());
   61| 			<#= member.GetSerializeMethodString() #>;
   62| <# } #>
   63| 		}
   64| 
   65| 		public <#= Info.DataType.GetQualifiedName() #> Deserialize(ref global::MessagePack.MessagePackReader reader, global::MessagePack.MessagePackSerializerOptions options)
   66| 		{
   67| 			if (reader.TryReadNil())
   68| 			{
   69| <# if (Info.IsClass) { #>
   70| 				return null;
   71| <# } else { #>
   72| 				throw new global::System.InvalidOperationException("typecode is null, struct not supported");
   73| <# } #>
   74| 			}
   75| 
   76| <# if (Info.Members.Length == 0) { #>
   77| 			reader.Skip();
   78| 			var ____result = new <#= Info.GetConstructorString() #>;
   79| <# } else { #>
   80| 			options.Security.DepthStep(ref reader);
   81| <# if (isFormatterResolverNecessary) { #>
   82| 			var formatterResolver = options.Resolver;
   83| <# } #>
   84| 			var length = reader.ReadMapHeader();
   85| <# if (Info.MustDeserializeFieldsFirst) {
   86| 	foreach (var member in Info.Members.Where(x => x.IsWritable || Info.ConstructorParameters.Any(p => p.Equals(x)))) {
   87| 		// Until C# allows for optionally setting init-only properties (https://github.com/dotnet/csharplang/issues/6117)
   88| 		// we will unconditionally set them, and thus have no reason to track whether the local variable has been initialized.
   89| 		if (!member.IsInitOnly && !member.IsRequired && !Info.ConstructorParameters.Any(p => p.Equals(member))) { #>
   90| 			var <#= member.LocalVariableName #>IsInitialized = false;
   91| <#		} #>
   92| 			var <#= member.LocalVariableName #> = default(<#= member.Type #>);
   93| <#	} #>
   94| <# } else { #>
   95| 			var ____result = new <#= Info.GetConstructorString() #>;
   96| <# } #>
   97| 
   98| 			for (int i = 0; i < length; i++)
   99| 			{
  100| 				var stringKey = global::MessagePack.Internal.CodeGenHelpers.ReadStringSpan(ref reader);
  101| 				switch (stringKey.Length)
  102| 				{
  103| 					default:
  104| 					FAIL:
  105| 					  reader.Skip();
  106| 					  continue;
  107| <#= StringKeyFormatterDeserializeHelper.Classify(Info, "					", !Info.MustDeserializeFieldsFirst) #>
  108| 				}
  109| 			}
  110| 
  111| <# if (Info.MustDeserializeFieldsFirst) { #>
  112| 			var ____result = new <#= Info.GetConstructorString() #>;
  113| <# foreach (var member in Info.Members.Where(x => x.IsWritable && !x.IsInitOnly && !x.IsRequired && !Info.ConstructorParameters.Any(p => p.Equals(x)))) { #>
  114| 			if (<#= member.LocalVariableName #>IsInitialized)
  115| 			{
  116| 				<#= member.GetMemberAccess("____result") #> = <#= member.LocalVariableName #>;
  117| 			}
  118| 
  119| <# } #>
  120| <# } #>
  121| <# } #>
  122| <# if (Info.HasIMessagePackSerializationCallbackReceiver) {
  123| 		if (Info.NeedsCastOnAfter) { #>
  124| 			((global::MessagePack.IMessagePackSerializationCallbackReceiver)____result).OnAfterDeserialize();
  125| <# } else { #>
  126| 			____result.OnAfterDeserialize();
  127| <# } #>
  128| <# } #>
  129| <# if (Info.Members.Length != 0) { #>
  130| 			reader.Depth--;
  131| <# } #>
  132| 			return ____result;
  133| 		}
  134| 	}
  135| 
  136| <# } #>
```

### src/MessagePack.SourceGenerator/Transforms/TransformUtilities.cs at base (32258fdb), around the changed lines
```
  ... lines 1-24 not shown ...
   25| 
   26|                 // Start with outer-most type.
   27|                 if (nestingType.Container is not null)
   28|                 {
   29|                     reverseAction.Push(EmitNestingTypesAndNamespaces(nestingType.Container, writer));
   30|                 }
   31| 
   32|                 var kind = nestingType.Kind switch
   33|                 {
   34|                     TypeKind.Class when nestingType.IsRecord => "record", // C# 9 doesn't want to see `record class`.
   35|                     TypeKind.Class => "class",
   36|                     TypeKind.Struct when nestingType.IsRecord => "record struct",
   37|                     TypeKind.Struct => "struct",
   38|                     TypeKind.Interface => "interface",
   39|                     _ => throw new NotSupportedException("Unsupported kind: " + nestingType.Kind),
   40|                 };
   41| 
   42|                 var accessModifier = nestingType.AccessModifier switch
   43|                 {
   44|                     Accessibility.Public => "public",
   45|                     Accessibility.Internal => "internal",
   46|                     Accessibility.Private => "private",
   47|                     _ => null,
   48|                 };
   49|                 if (accessModifier is not null)
   50|                 {
   51|                     writer(accessModifier);
   52|                     writer($" ");
   53|                 }
   54| 
   55|                 writer($"partial {kind} {nestingType.GetQualifiedName(Qualifiers.None, GenericParameterStyle.Identifiers)}");
   56|                 bool anyConstraints = EmitTypeConstraints(nestingType, writer, leadingLineFeedIfAny: true);
   57| 
   58|                 writer(anyConstraints ? "{" : " {\r\n");
   59|                 reverseAction.Push(new DisposeAction(() => writer("}\r\n")));
   60| 
   61|                 return new DisposeAction(() =>
   62|                 {
   63|                     while (reverseAction.Count > 0)
   64|                     {
   65|                         reverseAction.Pop()?.Dispose();
   66|                     }
   67|                 });
   68|             default:
   69|                 throw new NotSupportedException();
   70|         }
   71|     }
   72| 
   73|     internal static bool EmitTypeConstraints(QualifiedNamedTypeName target, Action<string> writer, bool leadingLineFeedIfAny = false)
   74|     {
   75|         bool anyConstraints = false;
   76|         foreach (GenericTypeParameterInfo typeParameter in target.TypeParameters)
   77|         {
   78|             if (typeParameter.HasConstraints)
   79|             {
   80|                 if (leadingLineFeedIfAny && !anyConstraints)
   81|                 {
   82|                     writer("\r\n");
   83|                 }
   84| 
   85|                 anyConstraints = true;
   86|                 writer($"\t\twhere {typeParameter.Name} : {typeParameter.Constraints}\r\n");
   87|             }
   88|         }
   89| 
   90|         return anyConstraints;
   91|     }
  ... lines 92-136 not shown ...
```

### src/MessagePack.SourceGenerator/Transforms/UnionTemplate.tt at base (32258fdb), around the changed lines
```
    1| ﻿<#@ template debug="false" hostspecific="false" linePragmas="false" language="C#" #>
    2| <#@ assembly name="System.Core" #>
    3| <#@ import namespace="System.Linq" #>
    4| <#@ import namespace="System.Text" #>
    5| <#@ import namespace="System.Collections.Generic" #>
    6| 
    7| using MsgPack = global::MessagePack;
    8| 
    9| <# using (this.EmitNestingTypesAndNamespaces(this.Write)) { #>
   10| 	internal sealed class <#= Info.Formatter.GetQualifiedName(Qualifiers.None) #>: MsgPack::Formatters.IMessagePackFormatter<<#= Info.DataType.GetQualifiedName() #>>
   11| 	{
   12| 		private readonly global::System.Collections.Generic.Dictionary<global::System.RuntimeTypeHandle, global::System.Collections.Generic.KeyValuePair<int, int>> typeToKeyAndJumpMap;
   13| 		private readonly global::System.Collections.Generic.Dictionary<int, int> keyToJumpMap;
   14| 
   15| 		public <#= Info.Formatter.Name #>()
   16| 		{
   17| 			this.typeToKeyAndJumpMap = new global::System.Collections.Generic.Dictionary<global::System.RuntimeTypeHandle, global::System.Collections.Generic.KeyValuePair<int, int>>(<#= Info.SubTypes.Length #>, MsgPack::Internal.RuntimeTypeHandleEqualityComparer.Default)
   18| 			{
   19| <# for(var i = 0; i < Info.SubTypes.Length; i++) { var item = Info.SubTypes[i]; #>
   20| 				{ typeof(<#= item.Type #>).TypeHandle, new global::System.Collections.Generic.KeyValuePair<int, int>(<#= item.Key #>, <#= i #>) },
   21| <# } #>
   22| 			};
   23| 			this.keyToJumpMap = new global::System.Collections.Generic.Dictionary<int, int>(<#= Info.SubTypes.Length #>)
   24| 			{
   25| <# for(var i = 0; i < Info.SubTypes.Length; i++) { var item = Info.SubTypes[i]; #>
   26| 				{ <#= item.Key #>, <#= i #> },
   27| <# } #>
   28| 			};
   29| 		}
   30| 
   31| 		public void Serialize(ref MsgPack::MessagePackWriter writer, <#= Info.DataType.GetQualifiedName() #> value, MsgPack::MessagePackSerializerOptions options)
   32| 		{
   33| 			global::System.Collections.Generic.KeyValuePair<int, int> keyValuePair;
   34| 			if (value != null && this.typeToKeyAndJumpMap.TryGetValue(value.GetType().TypeHandle, out keyValuePair))
   35| 			{
   36| 				writer.WriteArrayHeader(2);
   37| 				writer.WriteInt32(keyValuePair.Key);
   38| 				switch (keyValuePair.Value)
   39| 				{
   40| <# for(var i = 0; i < Info.SubTypes.Length; i++) { var item = Info.SubTypes[i]; #>
   41| 					case <#= i #>:
   42| 						MsgPack::FormatterResolverExtensions.GetFormatterWithVerify<<#= item.Type #>>(options.Resolver).Serialize(ref writer, (<#= item.Type #>)value, options);
  ... lines 43-93 not shown ...
```

## What you did NOT get (refuse anything that depends on it)
- the contents and diffs of 228 generated files (listed above by name only)
- src/MessagePack.SourceGenerator/Transforms/TransformUtilities.cs at base: only ±30 lines around the changes (the full file did not fit the budget)
- src/MessagePack.SourceGenerator/Transforms/UnionTemplate.tt at base: only ±30 lines around the changes (the full file did not fit the budget)
- README.md: diff only, full file not provided (doc)
- the upstream issue page itself (only its URL); other files of the repository; build and test logs (only the facts.json summaries)

Return only the JSON object described in the brief.