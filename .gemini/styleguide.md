# Gemini Review Style Guide

## Source of truth
Use `specs_EN.md` as the primary reference for:
- architecture
- file organization
- system behavior
- constraints

If code differs from SPEC_en.md, treat it as a potential issue.

## Main objective
Focus on real engineering risk and SPEC compliance.
Avoid low-value or stylistic comments.

## Review priorities
1. Violations of SPEC_en.md (architecture or behavior)
2. Bugs and logic errors
3. Missing edge cases
4. Error handling issues
5. Backward compatibility risks
6. Missing or weak tests

## Architecture enforcement
- Flag any deviation from the file structure defined in SPEC_en.md
- Flag misplaced logic (wrong layer)
- Do NOT suggest fixes that contradict SPEC_en.md
- If a change is compliant with SPEC_en.md, do NOT re-flag it

## Review behavior
- Prefer high-signal comments over many comments
- Avoid repeating lint/formatting issues
- Do NOT suggest unnecessary refactors
- Do NOT optimize prematurely

## Comment format
Each comment should include:
- The problem
- Why it matters (impact)
- Reference to SPEC_en.md if relevant
- A concrete suggestion

## Stability rule (important)
- If a fix resolves a previous comment and is compliant with SPEC_en.md:
  → Do NOT raise a new contradictory comment

## Uncertainty handling
- If unsure, say it explicitly
- Do not assert speculative issues as facts