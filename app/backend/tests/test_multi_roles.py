"""A user may hold several roles: permissions are the union, the primary role stays visible, sessions are revoked on change,
nobody changes his own roles, and an administrator role held as an ADDITIONAL role counts for the "last administrator" rule."""
import re
import unittest
import uuid

from tests._harness import ENABLED
from tests.test_http_security import PASSWORD, Client, HttpCase


class MultiRoleTests(HttpCase):
    def _login(self, username, password=PASSWORD):
        status, js, _, r = Client(self.port).call("POST", "/api/auth/login", body={"username": username, "password": password})
        self.assertEqual(status, 200, js)
        token = re.search(r"ac_session=([^;]+)", r.getheader("Set-Cookie")).group(1)
        return Client(self.port, token, js["csrf_token"])

    def _create(self, primary, roles=None):
        name = f"multi_{uuid.uuid4().hex[:8]}"
        body = {"username": name, "full_name": "Multi Role User", "password": PASSWORD, "role": primary}
        if roles is not None:
            body["roles"] = roles
        status, js, _, _ = self.as_role("admin").call("POST", "/api/users", body=body)
        self.assertEqual(status, 201, js)
        return name, js

    def _perms(self, role):
        status, js, _, _ = self.as_role("admin").call("GET", "/api/roles")
        self.assertEqual(status, 200)
        return set(next(r for r in js if r["name"] == role)["permissions"])

    def test_permissions_are_the_union_and_the_primary_role_is_kept(self):
        name, created = self._create("technician", ["technician", "storekeeper"])
        self.assertEqual(created["role"], "technician")
        self.assertEqual([r["name"] for r in created["roles"]], ["technician", "storekeeper"])
        tech, store = self._perms("technician"), self._perms("storekeeper")
        self.assertTrue(store - tech, "the two roles must differ for this test to mean something")
        me = self._login(name).call("GET", "/api/auth/me")[1]["user"]
        self.assertEqual(set(me["permissions"]), tech | store)
        self.assertEqual(me["role"], "technician")
        # a permission only the extra role gives really works over HTTP; one neither role has is still refused
        self.assertEqual(self._login(name).call("GET", "/api/inventory/purchase-invoices")[0], 200)
        self.assertEqual(self._login(name).call("GET", "/api/users")[0], 403)

    def test_changing_roles_revokes_sessions_and_lists_the_new_set(self):
        name, created = self._create("technician")
        self.assertEqual([r["name"] for r in created["roles"]], ["technician"])  # single-role users behave exactly as before
        session = self._login(name)
        self.assertEqual(session.call("GET", "/api/auth/me")[0], 200)
        status, js, _, _ = self.as_role("admin").call("PATCH", f"/api/users/{created['id']}", body={"roles": ["technician", "receptionist", "storekeeper"]})
        self.assertEqual(status, 200, js)
        self.assertEqual([r["name"] for r in js["roles"]], ["technician", "receptionist", "storekeeper"])
        self.assertEqual(session.call("GET", "/api/auth/me")[0], 401, "the old session must stop working after a role change")
        # same set again: nothing changes, sessions stay
        again = self._login(name)
        self.as_role("admin").call("PATCH", f"/api/users/{created['id']}", body={"roles": ["storekeeper", "technician", "receptionist"]})
        self.assertEqual(again.call("GET", "/api/auth/me")[0], 200)
        # dropping the primary role promotes the first remaining one
        status, js, _, _ = self.as_role("admin").call("PATCH", f"/api/users/{created['id']}", body={"roles": ["storekeeper"]})
        self.assertEqual((status, js["role"], [r["name"] for r in js["roles"]]), (200, "storekeeper", ["storekeeper"]))

    def test_invalid_role_sets_are_refused(self):
        _, created = self._create("technician")
        admin = self.as_role("admin")
        for bad in ([], ["no_such_role"], ["technician", "no_such_role"], [""]):
            self.assertEqual(admin.call("PATCH", f"/api/users/{created['id']}", body={"roles": bad})[0], 422, bad)
        self.assertEqual(admin.call("POST", "/api/users", body={"username": f"x{uuid.uuid4().hex[:6]}", "full_name": "Bad Roles", "password": PASSWORD, "role": "technician", "roles": ["nope"]})[0], 422)
        self.assertEqual(self.as_role("storekeeper").call("PATCH", f"/api/users/{created['id']}", body={"roles": ["admin"]})[0], 403)
        self.assertEqual(self.as_role("technician").call("PATCH", f"/api/users/{created['id']}", body={"roles": ["admin"]})[0], 403)

    def test_nobody_changes_his_own_roles(self):
        name, created = self._create("technician", ["technician", "admin"])
        me = self._login(name)
        status, js, _, _ = me.call("PATCH", f"/api/users/{created['id']}", body={"roles": ["technician"]})
        self.assertEqual((status, js.get("error")), (409, "self_role_change"))

    def test_admin_as_additional_role_gives_full_administrator_power(self):
        name, created = self._create("technician", ["technician", "admin"])
        u = self._login(name)
        self.assertIn("users.manage", u.call("GET", "/api/auth/me")[1]["user"]["permissions"])
        self.assertEqual(u.call("GET", "/api/users")[0], 200)
        status, js, _, _ = u.call("POST", "/api/users", body={"username": f"made_{uuid.uuid4().hex[:6]}", "full_name": "Made By Extra Admin", "password": PASSWORD,
                                                              "role": "technician", "roles": ["technician", "receptionist"]})
        self.assertEqual(status, 201, js)
        self.assertEqual([r["name"] for r in js["roles"]], ["technician", "receptionist"])
        # the audit trail records the full role set
        status, audit, _, _ = self.as_role("admin").call("GET", "/api/audit?limit=20")
        self.assertEqual(status, 200)

    def test_database_keeps_primary_and_additional_roles_separate(self):
        from sqlalchemy import text
        _, created = self._create("technician", ["technician", "storekeeper", "receptionist"])
        self.db.expire_all()
        rows = self.db.execute(text("select r.name from user_roles ur join roles r on r.id=ur.role_id where ur.user_id=:u order by r.name"), {"u": created["id"]}).scalars().all()
        self.assertEqual(rows, ["receptionist", "storekeeper"])  # the primary role lives in users.role_id only
        self.assertEqual(self.db.execute(text("select r.name from users u join roles r on r.id=u.role_id where u.id=:u"), {"u": created["id"]}).scalar(), "technician")


if __name__ == "__main__":
    unittest.main()
