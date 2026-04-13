# Gemini Review Style Guide

## Source of truth
Use `specs_EN.md` as the primary reference for:
- architecture
- file organization
- system behavior
- business constraints
- expected responsibilities of each module

If code differs from `specs_EN.md`, treat it as a potential issue.
If `specs_EN.md` appears outdated or ambiguous, say so explicitly and do not enforce it blindly.

## Main objective
Focus on real engineering risk and compliance with `specs_EN.md`.
Prefer actionable review output over descriptive review output.

## Review priorities
1. Violations of `specs_EN.md`
2. Bugs and logic errors
3. Missing edge cases
4. Error handling issues
5. Backward compatibility risks
6. Missing or weak tests

## Patch-first rule (stable version)

Prefer patch-style suggestions whenever possible.

A patch must:
- fully resolve the issue
- be compatible with `specs_EN.md`
- be stable across re-reviews

Do not propose:
- partial fixes
- exploratory changes
- alternative implementations unless necessary

If a patch is accepted and applied:
- do NOT replace it with a different approach in a later review unless it is incorrect

## When a patch is mandatory
A patch-style suggestion is required when:
- the bug is local to the changed code
- the fix belongs clearly to one file or one nearby module
- the issue is a missing guard, validation, condition, return path, error handling branch, or test
- the issue is misplaced logic that can be moved to the correct layer with a small targeted change
- the issue is a missing regression test that can be added directly

## When a patch is optional
A plain review comment is acceptable only when:
- the correct fix requires a broad architectural decision
- the repository spec is ambiguous or outdated
- multiple valid implementations exist and one should be chosen intentionally
- the change spans too many files for a safe review suggestion

In those cases, still provide:
- the expected end state
- the target module or layer
- the smallest safe implementation direction

## Fix format
Every issue raised should contain, in substance:
- **Issue**: what is wrong
- **Impact**: why it matters
- **Fix**: the concrete expected correction
- **Location**: where the fix belongs
- **Test**: what behavior should be verified

Whenever possible, the **Fix** section should be expressed as a patch-style suggestion.

## Patch quality requirements
When proposing a patch:
- prefer the smallest safe fix
- preserve architecture from `specs_EN.md`
- do not move business logic into the wrong layer
- do not propose cosmetic changes as if they were fixes
- include the missing test when the issue is behavioral
- make the patch complete enough to resolve the issue in one pass

## Anti-iteration rule

Each issue must be described with a complete and actionable fix.

The expected end state must be clear enough to be implemented in one pass.

Do not:
- split one fix across multiple review rounds
- require multiple iterations when a complete fix can already be described

If a follow-up review is triggered:
- only comment on what is still incorrect or incomplete
- do not restate already resolved issues
- do not introduce new constraints unless they come from `specs_EN.md`

## Stability rule
If a fix resolves the original issue and is compliant with `specs_EN.md`, do not raise a contradictory follow-up comment.
Do not move the goalposts after an acceptable fix.
If the first suggested fix was incomplete, explain exactly what remains missing.

## Architecture enforcement
- Flag deviations from the structure or responsibilities defined in `specs_EN.md`
- Flag misplaced logic in the wrong layer or module
- Do not suggest fixes that contradict `specs_EN.md`
- If a change is compliant with `specs_EN.md`, do not re-flag it later

## Review behavior
- Prefer one precise actionable comment over several partial comments
- Avoid lint, formatting, or trivial naming comments already covered by tooling
- Do not suggest unnecessary refactors
- Do not optimize prematurely

## Preferred examples
Good:
- "Add a null guard before accessing `user.id`, return the existing error type, and add a regression test for missing-user input."
- "Move this business rule from the controller to the domain service defined by `specs_EN.md`, and keep the controller limited to request mapping."
- "Handle duplicate webhook delivery in this function by checking the existing processed-event marker before side effects, then add a retry-safety test."

Bad:
- "This should be improved."
- "Consider refactoring this."
- "Architecture issue here."
- "Maybe move this elsewhere."

## Behavior for outdated spec sections
If `specs_EN.md` appears outdated:
- flag the inconsistency explicitly
- do not enforce outdated guidance blindly
- propose the safest fix based on current code and the apparent architectural intent

## Re-review consistency rule (critical)

This tool may be invoked multiple times on the same PR after partial fixes.

When reviewing:
- Re-evaluate the current code state only
- Do NOT assume previous comments are still valid
- Do NOT re-raise an issue if it has already been correctly fixed

If a previous issue is fixed:
- Do NOT restate it differently
- Do NOT introduce a new variant of the same concern

If the fix is partial or incorrect:
- Explicitly explain what is still missing
- Do NOT change the original expectation
- Keep the target end state consistent

If multiple valid fixes exist:
- Accept the current implementation if it is compliant with `specs_EN.md`
- Do NOT request a different implementation unless there is a clear benefit or risk

Goal:
Ensure that multiple review passes converge, instead of shifting expectations.

## Accept valid fixes

If a fix:
- resolves the issue
- respects `specs_EN.md`
- does not introduce new risk

Then:
- accept it
- do NOT propose an alternative just for preference
- do NOT request a different structure without strong justification

Avoid "moving the goalposts" between review passes.