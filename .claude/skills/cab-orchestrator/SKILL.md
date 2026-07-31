---
name: cab-orchestrator
description: Determines CR readiness for CAB submission end-to-end — classifies the CR as infrastructure, application, or mixed, runs cab-form-validation always plus cab-infra-review and/or cab-app-review as applicable, aggregates per-area results into one overall score and status, and lists exactly what's missing and from whom. This is the primary entry point for any "is this CR ready for CAB" / "generate CAB readiness score" / "CAB compliance check" request — invoke this rather than the individual module skills directly unless the caller has already narrowed the CR type.
---

# CAB Readiness Orchestrator

This is the entry point for a full CR readiness evaluation — the UI/API
call this (or its deterministic Python re-implementation,
`poc/backend/cab_readiness.py`) rather than the individual module skills
directly.

## Logic

The full 6-step orchestration logic (CR-type determination, module
selection, aggregation, scoring, missing-item collection, `[VERIFY]`
surfacing) lives in `references/orchestration-logic.md` — read it before
running an evaluation.

## Source of truth for scoring

`../../../rubrics/scoring-config.json` and `../../../rubrics/approvers.json`
are the canonical scoring/approver data — every module skill (and the
Python re-implementation) reads from these same two files. Never hardcode
weights, thresholds, or approver names inline in any skill.

## Relationship to the backend API

`poc/backend/cab_readiness.py` is a deterministic Python re-implementation
of this same checklist/scoring logic, used by the `POST /api/cab/evaluate`
endpoint so the UI gets a callable, non-interactive evaluation path. Its
checklist row content (area names, requirements, approvers, `[VERIFY]`
flags, conditional flags) is hand-kept in sync with this skill's
`references/module-*-checklist.md` files — if the source checklists here
change, update `cab_readiness.py`'s constants too.
