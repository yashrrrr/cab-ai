# CAB Readiness Orchestration Logic

## Steps

1. **Determine CR type.** Prefer an explicit field from the CR record (the
   `cr_type` column on `change_requests` — `infrastructure | application |
   mixed`, set at submission time). If absent (pre-existing CRs created
   before this field existed), infer from the description/attachments via
   an LLM call, and clearly label the result `crTypeSource: "inferred"`
   rather than `"confirmed"` in the output.
2. **Always run `cab-form-validation`** (Module 3) — it applies to every
   CR regardless of type.
3. **Run the type-specific module(s):** `cab-infra-review` (Module 1) if
   infrastructure, `cab-app-review` (Module 2) if application, both if
   mixed.
4. **Aggregate per the output contract** (below). Compute `moduleScore` per
   module and `overallScore` overall using
   `../../../rubrics/scoring-config.json`'s `state_scores` and
   `default_area_weight` — never hardcode these values inline in this or
   any module skill.
5. **Produce `missingMandatoryItems` and `pendingApprovers`** by walking
   every area across all evaluated modules that isn't `complete` (or
   `not_applicable`, which is excluded entirely — a conditional row that
   doesn't apply should never appear as "missing").
6. **Surface `[VERIFY]` items** from the source checklists (currently:
   Module 1 row 1's required approver) into `openVerificationItems` so
   they're visible to whoever reviews the run, not silently dropped.

## Scoring source of truth

`../../../rubrics/scoring-config.json` and `../../../rubrics/approvers.json`
are the canonical data files. `poc/backend/cab_readiness.py` is the
deterministic re-implementation used by the `/api/cab/evaluate` API
endpoint — it reads the same two JSON files, never a hardcoded copy.

## Output contract

All modules feed into this one shape — extend it if new fields are needed,
never create a second parallel shape:

```json
{
  "crId": "string",
  "crType": "infrastructure | application | mixed",
  "crTypeSource": "confirmed | inferred",
  "evaluatedAt": "ISO-8601 timestamp",
  "modules": [
    {
      "module": "module-3-form-validation | module-1-infra | module-2-application",
      "areas": [
        {
          "id": "short-slug",
          "name": "Human-readable area name",
          "requirement": "text of the mandatory approval/document requirement",
          "requiredApprovers": ["string", "..."],
          "status": "complete | partial | missing | not_applicable",
          "conditionApplies": true,
          "evidence": [{ "fileName": "string", "notes": "string" }],
          "approverConfirmed": true,
          "score": 1,
          "weight": 1,
          "notes": "string",
          "verifyFlag": false
        }
      ],
      "moduleScore": 0,
      "moduleStatus": "ready | conditional | not_ready"
    }
  ],
  "overallScore": 0,
  "overallStatus": "ready | conditional | not_ready",
  "missingMandatoryItems": [{ "module": "string", "area": "string", "requiredApprovers": ["string"] }],
  "pendingApprovers": ["string"],
  "piiFlags": [{ "area": "Data Privacy Assessment", "flag": "PII/PHI indicators detected — DPIA required", "documentRef": "string" }],
  "openVerificationItems": ["string — anything still marked [VERIFY] in the source checklists"],
  "scoringDisclaimer": "Interim rubric — pending finalized templates and scoring criteria."
}
```
