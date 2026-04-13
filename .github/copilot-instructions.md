# GitHub Copilot Instructions

## Source of truth

Use `specs_EN.md` as the primary reference for:

* system architecture
* file organization
* business rules
* constraints and expected behaviors

If there is a conflict between local code and `specs_EN.md`, prefer `specs_EN.md` unless explicitly instructed otherwise.

## Coding principles

* Preserve the architecture and file structure defined in `specs_EN.md`
* Do NOT move logic to a different layer unless explicitly required
* Do NOT introduce new patterns inconsistent with the spec
* Prefer small, safe, incremental changes over large rewrites
* All Python code must be PEP8-compliant

## Architecture rules

* Follow the file organization defined in `specs_EN.md`
* Keep responsibilities clearly separated (no mixing layers)
* Keep business logic in the intended layer (as described in `specs_EN.md`)
* Avoid hidden side effects and implicit dependencies

## When fixing review comments

* Treat Gemini review comments as requiring a concrete end-state, not a minimal cosmetic patch
* Implement the smallest fix that fully resolves the review comment
* Always ensure the fix is compliant with `specs_EN.md`
* Do NOT “fix” an issue by violating architecture
* If the review comment conflicts with `specs_EN.md`, explain why and do NOT blindly apply it
* When a comment points to architecture, fix the ownership of the logic, not only the local symptom
* Add or update tests that prove the issue is resolved

## Repository-wide fix policy

* When a review comment identifies a problem, do not fix only the local occurrence
* Search the codebase for the same or closely related pattern (i.e., the same class of issue)
* Before applying changes, identify and list all relevant occurrences
* If the same class of issue exists elsewhere, prefer a repository-wide fix that resolves the whole pattern in one pass
* Normalize repeated implementations toward one consistent, architecture-compliant solution aligned with `specs_EN.md`
* Apply broad fixes only where the logic and risk are genuinely the same; avoid blind mechanical replacements
* Add or update tests for both the reported case and the other affected occurrences

## Strict DRY policy

* Enforce DRY strictly
* Do not duplicate business logic, validation, error handling, mapping logic, retry protection, or policy rules
* If logic is repeated, consolidate it into the correct shared abstraction
* Prefer one authoritative implementation per behavior
* Remove redundant copies when a shared implementation is introduced
* Do not create artificial abstractions for code that is only superficially similar

## Reliability

* Handle edge cases (null, empty, retries, concurrency)
* Preserve backward compatibility unless explicitly broken
* Validate inputs and handle errors explicitly

## Testing

* Any behavior change must include tests
* Prefer tests that prove correctness (not just coverage)
* Cover edge cases mentioned in `specs_EN.md`

## Before suggesting a change

Check:

* Is this aligned with `specs_EN.md`?
* Does it break architecture?
* Are tests needed?
* Could this introduce regression?


## Advanced code risk scanning

When analyzing or modifying code, proactively scan for the following classes of issues across the codebase, not just in the modified lines.

### Performance and scalability
- Identify functions that do not scale with large inputs (e.g. O(n²) patterns, repeated loops, unbounded memory growth)
- Flag inefficient data structures or unnecessary recomputations
- Propose optimized implementations where relevant
- Ensure fixes remain compliant with `specs_EN.md`

### Data isolation and access control
- Detect violations of data separation boundaries
- Identify any unintended data access, leakage, or cross-domain coupling
- Flag bypasses of intended access control or domain isolation rules
- Ensure strict adherence to data ownership and boundaries defined in `specs_EN.md`

### Memory safety
- Identify potential memory leaks (e.g. retained references, unbounded caches, missing cleanup, long-lived objects)
- Flag resource mismanagement (files, connections, handles, async tasks)
- Propose safe lifecycle management patterns

### Deprecated usage
- Detect usage of deprecated functions, APIs, or patterns
- Propose modern, supported alternatives
- Ensure migration does not break backward compatibility unless explicitly intended

### Thread safety and concurrency
- Identify non-thread-safe operations (shared mutable state, race conditions, missing locks or guards)
- Detect unsafe async usage or concurrency issues
- Propose safe synchronization or isolation strategies

### Extensibility and hard-coded behavior
- Detect hard-coded parameters, constants, or logic that should be configurable or extensible
- Propose abstractions or configuration mechanisms where appropriate
- Avoid premature abstraction: only generalize when the intent is clear

### Undefined behavior and unsafe assumptions
- Identify code paths that may lead to undefined, unsafe, or unpredictable behavior
- Flag unsafe assumptions about input validity, object state, initialization order, lifetimes, nullability, bounds, casting, or external system responses
- Detect missing guards around invalid states, partial states, or unexpected transitions
- Prefer explicit validation, defensive checks, and well-defined failure modes over implicit assumptions
- Ensure behavior remains deterministic and well-bounded under invalid, extreme, or unexpected inputs
- Propose fixes that make the behavior explicit, safe, and testable

## Expected behavior
- Do not only flag issues — propose concrete fixes whenever possible
- Prefer repository-wide fixes when the same issue appears multiple times
- Keep fixes minimal but complete
- Ensure all fixes remain compliant with `specs_EN.md`
- Add or update tests when behavior or risk is involved
- When multiple risk categories overlap, prioritize the fix that reduces systemic risk rather than local issues