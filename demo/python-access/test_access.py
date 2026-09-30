import unittest

from access import can_access


class AccessTests(unittest.TestCase):
    def test_active_admin(self):
        self.assertTrue(can_access("admin", False))

    def test_active_editor(self):
        self.assertTrue(can_access("editor", False))

    def test_viewer_denied(self):
        self.assertFalse(can_access("viewer", False))

    def test_suspended_admin_denied(self):
        self.assertFalse(can_access("admin", True))

    def test_unknown_role_denied(self):
        self.assertFalse(can_access("unknown", False))


if __name__ == "__main__":
    unittest.main()
