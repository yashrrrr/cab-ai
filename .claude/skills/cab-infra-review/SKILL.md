---
name: cab-infra-review
description: Evaluates an Infrastructure Change Request's attached documents and approvals against the Module 1 CAB checklist — architecture review sign-off, cloud deployment/subscription budget approval, Acceptable Usage Policy review, Data Privacy Impact Assessment (when PII/PHI involved), internal UST system integration approvals, client system integration alignment, vendor/hosted-infrastructure approval, and supporting architecture documentation. Use whenever a CR is flagged or classified as an infrastructure change, or when asked to "check infra CAB readiness" / "validate this infrastructure change request". Run alongside cab-form-validation; feed results to cab-orchestrator.
---

# Infrastructure CR Review (Module 1)

## Checklist source

The full 8-row checklist table lives in `references/module-1-checklist.md` —
read it before evaluating. It includes a `[VERIFY]` flag on row 1's required
approver; **do not resolve this yourself** — carry it through unchanged and
surface it in the orchestrator's `openVerificationItems` output.

## How to evaluate

For each row in the checklist:

1. Match the row's requirement against the CR's attached documents (use the
   document's `category` tag when available — e.g. `architecture_diagram`,
   `dpia`, `vapt_report` — to narrow which uploaded file is evidence for
   this area; fall back to reading all attached documents when no category
   narrows it down) and against the required-approver list in
   `../../../rubrics/approvers.json`.
2. Decide a status: `complete`, `partial`, `missing`, or `not_applicable`.
   None of Module 1's rows are conditional in the way Module 2's are — all
   8 apply to every infrastructure CR — so `not_applicable` should be rare
   here (reserve it for a genuinely inapplicable edge case, and say why in
   `notes`).
3. Emit one area entry per row in the shared output contract shape (see
   `cab-orchestrator`'s `references/orchestration-logic.md`).

## Row 4 — Data Privacy Assessment: PII/PHI guardrail

This row exists specifically because infrastructure CRs may involve
PII/PHI. When evaluating it:

- Scan the CR's attached documents/text for indicators of personal data
  (references to storing/processing PII, PHI, customer records, etc.).
- **Never extract, log, display, or persist the actual sensitive values.**
  Flag only the *category* of indicator found (e.g. "this document appears
  to reference PII/PHI, so a DPIA is required") in the area's `notes` and
  in a `piiFlags` entry for the orchestrator to collect.
- If a DPIA document is attached (category `dpia`), check that it exists
  and appears substantive — the actual grading template for "what a
  correct DPIA looks like" is `TODO(template)`, not yet supplied. Until
  then, presence + non-trivial length is the best available signal; label
  the result as based on interim criteria.

## Scoring

Read `state_scores`, `default_area_weight`, and `module_status_thresholds`
from `../../../rubrics/scoring-config.json` — never hardcode these values
here.

## Templates

`assets/templates/` is currently empty (see its `README.md`) — the real
per-area reference templates (what a correct architecture diagram, DPIA,
etc. looks like) will be dropped in later. Until then, evaluate on
presence/substantiveness of the uploaded document rather than a template
diff, and label results accordingly.
