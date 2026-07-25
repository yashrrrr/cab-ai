---
title: 'Per-Agent CAB Recommendation Flags'
type: 'feature'
created: '2026-07-25'
status: 'done'
review_loop_iteration: 0
context: []
baseline_commit: '7f993ba854c38f73fe6c778d2a601d5c59ea1671'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** CAB agents produce prose opinions but no structured, actionable "required changes." Approvers must re-read paragraphs to extract what must actually change (e.g. "group X must not have access to this button"), and there is no single place at the end of an RFC listing those action items.

**Approach:** Have every CAB agent (4 specialists + Chair) optionally emit structured recommendation *flags* alongside its prose. Collect all flags verbatim, persist them on the RFC, cap the final decision when any Must-fix flag exists, and render a "Required Changes & Recommendations" panel at the bottom of the RFC detail and CAB log.

## Boundaries & Constraints

**Always:**
- Each agent may raise ZERO or more flags — never forced; a clean review yields none.
- A flag carries: `raised_by`, `severity` (Must-fix | Should-fix | Nice-to-have), `category` (Access/Permissions | Testing | Rollback/Recovery | Communication/SLA | Compliance/Security | Infrastructure | Other), `affected_element`, `recommendation`.
- Aggregation is RAW CONCATENATION: keep every flag, grouped by agent, no merging/de-duplication across agents. Within an agent group, sort Must-fix first, then Should-fix, then Nice-to-have.
- If ANY Must-fix flag exists, the final CAB decision is capped: a would-be "Approved" becomes "Conditional Approval". "Rejected" stays "Rejected". Should-fix/Nice-to-have never change the decision.
- Flag parsing must be robust: a missing/malformed/empty flags block from a model yields an empty list for that agent, never an exception.

**Ask First:**
- Adding a new flag field, changing severity/category vocabularies, or changing the decision-cap rule.

**Never:**
- Do NOT switch the LLM provider — keep the existing OpenAI SDK / GitHub Models (`gpt-4o`) client in `cab_orchestrator.py`.
- Do NOT let the Chair merge or drop other agents' flags.
- Do NOT fix the unrelated pre-existing `classify_rfc` unpacking bug in `main.py` here.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Agent raises flags | Model returns a valid `FLAGS:` JSON array | Each object parsed into a flag dict tagged with that agent's `raised_by`, appended to the aggregate list | N/A |
| Clean review | Model returns empty array / no flags block | No flags contributed by that agent | Treat as empty list |
| Malformed flags block | Non-JSON or partial JSON after `FLAGS:` | That agent contributes zero flags; other agents unaffected | Catch parse error, log-skip |
| Must-fix present | Aggregate contains ≥1 `Must-fix` and synthesis says "approve" | Final decision returned as "Conditional Approval" | N/A |
| No flags at all | Every agent returns none | `cab_flags` persisted as `[]`; panel shows "No required changes flagged." | N/A |
| Cached view | RFC previously reviewed, `cab_flags` column populated | GET /rfc/{id} returns parsed flags; panel renders from cache | Empty/NULL column → `[]` |

</frozen-after-approval>

## Code Map

- `poc/backend/cab_orchestrator.py` -- 5 agent prompts, `run_ai_cab_session`, `parse_decision`; extend prompts to emit flags, parse them, return 4th value, apply Must-fix cap.
- `poc/backend/db_init.py` -- `change_requests` schema; add `cab_flags TEXT` column + idempotent migration for the existing `rfc_poc.db`.
- `poc/backend/main.py` -- `RFCResponse` model, GET `/rfc/{id}`, POST `/rfc/{id}/trigger-cab`; persist/return `cab_flags`, handle new 4-tuple from `run_ai_cab_session`.
- `poc/frontend/src/App.jsx` -- RFC detail view; render flags panel at the bottom of live CAB session and cached decision.
- `poc/frontend/src/App.css` -- styles for flag panel + severity badges.

## Tasks & Acceptance

**Execution:**
- [x] `poc/backend/cab_orchestrator.py` -- Append a flags instruction to each specialist + chair prompt (emit `FLAGS:` + a JSON array of `{severity, category, affected_element, recommendation}`, or `FLAGS: []`); add a robust `parse_flags(text, raised_by)` helper; collect flags from all 5 agents, sorted per-agent Must-fix→Nice; return `(decision, reasoning, agent_logs, flags)`; if any Must-fix flag exists and decision == "Approved", downgrade to "Conditional Approval"; append a grouped "🚩 REQUIRED CHANGES & RECOMMENDATIONS" block to `agent_logs`.
- [x] `poc/backend/db_init.py` -- Add `cab_flags TEXT` to the CREATE TABLE plus an idempotent `ALTER TABLE ADD COLUMN cab_flags` (guarded by a PRAGMA column check) so the existing DB migrates on startup.
- [x] `poc/backend/main.py` -- Add `cab_flags: Optional[List[dict]] = None` to `RFCResponse`; unpack 4 values from `run_ai_cab_session`; persist flags as JSON in the trigger-cab UPDATE and return them; parse `cab_flags` JSON in GET `/rfc/{id}` (default `[]`); run the migration on startup even when the DB file exists.
- [x] `poc/frontend/src/App.jsx` -- Add a flags panel (grouped by agent, Must-fix first, severity badge + category + affected element + recommendation, empty-state when none) at the bottom of both the live `cabSession` block and the cached `selectedRfc.cab_decision` block, reading `cab_flags` from each.
- [x] `poc/frontend/src/App.css` -- Styles for `.flags-panel`, `.flag-item`, and severity badge classes.

**Acceptance Criteria:**
- Given an RFC reviewed by the CAB where a specialist emits a Must-fix access flag, when the session completes, then the returned `cab_decision` is not "Approved" and the flag appears in `cab_flags` tagged with that specialist as `raised_by`.
- Given two agents independently raise the same recommendation, when flags are aggregated, then both appear (no de-duplication), each under its own agent group.
- Given a previously reviewed RFC is re-opened, when GET `/rfc/{id}` is called, then `cab_flags` is returned and the bottom panel renders the same flags as the live session.
- Given an agent returns no/malformed flags block, when the session runs, then no exception is raised and that agent contributes zero flags.

## Design Notes

Flag transport from the model uses a sentinel line to keep prose and structure separable:

```
<prose assessment ...>
FLAGS: [{"severity":"Must-fix","category":"Access/Permissions",
         "affected_element":"'Export' button -> Sales-Ops group",
         "recommendation":"Remove Export permission from Sales-Ops before deploy"}]
```

`parse_flags` splits on the last `FLAGS:`, `json.loads` the remainder, drops malformed entries, stamps `raised_by`, and normalizes unknown `severity`/`category` to `Nice-to-have`/`Other`. Empty array or any exception → `[]`. Strip the `FLAGS:` line from the prose shown in `agent_logs` so the deliberation reads cleanly.

## Verification

**Commands:**
- `cd poc/backend && python -c "import db_init, classification, cab_orchestrator"` -- expected: imports succeed (requires `OPENAI_API_KEY` set; if unset, expect only the orchestrator's explicit env error, confirming provider unchanged).
- `cd poc/backend && python -c "import sqlite3; c=sqlite3.connect('rfc_poc.db'); print([r[1] for r in c.execute('PRAGMA table_info(change_requests)')])"` -- expected: output includes `cab_flags`.

**Manual checks:**
- Start backend + frontend, open a Normal RFC (e.g. CHG20260724002), trigger CAB review: deliberation logs render, a "Required Changes & Recommendations" panel appears at the bottom grouped by agent with severity badges, and any Must-fix flag yields a non-"Approved" decision. Re-open the RFC: the same panel renders from cache.

## Suggested Review Order

**Flag extraction (highest risk — governs the Must-fix cap)**

- Entry point: robust prose/flags split — `raw_decode` stops at array end, tolerates trailing prose containing `]`, normalizes non-string fields.
  [`cab_orchestrator.py:143`](../../poc/backend/cab_orchestrator.py#L143)

- The instruction appended to every agent prompt that makes models emit the `FLAGS:` block.
  [`cab_orchestrator.py:132`](../../poc/backend/cab_orchestrator.py#L132)

**Session orchestration & decision cap**

- Collects flags from all 5 agents (raw concatenation), returns the new 4-tuple, appends the required-changes log block.
  [`cab_orchestrator.py:234`](../../poc/backend/cab_orchestrator.py#L234)

- The Must-fix → "Conditional Approval" cap.
  [`cab_orchestrator.py:290`](../../poc/backend/cab_orchestrator.py#L290)

**Schema & migration**

- Idempotent, concurrency- and missing-table-safe migration adding `cab_flags`.
  [`db_init.py:72`](../../poc/backend/db_init.py#L72)

**API contract**

- 4-tuple unpack + persist flags as JSON on trigger-cab.
  [`main.py:312`](../../poc/backend/main.py#L312)

- GET parses `cab_flags`, guarding against non-list stored JSON.
  [`main.py:240`](../../poc/backend/main.py#L240)

- Startup runs the migration even when the DB already exists.
  [`main.py:111`](../../poc/backend/main.py#L111)

**UI binding**

- `FlagsPanel` — grouped by agent, Must-fix first, severity badges; rendered at the bottom of both live and cached views.
  [`App.jsx:12`](../../poc/frontend/src/App.jsx#L12)
