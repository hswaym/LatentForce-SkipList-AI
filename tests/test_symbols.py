import unittest
import tempfile
import ast
from pathlib import Path
from skiplist.analysis.discovery import find_python_files
from skiplist.analysis.parsing import parse_file
from skiplist.analysis.symbols import build_symbol_table, get_module_dotted_name


class TestSymbolsAndDiscovery(unittest.TestCase):
    def test_discovery_and_parsing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            f1 = tmppath / "pkg" / "mod.py"
            f1.parent.mkdir(parents=True, exist_ok=True)
            f1.write_text("def hello(): pass\n", encoding="utf-8")

            f2 = tmppath / ".venv" / "bad.py"
            f2.parent.mkdir(parents=True, exist_ok=True)
            f2.write_text("invalid syntax :::", encoding="utf-8")

            files = find_python_files(tmppath)
            self.assertEqual(len(files), 1)
            self.assertEqual(files[0].name, "mod.py")

            tree = parse_file(files[0])
            self.assertIsNotNone(tree)

            bad_tree = parse_file(f2)
            self.assertIsNone(bad_tree)

    def test_build_symbol_table(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            code = (
                "class MyClass:\n"
                "    def method_one(self):\n"
                "        def nested_func():\n"
                "            pass\n"
                "        return 1\n"
            )
            f = tmppath / "service.py"
            f.write_text(code, encoding="utf-8")

            modules = {f: parse_file(f)}
            symbols = build_symbol_table(modules, tmppath)

            sym_names = {s.qualified_name: s.kind for s in symbols}
            self.assertIn("service.MyClass", sym_names)
            self.assertEqual(sym_names["service.MyClass"], "class")

            self.assertIn("service.MyClass.method_one", sym_names)
            self.assertEqual(sym_names["service.MyClass.method_one"], "method")

            self.assertIn("service.MyClass.method_one.nested_func", sym_names)
            self.assertEqual(sym_names["service.MyClass.method_one.nested_func"], "function")


if __name__ == "__main__":
    unittest.main()
