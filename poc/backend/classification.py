"""
Deterministic RFC Classification Engine
- Change Type classification
- Impact scoring (1-High, 2-Medium, 3-Low)
- Priority scoring (Critical, High, Moderate, Low)
- Risk assessment (1-5 scale)
- Standard Change Catalogue matching
- No Impact evaluation
"""

from enum import Enum
from typing import Tuple, List, Dict

class ImpactEnum(str, Enum):
    HIGH = "1-High"
    MEDIUM = "2-Medium"
    LOW = "3-Low"

class PriorityEnum(str, Enum):
    CRITICAL = "Critical"
    HIGH = "High"
    MODERATE = "Moderate"
    LOW = "Low"

# ─────────────────────────────────────────────────────────────
# Standard Change Catalogue (Hardcoded for PoC)
# ─────────────────────────────────────────────────────────────

SCC_ENTRIES = [
    {
        "name": "User Account Creation",
        "keywords": ["user", "account", "create", "active directory"],
        "services": ["Active Directory"],
        "risk_level": 1,
        "requires_test": False,
    },
    {
        "name": "Password Reset",
        "keywords": ["password", "reset", "unlock", "account unlock"],
        "services": ["Active Directory"],
        "risk_level": 1,
        "requires_test": False,
    },
    {
        "name": "Disk Space Extension",
        "keywords": ["disk", "storage", "extend", "partition", "mount"],
        "services": ["Storage", "Infrastructure"],
        "risk_level": 1,
        "requires_test": False,
    },
    {
        "name": "Application Log Rotation",
        "keywords": ["log rotation", "logging", "cleanup", "archive"],
        "services": ["Applications"],
        "risk_level": 1,
        "requires_test": False,
    },
    {
        "name": "Monitoring Threshold Update",
        "keywords": ["monitoring", "threshold", "alert", "metric"],
        "services": ["Monitoring"],
        "risk_level": 1,
        "requires_test": False,
    },
]

# ─────────────────────────────────────────────────────────────
# Change Type Classification (RFC Section 7.0)
# ─────────────────────────────────────────────────────────────

def classify_change_type(description: str, downtime: float, urgency_keywords: List[str]) -> str:
    """
    Classify RFC into one of: Normal, Expedited, Emergency, Standard, No Impact
    Based on description, downtime, and keywords.
    """

    desc_lower = description.lower()

    # Emergency: 24-48 hour, service outage, urgent
    if any(word in desc_lower for word in ["emergency", "outage", "critical", "down", "production issue"]):
        return "Emergency"

    # Expedited: urgent but not emergency
    if any(word in desc_lower for word in ["urgent", "asap", "expedited", "quick"]):
        return "Expedited"

    # Standard: routine, low-risk (will check against SCC later)
    if any(word in desc_lower for word in ["standard", "routine", "regular", "scheduled"]):
        return "Standard"

    # No Impact: no downtime, no user impact, metadata/config only
    if any(word in desc_lower for word in ["metadata", "config", "internal", "no downtime", "no impact"]):
        if downtime == 0:
            return "No Impact"

    # Default: Normal
    return "Normal"

# ─────────────────────────────────────────────────────────────
# Impact Scoring (RFC Section 8.0)
# ─────────────────────────────────────────────────────────────

def assess_impact(affected_systems: List[str], downtime: float, description: str) -> ImpactEnum:
    """
    Score impact: 1-High, 2-Medium, 3-Low
    Based on: # systems affected, downtime, scope.
    """

    desc_lower = description.lower()

    # High Impact: many systems, extended downtime, enterprise-wide
    if len(affected_systems) >= 3 or downtime > 4:
        if any(word in desc_lower for word in ["enterprise", "production", "mission", "critical", "all users"]):
            return ImpactEnum.HIGH

    # Medium Impact: moderate scope, 1-4 hour downtime
    if len(affected_systems) >= 2 or (1 <= downtime <= 4):
        return ImpactEnum.MEDIUM

    # Low Impact: single system, minimal downtime, isolated
    return ImpactEnum.LOW

# ─────────────────────────────────────────────────────────────
# Priority Scoring (RFC Section 8.0)
# ─────────────────────────────────────────────────────────────

def assess_priority(impact: ImpactEnum, description: str) -> PriorityEnum:
    """
    Score priority: Critical, High, Moderate, Low
    Based on: impact, security, business urgency.

    RFC Section 8.0: priority = highest of (service availability, security, business reaction).
    """

    desc_lower = description.lower()

    # CRITICAL: service down, security violation, immediate action
    if impact == ImpactEnum.HIGH:
        if any(word in desc_lower for word in ["security", "breach", "compromised", "critical", "down"]):
            return PriorityEnum.CRITICAL

    # HIGH: service degraded, significant impact
    if impact == ImpactEnum.HIGH:
        return PriorityEnum.HIGH

    if any(word in desc_lower for word in ["security", "breach", "vulnerability"]):
        return PriorityEnum.HIGH

    # MODERATE: medium impact, can wait
    if impact == ImpactEnum.MEDIUM:
        return PriorityEnum.MODERATE

    # LOW: low impact, can defer
    return PriorityEnum.LOW

# ─────────────────────────────────────────────────────────────
# Risk Assessment (RFC Section 23.0)
# ─────────────────────────────────────────────────────────────

def assess_risk(
    affected_systems: List[str],
    downtime: float,
    impact: ImpactEnum,
    description: str,
    test_cases: str = None
) -> int:
    """
    Compute risk level (1-5) for Normal changes.
    Criteria: users impacted, outage required, business impact, performance impact, history.
    """

    risk_score = 0

    # Users impacted: ≥500 (L5), 100-500 (L3), ≤100 (L1)
    # For PoC, estimate: each system has ~100 users per service
    estimated_users = len(affected_systems) * 100
    if estimated_users >= 500:
        risk_score = max(risk_score, 5)
    elif estimated_users >= 100:
        risk_score = max(risk_score, 3)
    else:
        risk_score = max(risk_score, 1)

    # Outage required: outside maintenance window (L5), during window (L3), none (L1)
    if downtime > 0:
        # Assume downtime outside normal window = higher risk
        risk_score = max(risk_score, 4)
    else:
        risk_score = max(risk_score, 1)

    # Business impact: enterprise-wide (L5), multiple lines (L4), site/office (L3), no impact (L1)
    if impact == ImpactEnum.HIGH:
        risk_score = max(risk_score, 5)
    elif impact == ImpactEnum.MEDIUM:
        risk_score = max(risk_score, 3)
    else:
        risk_score = max(risk_score, 1)

    # First-time implementation (L5), <3 times (L2), ≥3 times (L1)
    desc_lower = description.lower()
    if any(word in desc_lower for word in ["new", "first", "novel", "untested"]):
        risk_score = max(risk_score, 5)
    elif "proven" in desc_lower or "routine" in desc_lower:
        risk_score = max(risk_score, 1)
    else:
        risk_score = max(risk_score, 2)

    # Test coverage: weak tests = higher risk
    if test_cases and ("comprehensive" in test_cases.lower() or "regression" in test_cases.lower()):
        risk_score = min(risk_score, 3)  # Good tests lower risk

    return min(risk_score, 5)

# ─────────────────────────────────────────────────────────────
# Standard Change Catalogue Matching
# ─────────────────────────────────────────────────────────────

def match_scc(title: str, affected_systems: List[str]) -> bool:
    """
    Check if RFC matches an SCC entry.
    Returns True if matched (auto-approve candidate).
    """

    title_lower = title.lower()

    for entry in SCC_ENTRIES:
        # Check if keywords match
        keyword_match = any(kw in title_lower for kw in entry["keywords"])

        # Check if affected services match
        service_match = any(svc.lower() in [s.lower() for s in affected_systems] for svc in entry["services"])

        if keyword_match and service_match:
            return True

    return False

def get_scc_entry(title: str, affected_systems: List[str]):
    """Get the matched SCC entry details"""
    title_lower = title.lower()

    for entry in SCC_ENTRIES:
        keyword_match = any(kw in title_lower for kw in entry["keywords"])
        service_match = any(svc.lower() in [s.lower() for s in affected_systems] for svc in entry["services"])

        if keyword_match and service_match:
            return entry

    return None

# ─────────────────────────────────────────────────────────────
# No Impact Evaluation (RFC Section 18.0)
# ─────────────────────────────────────────────────────────────

def evaluate_no_impact(
    description: str,
    downtime: float,
    affected_systems: List[str],
    test_cases: str = None
) -> Tuple[bool, List[str]]:
    """
    Evaluate if RFC truly meets No Impact criteria (RFC Section 18.0).
    Returns: (is_no_impact: bool, reasons: List[str])

    Criteria:
    1. No end-user impact
    2. No service outage
    3. No interdependent systems affected
    4. Rollback simple
    5. Non-code or fully tested
    6. Minimal scope (config/metadata only)
    7. No audit/compliance impact
    """

    reasons = []

    # Check 1: No end-user impact
    if "user" in description.lower() or any("user" in s.lower() for s in affected_systems):
        reasons.append("❌ May affect end users (contains 'user' references)")

    # Check 2: No service outage
    if downtime > 0:
        reasons.append(f"❌ Requires downtime ({downtime} hours)")

    # Check 3: Minimal interdependencies
    if len(affected_systems) > 1:
        reasons.append(f"❌ Multiple systems affected ({len(affected_systems)})")

    # Check 4: Rollback simple (assume metadata-only is simple)
    desc_lower = description.lower()
    if any(word in desc_lower for word in ["delete", "remove", "backup", "restore"]):
        reasons.append("❌ Potential rollback complexity")

    # Check 5: Minimal scope
    if not any(word in desc_lower for word in ["metadata", "config", "log", "monitor", "threshold", "internal"]):
        reasons.append("❌ Scope may not be minimal (check description)")

    # Check 6: Testing adequate
    if not test_cases and any(word in desc_lower for word in ["code", "application", "script"]):
        reasons.append("❌ Code changes require test evidence")

    # Check 7: No compliance impact
    if any(word in desc_lower for word in ["audit", "compliance", "security", "access", "permission"]):
        reasons.append("❌ Compliance/security impact detected")

    # If no blockers, it's a valid No Impact change
    is_no_impact = len(reasons) == 0

    if is_no_impact:
        reasons = ["✅ All No Impact criteria met"]

    return is_no_impact, reasons

# ─────────────────────────────────────────────────────────────
# Main Classification Function (Used by API)
# ─────────────────────────────────────────────────────────────

def classify_rfc(
    description: str,
    affected_systems: List[str],
    downtime: float = 0,
    test_cases: str = None
) -> Tuple:
    """
    Comprehensive RFC classification.
    Returns: (change_type, impact, priority, risk_level)
    """

    # Classify type
    change_type = classify_change_type(description, downtime, [])

    # If type is Standard, check SCC match
    if change_type == "Standard":
        if not match_scc(description, affected_systems):
            change_type = "Normal"  # Downgrade if no SCC match

    # Assess impact
    impact = assess_impact(affected_systems, downtime, description)

    # Assess priority
    priority = assess_priority(impact, description)

    # Assess risk (only for Normal/Expedited/Emergency)
    risk_level = None
    if change_type in ["Normal", "Expedited", "Emergency"]:
        risk_level = assess_risk(affected_systems, downtime, impact, description, test_cases)

    return change_type, impact, priority, risk_level
