import unittest
import tempfile
from pathlib import Path
from skiplist.analysis.parsing import parse_file
from skiplist.analysis.symbols import build_symbol_table
from skiplist.analysis.entrypoints import detect_entry_points


class TestFrameworkEntryPoints(unittest.TestCase):
    def test_flask_fastapi_click_detection(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            f = tmppath / "web.py"
            f.write_text(
                "import flask\n"
                "app = flask.Flask(__name__)\n\n"
                "@app.route('/index')\n"
                "def index_view():\n"
                "    return 'hello'\n\n"
                "def unused_func():\n"
                "    pass\n",
                encoding="utf-8"
            )

            modules = {f: parse_file(f)}
            symbols = build_symbol_table(modules, tmppath)

            entries_off = detect_entry_points(modules, symbols, repo_root=tmppath, frameworks_enabled=False)
            self.assertNotIn("web.index_view", entries_off)

            entries_on = detect_entry_points(modules, symbols, repo_root=tmppath, frameworks_enabled=True)
            self.assertIn("web.index_view", entries_on)


if __name__ == "__main__":
    unittest.main()
