import unittest
import tempfile
import json
from pathlib import Path
from skiplist.analysis.parsing import parse_file
from skiplist.analysis.symbols import build_symbol_table
from skiplist.analysis.duplicates import cluster_duplicates
from skiplist.analysis.scoring import compute_priority_score


class TestDuplicatesAndScoring(unittest.TestCase):
    def test_structural_duplicate_cluster_detected_and_keeper_selected(self):
        """Normalized AST hashing detects cross-module structural duplicates and selects reachable keeper."""
        legacy_dir = Path("fixtures/legacy_sample").resolve()
        py_files = sorted(list(legacy_dir.glob("*.py")))

        modules = {f: parse_file(f) for f in py_files if parse_file(f) is not None}
        symbols = build_symbol_table(modules, legacy_dir)

        reachable = {"formatting.format_amount"}
        clusters = cluster_duplicates(modules, symbols, reachable, legacy_dir)

        self.assertEqual(len(clusters), 1)
        cluster = clusters[0]
        self.assertEqual(cluster.keeper.qualified_name, "formatting.format_amount")
        self.assertEqual(len(cluster.non_keepers), 1)
        self.assertEqual(cluster.non_keepers[0].qualified_name, "legacy_format.render_amount")

    def test_priority_score_ranks_duplicates_higher_than_dead_code(self):
        """Priority score formula ranks duplicate merges higher than plain dead code of equal line size."""
        score_dup = compute_priority_score(5, "high", "duplicate")
        self.assertEqual(score_dup, 10)

        score_dead = compute_priority_score(5, "high", "dead_code")
        self.assertEqual(score_dead, 5)


if __name__ == "__main__":
    unittest.main()
