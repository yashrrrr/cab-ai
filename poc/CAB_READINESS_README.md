# AI CAB Readiness Agent — Handoff

This document covers the **CAB Readiness Agent** feature: 4 Claude Skills plus a
deterministic backend/frontend implementation that score a Change Request's
document and approval completeness against fixed checklists.

This is **separate** from the pre-existing "AI CAB" deliberation feature
(`poc/backend/cab_orchestrator.py`, the 5-persona Approve/Reject debate wired to
`POST /rfc/{rfc_id}/trigger-cab`). That feature renders a decision recommendation.
This feature renders a *readiness score* — "is this RFC's paperwork complete
enough to go in front of CAB at all" — and never makes an approve/reject call.
They share nothing except living in the same app; both can be run independently
on the same RFC.

## Where things live

| Concern | Location |
|---|---|
| Claude Skills (interactive, markdown) | `.claude/skills/cab-form-validation/`, `.claude/skills/cab-infra-review/`, `.claude/skills/cab-app-review/`, `.claude/skills/cab-orchestrator/` |
| Checklist source-of-truth tables | `.claude/skills/*/references/module-*-checklist.md`, `.claude/skills/cab-orchestrator/references/orchestration-logic.md` |
| Scoring/approver config (JSON, shared) | `rubrics/scoring-config.json`, `rubrics/approvers.json` |
| Deterministic Python re-implementation used by the API | `poc/backend/cab_readiness.py` |
| API endpoint | `POST /api/cab/evaluate` in `poc/backend/main.py` |
| Frontend panel | `CabReadinessPanel` in `poc/frontend/src/App.jsx` (+ styles in `App.css` under "CAB Readiness Agent panel") |
| LLM client (shared gateway, new) | `poc/backend/llm_gateway.py` |
| PII/PHI category-only detector (new) | `poc/backend/pii_guardrail.py` |
| Real vendor/reviewer templates land here later | `.claude/skills/cab-infra-review/assets/templates/<area-slug>/`, `.claude/skills/cab-app-review/assets/templates/<area-slug>/` (currently just `README.md` + `.gitkeep` placeholders) |

## Known duplication — checklist content lives in two places

The Claude Skills are markdown instructions meant for an interactive Claude Code
session; the API endpoint needs deterministic, callable Python. Rather than
parsing markdown tables at runtime, `poc/backend/cab_readiness.py` encodes the
same checklist rows (area names, requirements, required-approver keys,
`[VERIFY]` flags, conditional flags) as Python constants:
`MODULE_1_CHECKLIST`, `MODULE_2_CHECKLIST`, `MODULE_3_CHECKLIST`.

**If the real checklist content changes, both places must be updated together:**
1. `.claude/skills/{cab-form-validation,cab-infra-review,cab-app-review}/references/module-*-checklist.md`
2. The matching `MODULE_*_CHECKLIST` constant in `poc/backend/cab_readiness.py`

Scoring weights/thresholds and approver name lists are **not** duplicated —
both the skills (via `cab-orchestrator`'s reference doc) and
`cab_readiness.py` read the same `rubrics/scoring-config.json` and
`rubrics/approvers.json` files directly. Update the rubric there once; no code
change needed for weight/threshold/approver-name edits alone (only for
structural checklist changes — new/removed areas, changed conditions, etc.).

## Open `[VERIFY]` items

Currently one, carried over verbatim from the source brief and never resolved
by recon since no further source material was available:

- **Module 1 (Infrastructure), Area 1 — Architecture Review.** The required
  approver for this specific checklist row is not explicit in the source
  table. `rubrics/approvers.json`'s `architecture_review` key currently holds
  a placeholder: `"TODO(criteria): approver not explicit in source table for
  Module 1 item 1 — verify"`. The checklist row itself
  (`.claude/skills/cab-infra-review/references/module-1-checklist.md` and the
  matching `MODULE_1_CHECKLIST` entry in `cab_readiness.py`) is marked
  `verify_flag: True`, so it always surfaces in the API response's
  `openVerificationItems` array and in the frontend panel's `[VERIFY]` badge
  until a real approver is supplied and this flag is removed from both places.

## Recon assumptions (stand-ins for missing information)

These were necessary judgment calls made during implementation, not requirements
from the brief. Revisit them once real data/policy is available:

- **Legacy document migration** — RFCs that existed before the `rfc_documents`
  table was added get a single backfilled row with `category = 'other'`
  (see `migrate_db()` in `poc/backend/db_init.py`). There was no way to
  retroactively know what category those older single-document uploads were.
- **Pre-existing RFCs have `cr_type = NULL`** — for any RFC submitted before the
  CR-type field existed, `cab_readiness.determine_cr_type()` falls back to an
  LLM classification call over the RFC's title/description and reports
  `crTypeSource: "inferred"` in the API response, distinct from
  `crTypeSource: "confirmed"` for RFCs where the requestor explicitly picked a
  type at submission time. Inferred classification defaults to `"mixed"`
  (evaluates both Module 1 and Module 2) if the LLM call is inconclusive or
  unavailable, since that's the safer over-inclusive failure mode for a
  readiness gate.
- **PII/PHI detection is heuristic, not production DLP** — `pii_guardrail.py`
  uses a small set of regexes (SSN-like, Aadhaar-like, PAN-like, card-number-like,
  email address) and reports **category + count only**, never the matched
  value, in API responses, cached DB rows, or logs. This satisfies the brief's
  "flag category, never persist/log the value" requirement for a PoC. It is
  not a substitute for a real DLP/PII scanning product and will both
  under- and over-match on real-world documents.
- **Conditional area detection (Module 2)** — the three conditional rows
  (AI Architecture Alignment, Vendor Involvement, Cloud Subscription Hosting)
  use a keyword-heuristic check (`_condition_applies()` in `cab_readiness.py`)
  against the RFC's title/description text, not a real classifier. A
  condition that doesn't match is scored `not_applicable`, not `missing`, so
  it never penalizes the RFC — but a genuinely-applicable condition phrased in
  unexpected words could be missed. Worth revisiting if this becomes more than
  a PoC.
- **Thin/boilerplate text is not auto-approved** — LLM-based per-area
  classification (`_classify_text()`) is explicitly instructed not to mark a
  field "complete" just because it's non-empty (e.g. a `test_cases` value of
  `"Tested."` alone is correctly scored as not complete). This is a prompting
  choice, not a hard rule — genuinely terse-but-sufficient text could still be
  misjudged either way since it depends on the gateway's live model output.
- **Multi-file extracted-field conflicts** — when a requestor uploads multiple
  documents at submission time, if more than one contains an auto-extractable
  field (e.g. affected systems), the last-processed file's extracted value
  wins. This is acceptable for a PoC and is not surfaced as a conflict to the
  requestor.

## LLM Gateway configuration

`poc/backend/llm_gateway.py` is used only by this feature (the pre-existing AI
CAB deliberation feature keeps using its own OpenAI-SDK-via-GitHub-Models
client, untouched). Config is read in this order:

1. Real environment variables: `LLM_GATEWAY_BASE_URL`, `LLM_GATEWAY_API_KEY`,
   `LLM_GATEWAY_PEM_PATH`, `LLM_GATEWAY_PEM_MODE`, `LLM_GATEWAY_MODEL`.
2. Fallback: parsed from a gitignored `.env.llm` file at the **repository
   root** (sibling to `poc/`, not inside it) — same key names. This file
   already existed in the repo before this feature was built (see
   `test_llm_gateway.py` and `check-usage.py` at repo root) and holds the real
   credentials; nothing needed to be duplicated into `poc/.env` or committed.

`poc/.env.example` documents the same variable names with blank placeholder
values, for anyone setting up a fresh environment without access to the
existing `.env.llm`.

A failed or unreachable LLM call never raises or blocks the evaluation — it
degrades to a `partial` status for that specific area with a note that
evaluation was unavailable, so one gateway hiccup never fails an entire CAB
readiness check.

## Trying it out

Two fixture RFCs are seeded by `poc/backend/db_init.py`'s
`insert_cab_readiness_fixtures()` (run automatically as part of
`python poc/backend/db_init.py`):

- `rfc-cab-infra-001` — `cr_type: infrastructure`, has an architecture-diagram
  document (with an embedded fixture-only, clearly-labeled placeholder
  SSN-shaped string to exercise the PII guardrail — not a real identifier) but
  no DPIA document, to show a mix of complete/missing areas.
- `rfc-cab-app-002` — `cr_type: application`, has a thin one-word
  `test_cases` value and a VAPT report document, to show the
  "non-empty text ≠ automatically complete" rule alongside a genuinely
  complete area.

From either RFC's detail page in the frontend, click **Check CAB Readiness**
to run a live evaluation, or call the endpoint directly:

```
POST /api/cab/evaluate
{"rfc_id": "rfc-cab-infra-001"}
```
