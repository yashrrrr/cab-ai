"""
Reset CAB review results on RFCs so they can be reviewed again.

Clears status / cab_decision / cab_reasoning / cab_flags, returning an RFC to
the "Submitted" state (which re-enables the "Trigger AI CAB Review" button).

Usage:
    python reset_cab.py                    # reset ALL CAB-reviewed RFCs
    python reset_cab.py CHG20260724002     # reset one RFC by rfc_number
    python reset_cab.py CHG...001 CHG...002 # reset several
    python reset_cab.py --list             # just show current review state, change nothing

Standalone utility — does not touch the web app or the API.
"""

import os
import sys
import sqlite3

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "rfc_poc.db")


def get_conn():
    if not os.path.exists(DB_PATH):
        print(f"[ERROR] Database not found: {DB_PATH}")
        sys.exit(1)
    return sqlite3.connect(DB_PATH)


def show_state(conn):
    rows = conn.execute(
        "SELECT rfc_number, status, cab_decision FROM change_requests ORDER BY rfc_number"
    ).fetchall()
    reviewed = [r for r in rows if r[2] is not None or r[1] == "CAB Reviewed"]
    print(f"Total RFCs: {len(rows)}")
    if reviewed:
        print("Currently CAB-reviewed:")
        for rfc_number, status, decision in reviewed:
            print(f"  {rfc_number} | {status} | decision={decision}")
    else:
        print("Currently CAB-reviewed: (none - all clear, ready to run CAB)")


def reset(conn, rfc_numbers=None):
    """Reset all reviewed RFCs, or only the given rfc_numbers."""
    fields = "status='Submitted', cab_decision=NULL, cab_reasoning=NULL, cab_flags=NULL, reviewed_at=NULL"
    if rfc_numbers:
        placeholders = ",".join("?" for _ in rfc_numbers)
        sql = f"UPDATE change_requests SET {fields} WHERE rfc_number IN ({placeholders})"
        conn.execute(sql, rfc_numbers)
    else:
        sql = f"UPDATE change_requests SET {fields} WHERE cab_decision IS NOT NULL"
        conn.execute(sql)
    conn.commit()
    return conn.total_changes


def main():
    args = [a for a in sys.argv[1:] if a.strip()]
    conn = get_conn()
    try:
        if args and args[0] in ("--list", "-l"):
            show_state(conn)
            return

        targets = args or None  # no args => reset all reviewed
        changed = reset(conn, targets)

        if targets and changed == 0:
            print(f"[WARN] No matching RFCs found for: {', '.join(targets)}")
        else:
            scope = ", ".join(targets) if targets else "all reviewed RFCs"
            print(f"[OK] Reset {changed} row(s) ({scope}).")

        print("---")
        show_state(conn)
        print("\nTip: re-open the RFC in the web app (click it again) to see the "
              "'Trigger AI CAB Review' button return.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
