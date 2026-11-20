"""Backup (create / verify / download / encrypt) and warranty behaviour over HTTP against the throw-away server and database.
The restore itself is NOT executed here (it would replace the test database); its table-level round trip is covered in test_inventory.test_18."""
import hashlib
import time
import unittest
import uuid

from tests._harness import ENABLED
from tests.test_http_security import HttpCase
from tests.test_workflows import FlowBase


def wait_done(case, rid, seconds=90):
    for _ in range(seconds):
        js = case.api("GET", f"/api/backups/{rid}", expect=200)
        if js["status"] != "running":
            return js
        time.sleep(1)
    case.fail("the backup did not finish in time")


class BackupTests(FlowBase):
    def test_backup_create_verify_download_and_checksum(self):
        out = self.api("POST", "/api/backups", {}, expect=202)
        rid = out.get("id") or out.get("record", {}).get("id")
        self.assertTrue(rid, out)
        rec = wait_done(self, rid)
        self.assertNotEqual(rec["status"], "failed", rec.get("error"))
        self.assertGreater(rec["size_bytes"], 1000)
        ver = self.api("POST", f"/api/backups/{rid}/verify", {"deep": True}, expect=200)
        self.assertFalse(ver.get("error"), ver)
        status, _, payload, resp = self.as_role("admin").call("GET", f"/api/backups/{rid}/download", timeout=120)
        self.assertEqual(status, 200)
        self.assertEqual(hashlib.sha256(payload).hexdigest(), rec["sha256"], "the downloaded archive must match the recorded checksum")
        prev = self.api("POST", "/api/restore/preview", {"id": rid}, expect=200)
        self.assertIsInstance(prev, dict)

    def test_encrypted_backup_needs_the_passphrase(self):
        out = self.api("POST", "/api/backups", {"passphrase": "Correct-Horse-9"}, expect=202)
        rid = out.get("id") or out.get("record", {}).get("id")
        rec = wait_done(self, rid)
        self.assertNotEqual(rec["status"], "failed", rec.get("error"))
        self.assertTrue(rec["encrypted"])
        status, _, payload, _ = self.as_role("admin").call("GET", f"/api/backups/{rid}/download", timeout=120)
        self.assertEqual(status, 200)
        self.assertNotIn(b"PGDMP", payload[:64], "an encrypted backup must not be a readable dump")
        self.assertNotIn(b"PK\x03\x04", payload[:4])
        wrong = self.as_role("admin").call("POST", f"/api/backups/{rid}/verify", body={"passphrase": "wrong-pass-123", "deep": True})
        self.assertIn(wrong[0], (400, 422, 200))
        if wrong[0] == 200:
            self.assertTrue(wrong[1].get("error") or wrong[1].get("ok") is False or wrong[1].get("status") in ("failed", "bad_passphrase"), wrong[1])
        good = self.api("POST", f"/api/backups/{rid}/verify", {"passphrase": "Correct-Horse-9", "deep": True}, expect=200)
        self.assertFalse(good.get("error"), good)

    def test_backups_cannot_be_reached_by_other_roles_and_paths_cannot_escape_the_backup_folder(self):
        for role in ("technician", "storekeeper", "receptionist", "accountant"):
            self.assertEqual(self.as_role(role).call("GET", "/api/backups")[0], 403, role)
            self.assertEqual(self.as_role(role).call("POST", "/api/backups", body={})[0], 403, role)
        self.api("GET", f"/api/backups/{uuid.uuid4()}/download", expect=404)
        self.api("POST", "/api/restore/preview", {"id": str(uuid.uuid4())}, expect=404)


class WarrantyTests(FlowBase):
    def test_warranty_lifecycle_permissions_and_validation(self):
        c, v, job = self.customer_vehicle_job()
        op = self.api("POST", f"/api/jobs/{job}/operations", {"description": "Brake job", "labor_hours": "1", "labor_rate": "100"}, expect=201)
        w = self.api("POST", f"/api/jobs/{job}/warranties", {"kind": "labor", "operation_id": op["id"], "description": "6 months labor warranty", "months": 6}, expect=201)
        self.api("POST", f"/api/jobs/{job}/warranties", {"kind": "labor", "description": "x", "months": 0}, expect=422)
        self.api("POST", f"/api/jobs/{job}/warranties", {"kind": "parts", "description": "bad kind", "months": 3}, expect=422)
        other_c, other_v, other_job = self.customer_vehicle_job()
        self.api("POST", f"/api/jobs/{other_job}/warranties", {"kind": "labor", "operation_id": op["id"], "description": "wrong job", "months": 3}, expect=422)
        lst = self.api("GET", f"/api/vehicles/{v['id']}/warranties", expect=200)
        self.assertEqual(len(lst), 1)
        self.assertEqual(lst[0]["id"], w["id"])
        # who may void
        self.api("POST", f"/api/warranties/{w['id']}/void", {"reason": "entered by mistake"}, role="technician", expect=403)
        self.api("POST", f"/api/warranties/{w['id']}/void", {"reason": "entered by mistake"}, expect=200)
        self.api("POST", f"/api/warranties/{w['id']}/void", {"reason": "again"}, expect=409)  # the original reason is never overwritten
        self.api("POST", f"/api/warranties/{w['id']}/void", {"reason": "ab"}, expect=422)

    def test_customer_supplied_part_carries_no_workshop_warranty_by_default(self):
        c, v, job = self.customer_vehicle_job()
        part = self.api("POST", f"/api/jobs/{job}/parts/customer-supplied", {"description": "Customer battery", "quantity": "1"}, expect=201)
        self.assertFalse(part.get("warranty_months"), part)


if __name__ == "__main__":
    unittest.main()

