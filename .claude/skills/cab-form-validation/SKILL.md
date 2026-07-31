---
name: cab-form-validation
description: Validates a Change Request's written description/form fields against the mandatory CR form structure (Business Justification, Problem Statement, Proposed Solution, Expected Outcomes, Consumer/Stakeholder Impact, Implementation Details, Testing Evidence, Supporting Documents). Use this for every single CR readiness check, infrastructure or application, before or alongside the module-specific checklist — it's the baseline layer. Trigger on "check this CR description", "is my CR form complete", "validate CR fields", or as a sub-step invoked by cab-orchestrator.
---

# CR Form Validation (Module 3)

This is the baseline layer of the AI CAB Readiness Agent: it grades the CR's
own description/form-field text, independent of whether the CR is an
infrastructure or application change. Every readiness check runs this module.

## Checklist source

The full 8-row checklist table lives in `references/module-3-checklist.md` —
read it before evaluating. Do not inline it here or duplicate it elsewhere.

## How to evaluate

For each row in the checklist:

1. Read the corresponding CR field/section (title, description, business
   justification, implementation plan, test cases, back-out plan, attached
   supporting documents — map each row to whichever field(s) hold that
   content in the CR record).
2. Decide a status: `complete`, `partial`, or `missing`.
   - **Do not rubber-stamp non-empty text as `complete`.** Boilerplate,
     placeholder text ("TBD", "N/A", a single generic sentence), or text
     clearly too thin to satisfy the requirement counts as `partial` or
     `missing`, even though the field is technically non-empty.
   - `missing` = the field is empty or entirely absent.
   - `partial` = present but thin/boilerplate/incomplete.
   - `complete` = the field substantively satisfies the stated requirement.
3. Emit one area entry per row in the shared output contract shape (see
   `cab-orchestrator`'s `references/orchestration-logic.md` for the exact
   JSON shape all skills feed into).

## Scoring

Read `state_scores` and `default_area_weight` from `../../../rubrics/scoring-config.json`
— never hardcode these values here. This module has no conditional rows
(unlike Module 2); every area always applies.

## PII/PHI guardrail

This module's rows are CR-text fields, not document uploads, so PII
detection here is lower-priority than Module 1 item 4 / Module 2 item 2 —
but if business-justification or description text appears to contain
identifiable data (names + SSNs, Aadhaar, PAN, card numbers, etc.), flag the
**category only** in `notes`, never the actual matched value.
