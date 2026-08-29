import unittest
from pathlib import Path
import tempfile
from skiplist.analysis.parsing import parse_file
from skiplist.analysis.symbols import build_symbol_table
from skiplist.analysis.callgraph import build_call_graph
from skiplist.analysis.entrypoints import detect_entry_points
from skiplist.analysis.reachability import find_dead_code


class TestReachability(unittest.TestCase):
    def test_legacy_sample_reachability(self):
        legacy_dir = Path("fixtures/legacy_sample").resolve()
        py_files = sorted(list(legacy_dir.glob("*.py")))

        modules = {}
        for f in py_files:
            tree = parse_file(f)
            if tree is not None:
                modules[f] = tree

        symbols = build_symbol_table(modules, legacy_dir)
        graph = build_call_graph(modules, symbols, legacy_dir)
        entry_points = detect_entry_points(modules, symbols, repo_root=legacy_dir)

        self.assertEqual(entry_points, {"app.main"})

        dead_symbols = find_dead_code(graph, entry_points, symbols)
        dead_names = {s.qualified_name for s in dead_symbols}

        expected_dead = {
            "dispatch.export_data",
            "dispatch.import_data",
            "legacy_format.render_amount",
            "orders.cancel_order",
            "payments.deprecated_refund",
            "unused_module.orphan_one",
            "unused_module.orphan_two"
        }

        self.assertEqual(dead_names, expected_dead)

        # Ensure live symbols are NOT marked dead
        live_symbols = {
            "app.main",
            "orders.create_order",
            "payments.charge",
            "formatting.format_amount",
            "dispatch.run_action"
        }
        for live in live_symbols:
            self.assertNotIn(live, dead_names)


if __name__ == "__main__":
    unittest.main()
