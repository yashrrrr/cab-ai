"""
CAB Readiness Agent — deterministic orchestration engine.

This is a from-scratch Python re-implementation of the same checklist/
scoring logic described in .claude/skills/cab-orchestrator (and its sibling
module skills cab-form-validation/cab-infra-review/cab-app-review) — those
skills are markdown instructions for an interactive Claude Code session;
this module is the callable, deterministic path the POST /api/cab/evaluate
endpoint uses.

Checklist row content (area names, requirements, approver keys, [VERIFY]
flags, conditional flags) is encoded below as Python constants, hand-kept in
sync with .claude/skills/*/references/module-*-checklist.md. This
duplication is a known, documented tradeoff (see poc/CAB_READINESS_README.md)
— markdown-table parsing would add real complexity for no PoC-stage benefit.

Scoring weights/thresholds and approver names are NEVER hardcoded here —
both are read from rubrics/scoring-config.json and rubrics/approvers.json
at the repo root, the single source of truth shared with the skills.
"""

import json
import os
import re
from datetime import datetime
from typing import Optional

from llm_gateway import chat_completion
from pii_guardrail import scan_for_pii

_BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.abspath(os.path.join(_BACKEND_DIR, "..", ".."))
_RUBRICS_DIR = os.path.join(_REPO_ROOT, "rubrics")


def _load_json(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


APPROVERS = _load_json(os.path.join(_RUBRICS_DIR, "approvers.json"))
SCORING = _load_json(os.path.join(_RUBRICS_DIR, "scoring-config.json"))
STATE_SCORES = SCORING["state_scores"]

# ─────────────────────────────────────────────────────────────
# Checklist constants — mirror .claude/skills/*/references/module-*.md
# ─────────────────────────────────────────────────────────────

MODULE_3_CHECKLIST = [
    {"id": "business-justification", "name": "Business Justification",
     "requirement": "Clearly describe why the change is required.", "field": "business_justification"},
    {"id": "problem-statement", "name": "Problem Statement",
     "requirement": "Define the existing issue or business need.", "field": "description"},
    {"id": "proposed-solution", "name": "Proposed Solution",
     "requirement": "Explain the planned solution or change.", "field": "description"},
    {"id": "expected-outcomes", "name": "Expected Outcomes",
     "requirement": "Document expected benefits and outcomes.", "field": "business_justification"},
    {"id": "stakeholder-impact", "name": "Consumer/Stakeholder Impact",
     "requirement": "Identify affected users, systems, or stakeholders.", "field": "affected_systems"},
    {"id": "implementation-details", "name": "Implementation Details",
     "requirement": "Detailed implementation plan must be provided.", "field": "implementation_plan"},
    {"id": "testing-evidence", "name": "Testing Evidence",
     "requirement": "Test execution results and sign-offs must be attached.", "field": "test_cases"},
    {"id": "supporting-documents-form", "name": "Supporting Documents",
     "requirement": "All mandatory approvals, assessment reports, and design documents should be attached before submission.",
     "field": None, "document_presence_only": True},
]

MODULE_1_CHECKLIST = [
    {"id": "architecture-review", "name": "Architecture Review",
     "requirement": "Architecture review and approval must be completed before CR submission.",
     "approver_key": "architecture_review", "category_hint": "architecture_diagram", "verify_flag": True},
    {"id": "cloud-deployment", "name": "Cloud Deployment / Cloud Subscription Changes",
     "requirement": "Budget approval for new cloud deployments, additions to existing cloud infrastructure, or subscription changes.",
     "approver_key": "cloud_budget_approval", "category_hint": None},
    {"id": "aup-review", "name": "Acceptable Usage Policy (AUP)",
     "requirement": "AUP review and approval.", "approver_key": "aup_review", "category_hint": None},
    {"id": "data-privacy-assessment", "name": "Data Privacy Assessment",
     "requirement": "Data Privacy Impact Assessment (DPIA) required when data, PII, or PHI is processed.",
     "approver_key": "data_privacy", "category_hint": "dpia", "pii_check": True},
    {"id": "internal-system-integration", "name": "Internal System Integration",
     "requirement": "Service owner approval emails required for integrations with UST systems.",
     "approver_key": "internal_integration", "category_hint": None},
    {"id": "client-system-integration", "name": "Client System Integration",
     "requirement": "Approval and alignment required for integrations with client systems.",
     "approver_key": "client_integration", "category_hint": None},
    {"id": "vendor-application-involvement", "name": "Vendor Application Involvement",
     "requirement": "Approval required when vendor-hosted or vendor-managed infrastructure is involved.",
     "approver_key": "vendor_involvement", "category_hint": None},
    {"id": "supporting-documentation", "name": "Supporting Documentation",
     "requirement": "Architecture diagrams and related infrastructure documents must be attached and approved before submission.",
     "approver_key": "supporting_docs_infra", "category_hint": "architecture_diagram"},
]

MODULE_2_CHECKLIST = [
    {"id": "architecture-review-app", "name": "Architecture Review",
     "requirement": "Architecture review and approval.",
     "approver_key": "architecture_review_app", "category_hint": "architecture_diagram"},
    {"id": "data-privacy-alignment", "name": "Data Privacy Alignment",
     "requirement": "Data Privacy review and alignment.",
     "approver_key": "data_privacy", "category_hint": "dpia", "pii_check": True},
    {"id": "ai-architecture-alignment", "name": "AI Architecture Alignment",
     "requirement": "AI Architecture review and approval (if AI components are involved).",
     "approver_key": "ai_architecture", "category_hint": None, "conditional": True},
    {"id": "security-validation", "name": "Security Validation",
     "requirement": "VAPT Report (Vulnerability Assessment and Penetration Testing).",
     "approver_key": "security_validation", "category_hint": "vapt_report"},
    {"id": "testing-validation", "name": "Testing Validation",
     "requirement": "Test Cases and Test Sign-Off Documents.",
     "approver_key": "testing_validation", "category_hint": "test_signoff"},
    {"id": "vendor-involvement-app", "name": "Vendor Involvement",
     "requirement": "SOP documentation when vendor applications or vendors are involved.",
     "approver_key": "vendor_involvement_app", "category_hint": None, "conditional": True},
    {"id": "security-assessment", "name": "Security Assessment",
     "requirement": "ISMS Security Impact Assessment Report.",
     "approver_key": "security_assessment", "category_hint": None},
    {"id": "business-design-documents", "name": "Business & Design Documents",
     "requirement": "BRD, FRD, Flow Diagrams, Architecture Diagrams, and Network Architecture Diagrams.",
     "approver_key": "business_design_docs", "category_hint": "brd_frd"},
    {"id": "integration-approval-app", "name": "Integration Approval",
     "requirement": "Service Owner approval emails for application integrations.",
     "approver_key": "integration_approval_app", "category_hint": None},
    {"id": "cloud-subscription-hosting", "name": "Cloud Subscription Hosting",
     "requirement": "Approval required if the application is hosted in another team's cloud subscription.",
     "approver_key": "cloud_subscription_hosting", "category_hint": None, "conditional": True},
    {"id": "change-justification", "name": "Change Justification",
     "requirement": "CR Description must clearly include Business Justification, Problem Statement, Proposed Solution, Expected Outcomes, and Stakeholder/Consumer Impact.",
     "required_approvers": ["Requestor"], "category_hint": None,
     "overlaps_module_3": True, "field": "description"},
]

_CONDITION_KEYWORDS = {
    "ai-architecture-alignment": ("ai ", "artificial intelligence", "machine learning", "ml model", "llm", "genai", "chatbot"),
    "vendor-involvement-app": ("vendor", "third-party", "third party"),
    "cloud-subscription-hosting": ("another team", "cross-team", "shared subscription", "hosted in"),
}


def _condition_applies(area_id: str, rfc_row) -> bool:
    """Heuristic keyword check — PoC-level, not a real classifier. Documented
    in poc/CAB_READINESS_README.md as an area to revisit."""
    keywords = _CONDITION_KEYWORDS.get(area_id)
    if not keywords:
        return True
    text = f"{rfc_row['title']} {rfc_row['description']}".lower()
    return any(kw in text for kw in keywords)


def determine_cr_type(rfc_row) -> tuple:
    """(type, 'confirmed') if rfc_row['cr_type'] is set, else falls back to
    an LLM classification call over title+description, returning
    (type, 'inferred')."""
    existing = rfc_row["cr_type"] if "cr_type" in rfc_row.keys() else None
    if existing:
        return existing, "confirmed"

    system_prompt = (
        "Classify a Change Request as exactly one of: infrastructure, application, mixed. "
        "Respond with exactly one word — the classification only."
    )
    user_prompt = f"Title: {rfc_row['title']}\nDescription: {rfc_row['description']}"
    result = chat_completion(system_prompt, user_prompt, max_tokens=10)
    if result:
        normalized = result.strip().lower()
        for candidate in ("infrastructure", "application", "mixed"):
            if candidate in normalized:
                return candidate, "inferred"
    return "mixed", "inferred"  # unresolvable — evaluate against both modules rather than guessing wrong


def _match_documents(documents, category_hint: Optional[str]):
    if category_hint:
        matched = [d for d in documents if d.get("category") == category_hint]
        if matched:
            return matched
    return documents


def _classify_text(requirement: str, label: str, text: Optional[str]) -> tuple:
    """Returns (status, note). Never raises — an LLM failure degrades to a
    conservative 'partial'/'missing' status rather than blocking the whole
    evaluation."""
    if not text or not text.strip():
        return "missing", "No content found for this area."

    system_prompt = (
        "You are grading one checklist item for a Change Request CAB-readiness review. "
        "Given the requirement and the relevant content, decide whether the requirement is "
        "complete, partial, or missing. Boilerplate, placeholder, or clearly too-thin content "
        "is 'partial' or 'missing' — never rubber-stamp non-empty text as 'complete'. "
        "Respond in exactly this format:\nSTATUS: <complete|partial|missing>\nNOTE: <one short sentence>"
    )
    user_prompt = f"Requirement ({label}): {requirement}\n\nContent:\n{text[:4000]}"
    result = chat_completion(system_prompt, user_prompt, max_tokens=120)
    if not result:
        return "partial", "LLM evaluation unavailable — content present but unverified."

    status_match = re.search(r"STATUS:\s*(complete|partial|missing)", result, re.IGNORECASE)
    note_match = re.search(r"NOTE:\s*(.+)", result, re.IGNORECASE)
    status = status_match.group(1).lower() if status_match else "partial"
    note = note_match.group(1).strip() if note_match else "Evaluated by LLM."
    return status, note


def evaluate_area(area_def: dict, rfc_row, documents: list) -> dict:
    """One area of the output contract's 'areas' array."""
    approvers = area_def.get("required_approvers")
    if approvers is None:
        approvers = APPROVERS.get(area_def.get("approver_key"), [])

    entry = {
        "id": area_def["id"],
        "name": area_def["name"],
        "requirement": area_def["requirement"],
        "requiredApprovers": approvers,
        "status": "missing",
        "conditionApplies": True,
        "evidence": [],
        # This PoC has no approver-confirmation data model (no sign-off
        # tracking) — always False; a real approver workflow would set this.
        "approverConfirmed": False,
        "score": 0,
        "weight": SCORING["default_area_weight"],
        "notes": "",
        "verifyFlag": area_def.get("verify_flag", False),
    }
    if area_def.get("overlaps_module_3"):
        entry["notes"] = "Overlaps with module-3-form-validation — see that module for the same fields."

    if area_def.get("conditional"):
        applies = _condition_applies(area_def["id"], rfc_row)
        entry["conditionApplies"] = applies
        if not applies:
            entry["status"] = "not_applicable"
            entry["notes"] = f"{area_def['name']} does not apply to this CR."
            entry["score"] = None
            return entry

    pii_hits = []

    if area_def.get("document_presence_only"):
        entry["evidence"] = [{"fileName": d["filename"], "notes": d.get("category") or "other"} for d in documents]
        status = "complete" if documents else "missing"
        note = f"{len(documents)} document(s) attached." if documents else "No supporting documents attached."
        entry["status"] = status
        entry["notes"] = (entry["notes"] + " " + note).strip()
    elif area_def.get("field"):
        field_name = area_def["field"]
        raw_value = rfc_row[field_name] if field_name in rfc_row.keys() else None
        if field_name == "affected_systems" and raw_value:
            try:
                systems = json.loads(raw_value)
                text = ", ".join(systems) if isinstance(systems, list) else str(raw_value)
            except Exception:
                text = str(raw_value)
        else:
            text = raw_value
        status, note = _classify_text(area_def["requirement"], area_def["name"], text)
        entry["status"] = status
        entry["notes"] = (entry["notes"] + " " + note).strip()
        if area_def.get("pii_check"):
            pii_hits = scan_for_pii(text or "")
    else:
        matched_docs = _match_documents(documents, area_def.get("category_hint"))
        combined_text = "\n\n".join(d.get("document_text") or "" for d in matched_docs if d.get("document_text"))
        entry["evidence"] = [{"fileName": d["filename"], "notes": d.get("category") or "other"} for d in matched_docs]
        if not matched_docs or not combined_text.strip():
            status, note = "missing", "No supporting document found for this area."
        else:
            status, note = _classify_text(area_def["requirement"], area_def["name"], combined_text)
        entry["status"] = status
        entry["notes"] = (entry["notes"] + " " + note).strip()
        if area_def.get("pii_check"):
            pii_hits = scan_for_pii(combined_text)

    entry["score"] = STATE_SCORES.get(entry["status"])
    if pii_hits:
        entry["_pii_hits"] = pii_hits
    return entry


def _score_status(score: float, thresholds: dict) -> str:
    if score >= thresholds["ready_min"]:
        return "ready"
    if score >= thresholds["conditional_min"]:
        return "conditional"
    return "not_ready"


def evaluate_module(module_key: str, checklist: list, rfc_row, documents: list) -> dict:
    """Runs evaluate_area over every area_def in the module's checklist
    constant, computes moduleScore/moduleStatus from
    rubrics/scoring-config.json's state_scores + thresholds."""
    areas = [evaluate_area(area_def, rfc_row, documents) for area_def in checklist]
    scored = [a["score"] for a in areas if a["score"] is not None]
    module_score = round(100 * sum(scored) / len(scored)) if scored else 100
    return {
        "module": module_key,
        "areas": areas,
        "moduleScore": module_score,
        "moduleStatus": _score_status(module_score, SCORING["module_status_thresholds"]),
    }


def evaluate(rfc_row, documents: list) -> dict:
    """Full orchestration per the CAB Readiness Agent brief: always
    evaluate_module('module-3-form-validation', ...); branch to module-1/
    module-2/both based on determine_cr_type(); aggregate overallScore/
    overallStatus; walk non-complete areas into missingMandatoryItems/
    pendingApprovers; collect piiFlags; collect verifyFlag=True areas into
    openVerificationItems."""
    cr_type, cr_type_source = determine_cr_type(rfc_row)

    modules = [evaluate_module("module-3-form-validation", MODULE_3_CHECKLIST, rfc_row, documents)]
    if cr_type in ("infrastructure", "mixed"):
        modules.append(evaluate_module("module-1-infra", MODULE_1_CHECKLIST, rfc_row, documents))
    if cr_type in ("application", "mixed"):
        modules.append(evaluate_module("module-2-application", MODULE_2_CHECKLIST, rfc_row, documents))

    all_scores = [a["score"] for m in modules for a in m["areas"] if a["score"] is not None]
    overall_score = round(100 * sum(all_scores) / len(all_scores)) if all_scores else 100
    overall_status = _score_status(overall_score, SCORING["overall_status_thresholds"])

    missing_items = []
    pending_approvers = set()
    open_verification_items = []
    pii_flags = []

    for module in modules:
        for area in module["areas"]:
            if area["status"] not in ("complete", "not_applicable"):
                missing_items.append({
                    "module": module["module"],
                    "area": area["name"],
                    "requiredApprovers": area["requiredApprovers"],
                })
                pending_approvers.update(area["requiredApprovers"])
            if area.get("verifyFlag"):
                open_verification_items.append(f"{module['module']} — {area['name']}: {area['requirement']}")
            pii_hits = area.pop("_pii_hits", None)
            if pii_hits:
                doc_ref = ", ".join(e["fileName"] for e in area["evidence"]) or "CR text"
                for hit in pii_hits:
                    pii_flags.append({
                        "area": area["name"],
                        "flag": f"PII/PHI indicator detected: {hit['category']} (x{hit['count']})",
                        "documentRef": doc_ref,
                    })

    return {
        "crId": rfc_row["id"],
        "crType": cr_type,
        "crTypeSource": cr_type_source,
        "evaluatedAt": datetime.now().isoformat(),
        "modules": modules,
        "overallScore": overall_score,
        "overallStatus": overall_status,
        "missingMandatoryItems": missing_items,
        "pendingApprovers": sorted(pending_approvers),
        "piiFlags": pii_flags,
        "openVerificationItems": open_verification_items,
        "scoringDisclaimer": SCORING["status_disclaimer"],
    }
