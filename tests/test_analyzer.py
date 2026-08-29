import unittest
import tempfile
import os
from pathlib import Path
from skiplist.analyzer import analyze_directory


class TestSkipListAnalyzer(unittest.TestCase):
    def test_analyzer_detects_dead_code_and_duplicates(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            f1 = Path(tmpdir) / "mod1.py"
            f1.write_text(
                "def active_func():\n"
                "    return 42\n\n"
                "def unused_func():\n"
                "    return 100\n",
                encoding="utf-8"
            )

            f2 = Path(tmpdir) / "mod2.py"
            f2.write_text(
                "from mod1 import active_func\n\n"
                "def dup_one(x):\n"
                "    a = x * 2\n"
                "    return a + 1\n\n"
                "def dup_two(y):\n"
                "    b = y * 2\n"
                "    return b + 1\n\n"
                "def main():\n"
                "    print(active_func())\n"
                "    print(dup_one(5))\n",
                encoding="utf-8"
            )

            results = analyze_directory(tmpdir)
            summary = results["summary"]

            self.assertEqual(summary["total_files"], 2)
            dead_fn_names = [f["name"] for f in results["dead_code"]["functions"]]
            self.assertIn("unused_func", dead_fn_names)
            self.assertIn("dup_two", dead_fn_names)
            self.assertNotIn("active_func", dead_fn_names)

            self.assertEqual(len(results["duplicates"]), 1)
            self.assertEqual(results["duplicates"][0]["count"], 2)


if __name__ == "__main__":
    unittest.main()
