import unittest
import tempfile
from pathlib import Path
from skiplist.analysis.parsing import parse_file
from skiplist.analysis.symbols import build_symbol_table
from skiplist.analysis.callgraph import build_call_graph
from skiplist.analysis.entrypoints import detect_entry_points
from skiplist.analysis.reachability import find_dead_code


class TestReachabilityGuards(unittest.TestCase):
    def test_dunders_all_exports_and_test_methods_never_flagged_dead(self):
        """Class dunder methods, module __all__ exports, and unittest/pytest discovery methods are never flagged as dead."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            f = tmppath / "test_service.py"
            f.write_text(
                "import unittest\n"
                "import pytest\n\n"
                "@pytest.fixture\n"
                "def db_conn():\n"
                "    return 'conn'\n\n"
                "class TestService(unittest.TestCase):\n"
                "    def setUp(self):\n"
                "        pass\n"
                "    def test_run(self):\n"
                "        pass\n\n"
                "def genuine_dead_func():\n"
                "    return 'dead'\n",
                encoding="utf-8"
            )

            modules = {f: parse_file(f)}
            symbols = build_symbol_table(modules, tmppath)
            graph = build_call_graph(modules, symbols, tmppath)
            entry_points = detect_entry_points(modules, symbols, repo_root=tmppath)

            dead_symbols = find_dead_code(graph, entry_points, symbols, modules, tmppath)
            dead_names = {s.qualified_name for s in dead_symbols}

            self.assertNotIn("test_service.db_conn", dead_names)
            self.assertNotIn("test_service.TestService.setUp", dead_names)
            self.assertNotIn("test_service.TestService.test_run", dead_names)

            self.assertIn("test_service.genuine_dead_func", dead_names)


if __name__ == "__main__":
    unittest.main()
