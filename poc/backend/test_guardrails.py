"""
Regression tests for the Environment-Staged Predecessor Gate.

Brief reference: docs/brief.md sections 3.4, 5.4, 13.12, 15.6, 17.1, 17.2,
and 18.1 (Guardrail Test Suite) test cases 9 and 10:

  9. Assert: No QA/Production RFC (type != Emergency) reaches creation
     without a same-type, Completed predecessor RFC one environment stage
     lower.
 10. Assert: Emergency RFCs bypass the environment-predecessor gate at every
     environment value.

Two layers are exercised, matching the "enforced at the data-access layer,
not only the API handler" architectural constraint (brief 5.3/5.4/15.6):

  - Layer 1 (`GateTriggerTests`): raw SQLite inserts straight against the
    `trg_environment_predecessor_gate` trigger created in db_init.py. This
    proves the rule holds even for a hypothetical code path that never goes
    through main.py at all.
  - Layer 2 (`SubmitRfcApiTests`): the real `/rfc/submit` and
    `/rfc/{id}/complete` FastAPI endpoints, proving the API surfaces a clean
    4xx (via guardrails.py's pre-check) rather than a raw DB error, and that
    the documented happy path (mark predecessor Completed, then create the
    next-stage RFC) actually works end to end.

Uses stdlib unittest (no pytest dependency) to match the POC's existing
zero-test-framework footprint. Run with:

    python test_guardrails.py
"""

import os
import sqlite3
import sys
import tempfile
import time
import unittest
import uuid

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# cab_orchestrator.py (imported transitively by main.py) requires this env
# var to be *set* at import time, even though these tests never exercise
# the CAB/LLM code path. Pre-existing POC constraint, unrelated to this
# feature — set a placeholder only if a real key isn't already present.
os.environ.setdefault("OPENAI_API_KEY", "test-placeholder-not-used-by-gate-tests")

import db_init
import main
from fastapi.testclient import TestClient


def _mark_completed(cursor, id):
    # UPDATE, not INSERT — the gate trigger is BEFORE INSERT only, so this is
    # the (realistic) way an already-created RFC becomes eligible to serve
    # as somebody else's predecessor, mirroring POST /rfc/{id}/complete.
    cursor.execute("UPDATE change_requests SET status = 'Completed' WHERE id = ?", (id,))


def _insert_rfc(cursor, id, change_type, status, environment, predecessor_id=None):
    cursor.execute(
        """
        INSERT INTO change_requests (
            id, rfc_number, title, description, change_type, impact, priority,
            risk_level, status, auto_approved, created_at, requestor_name,
            affected_systems, environment, environment_predecessor_rfc_id
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            id, id, f"Test {id}", "test rfc", change_type, "3-Low", "Low",
            1, status, 0, "2026-07-29T00:00:00", "Test Requestor",
            "[]", environment, predecessor_id,
        ),
    )


class GateTriggerTests(unittest.TestCase):
    """Layer 1: the SQLite trigger itself, independent of the API."""

    def setUp(self):
        fd, self.db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        db_init.init_db(self.db_path)
        self.conn = sqlite3.connect(self.db_path)
        self.cursor = self.conn.cursor()

    def tearDown(self):
        self.conn.close()
        os.remove(self.db_path)

    # --- Test case 9 -----------------------------------------------------

    def test_qa_rejected_without_predecessor(self):
        with self.assertRaises(sqlite3.IntegrityError):
            _insert_rfc(self.cursor, "qa-no-pred", "Standard", "Submitted", "QA")

    def test_qa_rejected_when_predecessor_not_completed(self):
        _insert_rfc(self.cursor, "dev-not-done", "Standard", "Submitted", "Dev")
        with self.assertRaises(sqlite3.IntegrityError):
            _insert_rfc(self.cursor, "qa-pred-not-done", "Standard", "Submitted", "QA", "dev-not-done")

    def test_qa_rejected_when_predecessor_wrong_type(self):
        _insert_rfc(self.cursor, "dev-wrong-type", "Normal", "Completed", "Dev")
        with self.assertRaises(sqlite3.IntegrityError):
            _insert_rfc(self.cursor, "qa-wrong-type", "Standard", "Submitted", "QA", "dev-wrong-type")

    def test_qa_rejected_when_predecessor_wrong_environment(self):
        # Build a real, valid, Completed QA row (Dev predecessor -> QA -> mark
        # Completed), then try to use *that QA row* as another QA insert's
        # predecessor — it's the right type and Completed, but its
        # environment is QA, not the required Dev, so it must still fail.
        _insert_rfc(self.cursor, "dev-for-qa-as-pred", "Standard", "Submitted", "Dev")
        _mark_completed(self.cursor, "dev-for-qa-as-pred")
        _insert_rfc(self.cursor, "qa-as-pred", "Standard", "Submitted", "QA", "dev-for-qa-as-pred")
        _mark_completed(self.cursor, "qa-as-pred")

        with self.assertRaises(sqlite3.IntegrityError):
            _insert_rfc(self.cursor, "qa-wrong-env-pred", "Standard", "Submitted", "QA", "qa-as-pred")

    def test_qa_accepted_with_valid_completed_dev_predecessor(self):
        _insert_rfc(self.cursor, "dev-done", "Standard", "Submitted", "Dev")
        _mark_completed(self.cursor, "dev-done")
        _insert_rfc(self.cursor, "qa-ok", "Standard", "Submitted", "QA", "dev-done")  # should not raise

    def test_production_rejected_without_predecessor(self):
        with self.assertRaises(sqlite3.IntegrityError):
            _insert_rfc(self.cursor, "prod-no-pred", "Normal", "Submitted", "Production")

    def test_production_accepted_with_valid_completed_qa_predecessor(self):
        _insert_rfc(self.cursor, "dev-for-prod", "Normal", "Submitted", "Dev")
        _mark_completed(self.cursor, "dev-for-prod")
        _insert_rfc(self.cursor, "qa-done", "Normal", "Submitted", "QA", "dev-for-prod")
        _mark_completed(self.cursor, "qa-done")
        _insert_rfc(self.cursor, "prod-ok", "Normal", "Submitted", "Production", "qa-done")  # should not raise

    def test_production_rejected_when_predecessor_is_dev_not_qa(self):
        # Same-type, Completed, but one environment too far back (Dev instead of QA).
        _insert_rfc(self.cursor, "dev-done-2", "Normal", "Submitted", "Dev")
        _mark_completed(self.cursor, "dev-done-2")
        with self.assertRaises(sqlite3.IntegrityError):
            _insert_rfc(self.cursor, "prod-wrong-pred-env", "Normal", "Submitted", "Production", "dev-done-2")

    # --- Test case 10 ------------------------------------------------------

    def test_emergency_bypasses_gate_in_qa(self):
        _insert_rfc(self.cursor, "emg-qa", "Emergency", "Submitted", "QA")  # should not raise

    def test_emergency_bypasses_gate_in_production(self):
        _insert_rfc(self.cursor, "emg-prod", "Emergency", "Submitted", "Production")  # should not raise

    def test_emergency_still_carries_environment_field(self):
        _insert_rfc(self.cursor, "emg-dev", "Emergency", "Submitted", "Dev")
        row = self.cursor.execute(
            "SELECT environment FROM change_requests WHERE id = 'emg-dev'"
        ).fetchone()
        self.assertEqual(row[0], "Dev")

    # --- Gate holds on UPDATE too, not just INSERT --------------------------
    # (review finding: an INSERT-only trigger would let a row's environment
    # or predecessor be changed post-creation with no gate check at all.)

    def test_update_to_qa_without_predecessor_rejected(self):
        _insert_rfc(self.cursor, "dev-then-update", "Standard", "Submitted", "Dev")
        with self.assertRaises(sqlite3.IntegrityError):
            self.cursor.execute(
                "UPDATE change_requests SET environment = 'QA' WHERE id = 'dev-then-update'"
            )

    def test_update_predecessor_to_invalid_value_rejected(self):
        _insert_rfc(self.cursor, "dev-ok", "Standard", "Submitted", "Dev")
        _mark_completed(self.cursor, "dev-ok")
        _insert_rfc(self.cursor, "qa-valid", "Standard", "Submitted", "QA", "dev-ok")
        with self.assertRaises(sqlite3.IntegrityError):
            self.cursor.execute(
                "UPDATE change_requests SET environment_predecessor_rfc_id = NULL WHERE id = 'qa-valid'"
            )

    def test_update_leaving_dev_untouched_is_unaffected(self):
        # Sanity check: the UPDATE trigger only fires for columns it's
        # declared OF (environment, environment_predecessor_rfc_id,
        # change_type) — unrelated column updates on a Dev row must not be
        # accidentally caught by it.
        _insert_rfc(self.cursor, "dev-untouched", "Standard", "Submitted", "Dev")
        self.cursor.execute(
            "UPDATE change_requests SET title = 'Renamed' WHERE id = 'dev-untouched'"
        )  # should not raise

    # --- Domain-check trigger: non-canonical environment values ------------
    # (review finding: the gate trigger's WHEN only matches the exact
    # strings 'QA'/'Production', so a typo'd/lowercased value would skip it
    # entirely without a separate guard.)

    def test_non_canonical_environment_value_rejected_on_insert(self):
        with self.assertRaises(sqlite3.IntegrityError):
            _insert_rfc(self.cursor, "bad-env", "Standard", "Submitted", "Staging")

    def test_lowercase_environment_value_rejected_on_insert(self):
        with self.assertRaises(sqlite3.IntegrityError):
            _insert_rfc(self.cursor, "bad-env-2", "Standard", "Submitted", "qa")

    def test_non_canonical_environment_value_rejected_on_update(self):
        _insert_rfc(self.cursor, "dev-for-bad-update", "Standard", "Submitted", "Dev")
        with self.assertRaises(sqlite3.IntegrityError):
            self.cursor.execute(
                "UPDATE change_requests SET environment = 'Staging' WHERE id = 'dev-for-bad-update'"
            )


class SubmitRfcApiTests(unittest.TestCase):
    """Layer 2: the real /rfc/submit and /rfc/{id}/complete endpoints."""

    def setUp(self):
        fd, self.db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        db_init.init_db(self.db_path)

        # Redirect main.py's DB access to this test's temp DB instead of the
        # real rfc_poc.db, so running these tests never touches demo data.
        self._real_get_db_connection = main.get_db_connection
        db_path = self.db_path

        def fake_get_db_connection(_db_path="rfc_poc.db"):
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            return conn

        main.get_db_connection = fake_get_db_connection
        self.client = TestClient(main.app)

    def tearDown(self):
        main.get_db_connection = self._real_get_db_connection
        os.remove(self.db_path)

    def _submit(self, **overrides):
        payload = {
            "title": "Test change",
            "description": "A test change request for the gate",
            "business_justification": "Testing",
            "affected_systems": ["TestSystem"],
            "requestor_name": "Test Requestor",
        }
        payload.update(overrides)
        return self.client.post("/rfc/submit", json=payload)

    # --- Test case 9 -----------------------------------------------------

    def test_api_rejects_qa_standard_without_predecessor(self):
        resp = self._submit(change_type="Standard", environment="QA")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("environment_predecessor_rfc_id", resp.json()["detail"])

    def test_api_rejects_qa_when_predecessor_not_completed(self):
        dev_resp = self._submit(change_type="Standard", environment="Dev")
        self.assertEqual(dev_resp.status_code, 200)
        dev_id = dev_resp.json()["id"]

        resp = self._submit(
            change_type="Standard", environment="QA", environment_predecessor_rfc_id=dev_id
        )
        self.assertEqual(resp.status_code, 400)

    def test_api_accepts_qa_after_predecessor_marked_completed(self):
        dev_resp = self._submit(change_type="Standard", environment="Dev")
        dev_id = dev_resp.json()["id"]

        complete_resp = self.client.post(f"/rfc/{dev_id}/complete")
        self.assertEqual(complete_resp.status_code, 200)
        self.assertEqual(complete_resp.json()["status"], "Completed")

        # rfc_number is generated from a second-granularity timestamp
        # (pre-existing behavior in main.py, unrelated to this feature) — two
        # inserts in the same wall-clock second can collide. Sidestep that
        # here rather than changing production ID-generation as part of this
        # feature.
        time.sleep(1.05)

        resp = self._submit(
            change_type="Standard", environment="QA", environment_predecessor_rfc_id=dev_id
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["environment"], "QA")
        self.assertEqual(resp.json()["environment_predecessor_rfc_id"], dev_id)

    def test_api_defaults_environment_to_dev_when_omitted(self):
        # Callers that don't send `environment` at all land on Dev, the one
        # tier that never needs a predecessor — not a silent gate bypass.
        resp = self._submit(change_type="Standard")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["environment"], "Dev")

    # --- Test case 10 ------------------------------------------------------

    def test_api_accepts_emergency_in_production_without_predecessor(self):
        resp = self._submit(change_type="Emergency", environment="Production")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["environment"], "Production")

    def test_api_accepts_emergency_in_qa_without_predecessor(self):
        resp = self._submit(change_type="Emergency", environment="QA")
        self.assertEqual(resp.status_code, 200)

    # --- Coverage gaps flagged in review: Production tier and a wrong-type
    # predecessor, exercised through the actual HTTP API (not just the raw
    # trigger in GateTriggerTests) --------------------------------------

    def test_api_rejects_production_without_qa_predecessor(self):
        resp = self._submit(change_type="Normal", environment="Production")
        self.assertEqual(resp.status_code, 400)

    def test_api_accepts_production_after_qa_predecessor_completed(self):
        dev_resp = self._submit(change_type="Normal", environment="Dev")
        dev_id = dev_resp.json()["id"]
        self.client.post(f"/rfc/{dev_id}/complete")

        time.sleep(1.05)
        qa_resp = self._submit(
            change_type="Normal", environment="QA", environment_predecessor_rfc_id=dev_id
        )
        self.assertEqual(qa_resp.status_code, 200)
        qa_id = qa_resp.json()["id"]
        self.client.post(f"/rfc/{qa_id}/complete")

        time.sleep(1.05)
        prod_resp = self._submit(
            change_type="Normal", environment="Production", environment_predecessor_rfc_id=qa_id
        )
        self.assertEqual(prod_resp.status_code, 200)
        self.assertEqual(prod_resp.json()["environment"], "Production")

    def test_api_rejects_predecessor_of_wrong_type(self):
        dev_resp = self._submit(change_type="Standard", environment="Dev")
        dev_id = dev_resp.json()["id"]
        self.client.post(f"/rfc/{dev_id}/complete")

        time.sleep(1.05)
        # Same environment stage, Completed predecessor exists — but this
        # submission is a different change_type, so it still must be rejected.
        resp = self._submit(
            change_type="Normal", environment="QA", environment_predecessor_rfc_id=dev_id
        )
        self.assertEqual(resp.status_code, 400)

    # --- Gate is checked against the *final* classified type, not the raw
    # request (spec boundary: No-Impact escalated to Normal must gate as
    # Normal) -----------------------------------------------------------

    def test_gate_uses_escalated_type_not_raw_no_impact(self):
        # This description trips multiple evaluate_no_impact() criteria
        # (user-facing, downtime, audit/compliance wording) so it reliably
        # escalates "No Impact" -> "Normal" server-side.
        ambiguous_no_impact = self._submit(
            change_type="No Impact",
            environment="QA",
            description="This change affects user accounts, requires downtime, and touches audit/compliance logging.",
            estimated_downtime_hours=1,
        )
        # No Completed "Normal" predecessor exists in Dev, so the escalated
        # type must be the one gated on — rejected, not silently treated as
        # a (never-checked) "No Impact" submission.
        self.assertEqual(ambiguous_no_impact.status_code, 400)

        # Prove it's specifically the *escalated* type being checked: a
        # Completed Normal (not No Impact) predecessor in Dev satisfies it.
        dev_normal = self._submit(change_type="Normal", environment="Dev")
        dev_id = dev_normal.json()["id"]
        self.client.post(f"/rfc/{dev_id}/complete")

        time.sleep(1.05)
        resp = self._submit(
            change_type="No Impact",
            environment="QA",
            description="This change affects user accounts, requires downtime, and touches audit/compliance logging.",
            estimated_downtime_hours=1,
            environment_predecessor_rfc_id=dev_id,
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["change_type"], "Normal")  # confirms escalation happened

    # --- complete_rfc guard: a CAB-rejected RFC can't become a valid
    # predecessor just by calling /complete (review finding) --------------

    def test_cannot_complete_a_cab_rejected_rfc(self):
        dev_resp = self._submit(change_type="Standard", environment="Dev")
        dev_id = dev_resp.json()["id"]

        # Simulate a CAB rejection directly (bypassing the LLM-backed
        # trigger-cab endpoint, which isn't under test here).
        conn = main.get_db_connection()
        conn.execute("UPDATE change_requests SET cab_decision = 'Rejected' WHERE id = ?", (dev_id,))
        conn.commit()
        conn.close()

        resp = self.client.post(f"/rfc/{dev_id}/complete")
        self.assertEqual(resp.status_code, 400)

        # And confirm it really did NOT get marked Completed / usable as a predecessor.
        detail = self.client.get(f"/rfc/{dev_id}").json()
        self.assertNotEqual(detail["status"], "Completed")


if __name__ == "__main__":
    unittest.main(verbosity=2)
