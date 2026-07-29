---
title: 'Environment-Staged Predecessor Gate (Dev -> QA -> Production)'
type: 'feature'
created: '2026-07-29'
status: 'done'
review_loop_iteration: 0
context: []
baseline_commit: '7b37ad0'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** The POC has no concept of `environment` on an RFC, so nothing stops an RFC from being created "in Production" or "in QA" without the corresponding lower-environment work having actually completed first, per brief section 3.4/5.4/17.1/17.2.

**Approach:** Add `environment` (Dev/QA/Production) and `environment_predecessor_rfc_id` columns to `change_requests`; enforce the gate with a real SQLite `BEFORE INSERT` trigger (`trg_environment_predecessor_gate`) so it can never be bypassed by any insert path, not just the `/rfc/submit` API; add a friendly pre-check in `main.py` for a clean 400 error; add a minimal "mark Completed" endpoint since the POC has no existing way to reach `Completed` status; extend the frontend submission form with the two new fields; add `test_guardrails.py` covering brief section 18.1 cases 9 and 10.

## Boundaries & Constraints

**Always:**
- Every RFC (all 5 types) carries `environment`; Emergency RFCs still carry it but are exempt from the predecessor check at every environment value.
- For non-Emergency types, QA requires a same-type Completed predecessor in Dev; Production requires a same-type Completed predecessor in QA. Check happens against the RFC's *final* classified type (after auto-classification / No-Impact-escalation), not the raw request.
- The gate is enforced in the SQLite schema itself (trigger), so it holds regardless of which code path performs the INSERT — not only through `main.py`.
- Existing classification/approval mechanics (Standard auto-approve, No Impact 2-tier, CAB routing) are unchanged.

**Ask First:** N/A — no items expected to require human judgment mid-implementation; if the SQLite trigger proves impractical for cross-row lookup, would ask before falling back to app-layer-only enforcement (ruled out during planning: trigger approach was verified working).

**Never:**
- Do not implement Open Question 7's "predecessor's PIR must also be complete" — explicitly out of scope/unresolved per the brief.
- Do not retrofit Section 5.3's guardrails (Standard/No-Impact enforcement) — out of scope, unrelated to this feature, not currently implemented in the POC.
- Do not change existing `change_type` classification/CAB logic.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Dev, any type | environment=Dev | Inserts freely, no predecessor needed | N/A |
| QA, non-Emergency, no valid predecessor | environment=QA, predecessor_id=null or predecessor not Completed/same-type/Dev | Insert rejected | 400 with clear detail; trigger raises IntegrityError as backstop |
| QA, non-Emergency, valid predecessor | predecessor same type, environment=Dev, status=Completed | Insert succeeds | N/A |
| Production, non-Emergency, valid QA predecessor | predecessor same type, environment=QA, status=Completed | Insert succeeds | N/A |
| Emergency, any environment | type=Emergency, environment=QA or Production, predecessor_id=null | Insert succeeds (bypass) | N/A |
| Predecessor type mismatch | predecessor exists, Completed, wrong type | Insert rejected | 400 / IntegrityError |

</frozen-after-approval>

## Code Map

- `poc/backend/db_init.py` -- add `environment`/`environment_predecessor_rfc_id` columns to `init_db`, migrate existing DBs in `migrate_db`, create/replace `trg_environment_predecessor_gate` trigger idempotently.
- `poc/backend/main.py` -- add `EnvironmentEnum`, extend `RFCSubmissionRequest`/`RFCResponse`, add pre-insert friendly validation + `IntegrityError` handling in `submit_rfc`, add `POST /rfc/{rfc_id}/complete` endpoint, include new fields in `get_rfc`.
- `poc/backend/guardrails.py` (new) -- `environment_predecessor_gate_error(cursor, environment, change_type, predecessor_rfc_id)` pure-ish helper used by `main.py` pre-check; single source of truth for the "one stage lower" mapping shared with tests.
- `poc/backend/test_guardrails.py` (new) -- covers brief 18.1 cases 9 & 10 against the real trigger + against `submit_rfc` via FastAPI TestClient.
- `poc/frontend/src/App.jsx` -- add `environment` select + `environment_predecessor_rfc_id` select to the submission form; add "Mark Completed" action in RFC detail view; surface `environment` on list/detail badges.

## Tasks & Acceptance

**Execution:**
- [x] `poc/backend/db_init.py` -- add columns + trigger -- data model + enforcement backbone
- [x] `poc/backend/guardrails.py` -- add gate-check helper -- shared logic for API pre-check and tests
- [x] `poc/backend/main.py` -- wire fields, pre-check, complete endpoint -- API surface
- [x] `poc/backend/test_guardrails.py` -- cases 9 & 10 -- regression coverage
- [x] `poc/frontend/src/App.jsx` -- form fields + mark-completed action -- minimal UI parity

**Acceptance Criteria:**
- Given a Dev Standard RFC not yet Completed, when a QA Standard RFC is submitted referencing it as predecessor, then submission is rejected with a clear error.
- Given that same Dev RFC marked Completed, when the QA RFC is resubmitted with the same predecessor, then it succeeds.
- Given an Emergency RFC with environment=Production and no predecessor, when submitted, then it succeeds.
- Given direct SQL insert into `change_requests` bypassing `main.py` entirely, when it violates the gate, then SQLite itself rejects it (trigger, not just API).

## Design Notes

The brief's Section 17.2 trigger is pseudocode (`BEGIN ... END` with a comment, no real body) written against an idealized multi-DB dialect. Verified empirically that SQLite fully supports the needed pattern — a `BEFORE INSERT ... WHEN ... BEGIN SELECT RAISE(ABORT, 'msg') WHERE <violation-condition using NOT EXISTS subquery on the same table> END;` — so no app-layer-only fallback is needed; this is a real, working translation, not a compromise.

`Completed` status does not exist anywhere in the current POC (max reached today is `CAB Reviewed`/`Auto-Approved...`). Adding a minimal `POST /rfc/{rfc_id}/complete` endpoint (sets `status='Completed'`) is required just to make the predecessor chain reachable/testable at all — flagged as a judgment call in the final report, not spec'd explicitly in the brief.

`environment` is modeled as `Optional[str] = "Dev"` in the Pydantic request model (defaults callers who omit it to the safest, gate-free tier) rather than strictly required, for backward compatibility with any existing callers of `/rfc/submit`. Brief says "required on all RFCs" for the *data model* column (which is `NOT NULL DEFAULT 'Dev'`) — satisfied; the API-level default is a pragmatic relaxation.

## Spec Change Log

## Verification

**Commands:**
- `cd poc/backend && python test_guardrails.py` -- expected: all tests pass (OK)
- `cd poc/backend && python db_init.py` -- expected: `[OK] Database initialized` with no errors, trigger created

**Manual checks (if no CLI):**
- Open the frontend submission form; confirm Environment select appears and Predecessor RFC select appears/hides correctly based on environment value.

## Suggested Review Order

**Enforcement backbone (data-access layer)**

- Entry point: the trigger that makes the gate non-bypassable regardless of code path — read this first.
  [`db_init.py:65`](../../poc/backend/db_init.py#L65)
- Mirrors the INSERT trigger on UPDATE so post-creation edits can't silently bypass the gate (review-driven addition).
  [`db_init.py:83`](../../poc/backend/db_init.py#L83)
- Belt-and-suspenders: rejects non-canonical environment spellings the gate trigger's WHEN wouldn't otherwise catch (review-driven addition).
  [`db_init.py:93`](../../poc/backend/db_init.py#L93)

**API pre-check (friendly errors, not the real enforcement)**

- Pure helper mirroring the trigger's logic in Python, so `/rfc/submit` can return a specific 400 instead of a raw DB error.
  [`guardrails.py:31`](../../poc/backend/guardrails.py#L31)
- Wired in after the *final* classified change_type is known (post auto-classify / No-Impact escalation) — the same value the trigger will see.
  [`main.py:265`](../../poc/backend/main.py#L265)
- Backstop: distinguishes a real gate rejection from an unrelated `IntegrityError` (e.g. rfc_number collision) so the latter isn't mislabeled.
  [`main.py:293`](../../poc/backend/main.py#L293)

**Making "Completed" reachable at all**

- New endpoint — nothing in the existing lifecycle ever reached `Completed`, so the predecessor chain was otherwise untestable/unusable.
  [`main.py:390`](../../poc/backend/main.py#L390)

**Frontend form wiring**

- Environment select + conditional Predecessor select; deliberately not HTML-`required` since change_type isn't known until after submit.
  [`App.jsx:1019`](../../poc/frontend/src/App.jsx#L1019)
- Clears a stale predecessor id when environment changes, so switching tiers can't submit a guaranteed-invalid reference.
  [`App.jsx:440`](../../poc/frontend/src/App.jsx#L440)
- "Mark Completed" action on the detail view — the UI path to the new endpoint above.
  [`App.jsx:545`](../../poc/frontend/src/App.jsx#L545)

**Tests (peripherals)**

- Layer 1 (raw trigger, bypasses main.py entirely) and Layer 2 (real `/rfc/submit` + `/rfc/{id}/complete`) — read the module docstring for the split.
  [`test_guardrails.py:1`](../../poc/backend/test_guardrails.py#L1)
