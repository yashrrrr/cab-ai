---
name: cab-app-review
description: Evaluates an Application Change Request's attached documents and approvals against the Module 2 CAB checklist — architecture review, data privacy alignment, AI architecture review (if AI components are involved), VAPT security report, test cases and sign-off, vendor SOP documentation, ISMS security impact assessment, BRD/FRD/flow/architecture/network diagrams, service-owner integration approvals, cross-team cloud subscription hosting approval, and CR change-justification completeness. Use whenever a CR is flagged or classified as an application change, or when asked to "check application CAB readiness" / "validate this app change request". Run alongside cab-form-validation; feed results to cab-orchestrator.
---

# Application CR Review (Module 2)

## Checklist source

The full 11-row checklist table lives in `references/module-2-checklist.md`
— read it before evaluating.

## How to evaluate

For each row in the checklist:

1. Match the row's requirement against the CR's attached documents (use the
   document's `category` tag when available to narrow which uploaded file
   is evidence — e.g. `vapt_report` for row 4, `test_signoff` for row 5,
   `brd_frd` for row 8 — falling back to reading all attached documents
   when no category narrows it down) and against the required-approver
   list in `../../../rubrics/approvers.json`.
2. Decide a status: `complete`, `partial`, `missing`, or `not_applicable`.

## Conditional rows

Rows 3, 6, and 10 are **conditional** — they only apply if the CR meets a
specific condition:

- **Row 3 (AI Architecture Alignment)** — only applies if the CR involves
  AI components.
- **Row 6 (Vendor Involvement)** — only applies if the CR involves vendor
  applications or vendors.
- **Row 10 (Cloud Subscription Hosting)** — only applies if the
  application is hosted in another team's cloud subscription.

Before scoring these three, run a lightweight "does this condition apply"
check by reading the CR's description/metadata for relevant keywords or
explicit flags. If the condition doesn't apply, mark the area
`not_applicable` (not `missing` — an inapplicable conditional row should
never drag the score down or appear in `missingMandatoryItems`). Record
`conditionApplies: false` on the area entry. If the condition does apply
but the evidence is absent, mark it `missing` as normal.

## Row 11 — overlap with Module 3

Row 11 (Change Justification) restates the same fields Module 3
(`cab-form-validation`) already grades (Business Justification, Problem
Statement, Proposed Solution, Expected Outcomes, Stakeholder/Consumer
Impact). **Don't double-penalize.** When both modules run (which is
always, per the orchestrator logic), either:

- Reuse Module 3's per-field verdicts directly for this row instead of
  re-evaluating from scratch, or
- If re-evaluating independently, clearly label this area's `notes` as
  overlapping with `module-3-form-validation` so the orchestrator/UI can
  present it without implying two independent failures for one gap.

## Row 2 — Data Privacy Alignment: PII/PHI guardrail

Same hard constraint as Module 1 row 4: detect and flag the **category**
of PII/PHI indicators only (e.g. "this document appears to reference
PII/PHI"). Never extract, log, display, or persist actual sensitive
values. Emit a `piiFlags` entry for the orchestrator to collect.

## Scoring

Read `state_scores`, `default_area_weight`, and `module_status_thresholds`
from `../../../rubrics/scoring-config.json` — never hardcode these values
here.

## Templates

`assets/templates/` is currently empty (see its `README.md`) — real
per-area reference templates land here later. Until then, evaluate on
presence/substantiveness of the uploaded document rather than a template
diff, and label results accordingly.
