import contextlib
import io
import tempfile
import unittest
from pathlib import Path

from sm import Interpreter, Size, SMError


class SMBetaTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.runtime = Interpreter(self.root / "workspace", auto_yes=True)

    def tearDown(self):
        self.temp.cleanup()

    def run_text(self, text):
        with contextlib.redirect_stdout(io.StringIO()):
            self.runtime.run_lines(text.splitlines())

    def test_dynamic_values_and_size(self):
        self.run_text('VAR n = 512 MB\nSET n = 1 GB\nSHOW n')
        self.assertEqual(self.runtime.env["n"], Size(1_000_000_000))

    def test_list_and_fixed_array(self):
        self.run_text('LIST things = ["x", 1, TRUE]\nARRAY slots = ARRAY(2)\nSET slots[0] = 64 MB')
        self.assertEqual(self.runtime.env["things"][0], "x")
        self.assertEqual(self.runtime.env["slots"].items[0], Size(64_000_000))
        self.assertEqual(len(self.runtime.env["slots"].items), 2)

    def test_file_write_read_copy_verify_and_trash_restore(self):
        self.run_text('DIRECTORY CREATE "docs"\nFILE WRITE "docs/a.txt" "hello"\nCOPY "docs/a.txt" TO "docs/b.txt"\nVERIFY "docs/a.txt" AGAINST "docs/b.txt" WITH SHA256\nTRASH "docs/b.txt"\nRESTORE "docs/b.txt"')
        self.assertEqual((self.root / "workspace" / "docs" / "b.txt").read_text(), "hello")

    def test_path_escape_is_rejected(self):
        with self.assertRaises(SMError):
            self.runtime.path("../outside.txt")

    def test_internal_workspace_paths_are_reserved(self):
        with self.assertRaises(SMError):
            self.runtime.path(".sm-data/settings.json")

    def test_symlink_cannot_escape_workspace(self):
        outside = self.root / "outside.txt"
        outside.write_text("private", encoding="utf-8")
        link = self.root / "workspace" / "escape.txt"
        try:
            link.symlink_to(outside)
        except (OSError, NotImplementedError):
            self.skipTest("symlinks are unavailable on this platform")
        with self.assertRaises(SMError):
            self.runtime.path("escape.txt")

    def test_load_rejects_path_like_names(self):
        with self.assertRaises(SMError):
            self.runtime.load_data("../../outside")

    def test_persistent_data_round_trip(self):
        self.run_text('DATA PERSIST settings\nVAR cap = 5 GB\nEND_DATA\nSAVE settings')
        self.assertEqual(self.runtime.env["settings"]["cap"], Size(5_000_000_000))
        self.runtime.data_blocks.clear()
        self.runtime.env.pop("settings", None)
        self.run_text('LOAD settings\nSHOW settings.cap')
        self.assertEqual(self.runtime.data_blocks["settings"].values["cap"], Size(5_000_000_000))

    def test_object_field_can_be_updated(self):
        self.run_text('OBJECT disk = {"capacity": 512 GB}\nSET disk.capacity = 1 TB')
        self.assertEqual(self.runtime.env["disk"]["capacity"], Size(1_000_000_000_000))

    def test_plan_preview_then_apply(self):
        self.run_text('PLAN "p"\nFILE WRITE "preview.txt" "planned"\nEND_PLAN')
        self.assertFalse((self.root / "workspace" / "preview.txt").exists())
        self.run_text('APPLY "p"')
        self.assertEqual((self.root / "workspace" / "preview.txt").read_text(), "planned")

    def test_su_does_not_escalate(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.runtime.run_lines(['SU OPERATION DEVICE LIST'])
        self.assertIn("no privilege escalation was attempted", output.getvalue())


if __name__ == "__main__":
    unittest.main()
