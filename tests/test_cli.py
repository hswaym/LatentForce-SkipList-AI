import unittest
import tempfile
import sys
from pathlib import Path
from io import StringIO
from unittest.mock import patch
from skiplist.cli import main


class TestCli(unittest.TestCase):
    def test_analyze_command(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            sample_file = Path(tmpdir) / "sample.py"
            sample_file.write_text(
                "def foo():\n"
                "    pass\n\n"
                "class Bar:\n"
                "    def baz(self):\n"
                "        pass\n",
                encoding="utf-8"
            )

            test_args = ["skiplist", "analyze", tmpdir]
            with patch.object(sys, "argv", test_args):
                with patch("sys.stdout", new=StringIO()) as fake_out:
                    main()
                    output = fake_out.getvalue().strip()
                    self.assertIn("Safe to skip:", output)


if __name__ == "__main__":
    unittest.main()
