"""
PII/PHI category-only guardrail — CAB Readiness Agent.

Hard constraint from the brief: flag the CATEGORY of any detected
identifiable data (e.g. "email_address", "ssn_like"), never extract, log, or
persist the matched value itself. This applies to the readiness evaluator's
Data Privacy Assessment area check and to any logging of CR/document text
(including LLM prompts/responses) across this feature.

Deliberately heuristic/regex-based — a PoC-stage guardrail, not a production
DLP engine. Real PII detection would need locale-aware validation (checksum
digits, etc.) that these patterns don't attempt.
"""

import re
from typing import List

PII_PATTERNS = [
    ("ssn_like", re.compile(r"\b\d{3}-\d{2}-\d{4}\b")),
    ("aadhaar_like", re.compile(r"\b\d{4}\s?\d{4}\s?\d{4}\b")),
    ("pan_like", re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b")),
    ("card_number_like", re.compile(r"\b(?:\d[ -]*?){13,16}\b")),
    ("email_address", re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")),
]


def scan_for_pii(text: str) -> List[dict]:
    """
    Returns [{"category": "ssn_like", "count": 2}, ...] — counts only, never
    the matched text. Used to flag Data Privacy Assessment areas and to
    decide what needs redaction before logging.
    """
    if not text:
        return []

    flags = []
    for category, pattern in PII_PATTERNS:
        matches = pattern.findall(text)
        if matches:
            flags.append({"category": category, "count": len(matches)})
    return flags


def redact_for_logging(text: str) -> str:
    """
    Replaces every match of every pattern above with '[REDACTED:<category>]'.
    Use this any time CR/document text (or an LLM prompt/response built from
    it) would otherwise be logged.
    """
    if not text:
        return text

    redacted = text
    for category, pattern in PII_PATTERNS:
        redacted = pattern.sub(f"[REDACTED:{category}]", redacted)
    return redacted
