import unittest
from pathlib import Path
from skiplist.analysis.parsing import parse_file
from skiplist.analysis.symbols import build_symbol_table
from skiplist.analysis.callgraph import build_call_graph, build_graph_export


class TestGraphExport(unittest.TestCase):
    def test_call_graph_serialized_with_node_and_edge_metadata(self):
        """Call graph serialization outputs node status attributes and caller-callee edges in findings.json."""
        legacy_dir = Path("fixtures/legacy_sample").resolve()
        py_files = sorted(list(legacy_dir.glob("*.py")))

        modules = {f: parse_file(f) for f in py_files if parse_file(f) is not None}
        symbols = build_symbol_table(modules, legacy_dir)
        graph = build_call_graph(modules, symbols, legacy_dir)

        export = build_graph_export(graph, symbols, [])

        self.assertFalse(export.collapsed)
        self.assertIsNone(export.collapse_reason)
        self.assertEqual(len(export.nodes), 12)
        self.assertTrue(len(export.edges) >= 4)


if __name__ == "__main__":
    unittest.main()
