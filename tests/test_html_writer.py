import unittest
import tempfile
from pathlib import Path
from skiplist.report.html_writer import write_html


class TestHtmlWriter(unittest.TestCase):
    def test_html_report_rendered_self_contained_and_offline_safe(self):
        """HTML report generator renders self-contained dashboard with zero external CDN dependencies."""
        report_data = {
            "meta": {
                "repo_path": "/path/to/myrepo",
                "analyzed_at": "2026-08-29T12:00:00Z",
                "tool_version": "0.1.0",
                "files_analyzed": 5,
                "total_functions": 10,
                "total_lines": 100,
                "entry_points": ["app.main"]
            },
            "summary": {
                "dead_functions": 2,
                "dead_lines": 10,
                "duplicate_clusters": 1,
                "duplicate_lines": 5,
                "safe_to_skip_lines": 15,
                "safe_to_skip_pct": 15.0
            },
            "findings": [
                {
                    "id": "F001",
                    "type": "duplicate",
                    "symbol": "mod.dup_func",
                    "file": "mod.py",
                    "line_start": 1,
                    "line_end": 5,
                    "lines": 5,
                    "reason": "Duplicate of original_func",
                    "evidence": {"callers": [], "duplicate_of": ["original_func"]},
                    "confidence": "high",
                    "caveats": [],
                    "priority_score": 10
                }
            ]
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            out_file = Path(tmpdir) / "report.html"
            write_html(report_data, out_file)

            self.assertTrue(out_file.exists())
            html_content = out_file.read_text(encoding="utf-8")

            self.assertIn("15.0% safe to skip or consolidate", html_content)
            self.assertIn("myrepo", html_content)
            self.assertNotIn("http://", html_content)
            self.assertNotIn("https://", html_content)


if __name__ == "__main__":
    unittest.main()
