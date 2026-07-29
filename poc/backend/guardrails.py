"""
Environment-Staged Predecessor Gate — service-layer helper.

The authoritative enforcement lives in db_init.py as a SQLite
BEFORE INSERT trigger (trg_environment_predecessor_gate): it fires on any
INSERT into change_requests, no matter which code path performs it, so the
rule can't be bypassed by skipping this module. This helper exists purely
so the API can return a clean 4xx with a specific reason *before* attempting
the insert, instead of surfacing a raw sqlite3.IntegrityError to the client.

Brief references: sections 3.4, 5.4, 13.12, 15.6, 17.1, 17.2.
"""

from typing import Optional

# Environment one stage lower than the given environment. Only environments
# that require a predecessor appear here.
#
# NOTE: db_init.py's trg_environment_predecessor_gate encodes this exact
# same mapping independently, in SQL (`CASE NEW.environment WHEN 'QA' THEN
# 'Dev' ... END`), because the trigger is the real enforcement and this
# dict only drives the friendlier API pre-check. These are two
# hand-synchronized copies of one small rule — if a stage is ever added,
# update both.
PREDECESSOR_ENVIRONMENT = {
    "QA": "Dev",
    "Production": "QA",
}


def environment_predecessor_gate_error(cursor, environment: str, change_type: str,
                                        predecessor_rfc_id: Optional[str]) -> Optional[str]:
    """
    Return a human-readable error string if creating an RFC with the given
    (environment, change_type, predecessor_rfc_id) would violate the
    Environment-Staged Predecessor Gate; return None if it's allowed.

    Mirrors trg_environment_predecessor_gate exactly — this is a pre-check,
    not a replacement for it.
    """
    if change_type == "Emergency":
        return None  # Emergency is exempt at every environment value

    required_predecessor_env = PREDECESSOR_ENVIRONMENT.get(environment)
    if required_predecessor_env is None:
        return None  # Dev (or any environment without a lower stage) needs no predecessor

    if not predecessor_rfc_id:
        return (
            f"An RFC in {environment} of type '{change_type}' requires "
            f"environment_predecessor_rfc_id referencing a Completed {change_type} "
            f"RFC in {required_predecessor_env}."
        )

    row = cursor.execute(
        """
        SELECT id FROM change_requests
        WHERE id = ? AND change_type = ? AND status = 'Completed' AND environment = ?
        """,
        (predecessor_rfc_id, change_type, required_predecessor_env),
    ).fetchone()

    if row is None:
        return (
            f"environment_predecessor_rfc_id '{predecessor_rfc_id}' is not a Completed "
            f"'{change_type}' RFC in {required_predecessor_env} — the Environment-Staged "
            f"Predecessor Gate requires that before an RFC can be created in {environment}."
        )

    return None
