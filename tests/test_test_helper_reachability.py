import unittest
import tempfile
from pathlib import Path
from skiplist.analysis.parsing import parse_file
from skiplist.analysis.symbols import build_symbol_table
from skiplist.analysis.callgraph import build_call_graph
from skiplist.analysis.entrypoints import detect_entry_points
from skiplist.analysis.reachability import find_dead_code


class TestTestHelperReachability(unittest.TestCase):
    def test_helper_called_from_test_method_is_reachable(self):
        """A helper function called only from inside a test_* method should NOT appear in dead-code findings."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            f = tmppath / "test_example.py"
            f.write_text(
                "def test_helper_util(x):\n"
                "    return x + 10\n\n"
                "def test_case_one():\n"
                "    val = test_helper_util(5)\n"
                "    assert val == 15\n\n"
                "def genuine_dead_function():\n"
                "    pass\n",
                encoding="utf-8"
            )

            modules = {f: parse_file(f)}
            symbols = build_symbol_table(modules, tmppath)
            graph = build_call_graph(modules, symbols, tmppath)
            entry_points = detect_entry_points(modules, symbols, repo_root=tmppath)

            dead_symbols = find_dead_code(graph, entry_points, symbols, modules, tmppath)
            dead_names = {s.qualified_name for s in dead_symbols}

            # test_case_one and test_helper_util MUST NOT appear in dead_names!
            self.assertNotIn("test_example.test_case_one", dead_names)
            self.assertNotIn("test_example.test_helper_util", dead_names)

            # genuine_dead_function MUST appear in dead_names
            self.assertIn("test_example.genuine_dead_function", dead_names)


if __name__ == "__main__":
    unittest.main()
