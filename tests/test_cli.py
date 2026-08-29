import unittest
import tempfile
import sys
from pathlib import Path
from io import StringIO
from unittest.mock import patch
from skiplist.cli import main


class TestCliSkeleton(unittest.TestCase):
    def test_analyze_walking_skeleton(self):
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
                    self.assertEqual(output, "Parsed 1 files, found 2 functions, 1 classes.")


if __name__ == "__main__":
    unittest.main()
