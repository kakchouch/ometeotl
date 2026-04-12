# GitHub Copilot Instructions

## Source of truth
Use `specs_EN.md` as the primary reference for:
- system architecture
- file organization
- business rules
- constraints and expected behaviors

If there is a conflict between local code and SPEC_en.md, prefer SPEC_en.md unless explicitly instructed otherwise.

## Coding principles
- Preserve the architecture and file structure defined in SPEC_en.md
- Do NOT move logic to a different layer unless explicitly required
- Do NOT introduce new patterns inconsistent with the spec
- Prefer small, safe, incremental changes over large rewrites

## Architecture rules
- Follow the file organization defined in SPEC_en.md
- Keep responsibilities clearly separated (no mixing layers)
- Keep business logic in the intended layer (as described in SPEC_en.md)
- Avoid hidden side effects and implicit dependencies

## When fixing review comments
- Always ensure the fix is compliant with SPEC_en.md
- Do NOT “fix” an issue by violating architecture
- Prefer a slightly larger but correct fix over a quick hack
- If the review comment conflicts with SPEC_en.md, explain why and do NOT blindly apply it

## Reliability
- Handle edge cases (null, empty, retries, concurrency)
- Preserve backward compatibility unless explicitly broken
- Validate inputs and handle errors explicitly

## Testing
- Any behavior change must include tests
- Prefer tests that prove correctness (not just coverage)
- Cover edge cases mentioned in SPEC_en.md

## Before suggesting a change
Check:
- Is this aligned with SPEC_en.md?
- Does it break architecture?
- Are tests needed?
- Could this introduce regression?