import ast
import fnmatch
import re
from pathlib import Path
from typing import Dict, List, Set, Optional
from skiplist.models import Symbol
from skiplist.analysis.symbols import get_module_dotted_name


FRAMEWORK_DECORATOR_ATTRS = {
    "route", "get", "post", "put", "delete", "patch", "head", "options", "websocket",
    "command", "group", "task", "shared_task"
}

FRAMEWORK_DECORATOR_NAMES = {
    "shared_task", "task", "command", "group", "route"
}


def is_if_main_node(node: ast.If) -> bool:
    """Check if an AST If node represents `if __name__ == '__main__':`."""
    test = node.test
    if not isinstance(test, ast.Compare):
        return False

    left_is_name = isinstance(test.left, ast.Name) and test.left.id == "__name__"
    if not left_is_name:
        return False

    for comp in test.comparators:
        if isinstance(comp, ast.Constant) and comp.value == "__main__":
            return True
        elif isinstance(comp, ast.Str) and comp.s == "__main__":
            return True

    return False


def _extract_if_main_calls(tree: ast.AST, current_module: str, known_symbols: Set[str]) -> Set[str]:
    entries = set()

    class IfMainVisitor(ast.NodeVisitor):
        def visit_If(self, node: ast.If):
            if is_if_main_node(node):
                for body_node in node.body:
                    for n in ast.walk(body_node):
                        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name):
                            func_name = n.func.id
                            qual = f"{current_module}.{func_name}" if current_module else func_name
                            if qual in known_symbols:
                                entries.add(qual)
            self.generic_visit(node)

    IfMainVisitor().visit(tree)
    return entries


def _detect_framework_routes(tree: ast.AST, current_module: str, known_symbols: Set[str]) -> Set[str]:
    entries = set()

    class FrameworkVisitor(ast.NodeVisitor):
        def __init__(self):
            self.scope: List[str] = [current_module] if current_module else []

        def visit_ClassDef(self, node: ast.ClassDef):
            self.scope.append(node.name)
            self.generic_visit(node)
            self.scope.pop()

        def visit_FunctionDef(self, node: ast.FunctionDef):
            self._check_func(node)

        def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
            self._check_func(node)

        def _check_func(self, node: ast.FunctionDef | ast.AsyncFunctionDef):
            qual_name = f"{'.'.join(self.scope)}.{node.name}" if self.scope else node.name

            for decorator in node.decorator_list:
                is_route = False
                if isinstance(decorator, ast.Call):
                    func_expr = decorator.func
                    if isinstance(func_expr, ast.Attribute) and func_expr.attr in FRAMEWORK_DECORATOR_ATTRS:
                        is_route = True
                    elif isinstance(func_expr, ast.Name) and func_expr.id in FRAMEWORK_DECORATOR_NAMES:
                        is_route = True
                elif isinstance(decorator, ast.Attribute) and decorator.attr in FRAMEWORK_DECORATOR_ATTRS:
                    is_route = True
                elif isinstance(decorator, ast.Name) and decorator.id in FRAMEWORK_DECORATOR_NAMES:
                    is_route = True

                if is_route and qual_name in known_symbols:
                    entries.add(qual_name)
                    break

            self.scope.append(node.name)
            self.generic_visit(node)
            self.scope.pop()

    FrameworkVisitor().visit(tree)
    return entries


def _detect_console_scripts(repo_root: Path) -> Set[str]:
    scripts = set()
    pyproject_path = repo_root / "pyproject.toml"

    if pyproject_path.exists():
        try:
            content = pyproject_path.read_text(encoding="utf-8")
            matches = re.findall(r'[\w\-]+\s*=\s*["\']([\w\.]+):([\w\.]+)["\']', content)
            for mod, func in matches:
                scripts.add(f"{mod}.{func}")
        except Exception:
            pass

    setup_py_path = repo_root / "setup.py"
    if setup_py_path.exists():
        try:
            content = setup_py_path.read_text(encoding="utf-8")
            matches = re.findall(r'["\'][\w\-]+\s*=\s*([\w\.]+):([\w\.]+)["\']', content)
            for mod, func in matches:
                scripts.add(f"{mod}.{func}")
        except Exception:
            pass

    return scripts


def extract_test_discovery_entry_points(
    modules: Dict[Path, ast.Module],
    symbol_table: List[Symbol],
    repo_root: Path
) -> Set[str]:
    """Identify test methods (test_*), unittest.TestCase methods, and @pytest.fixture functions as entry point reachability roots."""
    test_entries = set()
    test_case_classes = set()

    for file_path, tree in modules.items():
        if tree is None:
            continue

        file_name = file_path.name
        rel_parts = [p.lower() for p in file_path.relative_to(repo_root.resolve()).parts] if file_path.resolve().is_relative_to(repo_root.resolve()) else [p.lower() for p in file_path.parts]
        is_test_file = fnmatch.fnmatch(file_name, "test_*.py") or fnmatch.fnmatch(file_name, "*_test.py") or any(p in ("test", "tests") for p in rel_parts)
        mod_name = get_module_dotted_name(file_path.resolve(), repo_root.resolve())

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                is_test_case = False
                for base in node.bases:
                    if isinstance(base, ast.Name) and "TestCase" in base.id:
                        is_test_case = True
                    elif isinstance(base, ast.Attribute) and "TestCase" in base.attr:
                        is_test_case = True

                if is_test_case or (is_test_file and ("test" in node.name.lower() or "base" in node.name.lower())):
                    qual_cls = f"{mod_name}.{node.name}" if mod_name else node.name
                    test_case_classes.add(qual_cls)

    for sym in symbol_table:
        parts = sym.qualified_name.split(".")
        simple_name = parts[-1]
        parent_qual = ".".join(parts[:-1])
        filename = Path(sym.file).name
        file_parts = [p.lower() for p in Path(sym.file).parts]
        is_test_file = fnmatch.fnmatch(filename, "test_*.py") or fnmatch.fnmatch(filename, "*_test.py") or any(p in ("test", "tests") for p in file_parts)

        if parent_qual in test_case_classes:
            test_entries.add(sym.qualified_name)

        if is_test_file and (simple_name.startswith("test_") or simple_name in ("setUp", "tearDown", "setUpClass", "tearDownClass", "run", "setUpModule", "tearDownModule")):
            test_entries.add(sym.qualified_name)

    # Check @pytest.fixture decorators
    for file_path, tree in modules.items():
        if tree is None:
            continue

        mod_name = get_module_dotted_name(file_path.resolve(), repo_root.resolve())

        class FixtureVisitor(ast.NodeVisitor):
            def __init__(self):
                self.scope: List[str] = [mod_name] if mod_name else []

            def visit_ClassDef(self, node: ast.ClassDef):
                self.scope.append(node.name)
                self.generic_visit(node)
                self.scope.pop()

            def visit_FunctionDef(self, node: ast.FunctionDef):
                self._check_fixture(node)

            def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
                self._check_fixture(node)

            def _check_fixture(self, node: ast.FunctionDef | ast.AsyncFunctionDef):
                qual_name = f"{'.'.join(self.scope)}.{node.name}" if self.scope else node.name
                for dec in node.decorator_list:
                    is_fixture = False
                    if isinstance(dec, ast.Attribute) and dec.attr == "fixture":
                        is_fixture = True
                    elif isinstance(dec, ast.Name) and dec.id == "fixture":
                        is_fixture = True
                    elif isinstance(dec, ast.Call):
                        if isinstance(dec.func, ast.Attribute) and dec.func.attr == "fixture":
                            is_fixture = True
                        elif isinstance(dec.func, ast.Name) and dec.func.id == "fixture":
                            is_fixture = True

                    if is_fixture:
                        test_entries.add(qual_name)
                        break

                self.scope.append(node.name)
                self.generic_visit(node)
                self.scope.pop()

        FixtureVisitor().visit(tree)

    return test_entries


def detect_entry_points(
    modules: Dict[Path, ast.Module],
    symbol_table: List[Symbol],
    user_entries: Optional[List[str]] = None,
    repo_root: Optional[Path] = None,
    frameworks_enabled: bool = False
) -> Set[str]:
    """Detect entry points in the codebase."""
    entry_points = set()
    known_symbols: Set[str] = {sym.qualified_name for sym in symbol_table}

    if repo_root is None:
        repo_root = Path.cwd().resolve()
    else:
        repo_root = repo_root.resolve()

    # (a) Any function CALLED inside an `if __name__ == "__main__":` guard
    for file_path, tree in modules.items():
        if tree is None:
            continue
        current_module = get_module_dotted_name(file_path.resolve(), repo_root)
        if_main_entries = _extract_if_main_calls(tree, current_module, known_symbols)
        entry_points.update(if_main_entries)

        if frameworks_enabled:
            fw_entries = _detect_framework_routes(tree, current_module, known_symbols)
            entry_points.update(fw_entries)

    # (b) A module-level function literally named `main`
    for sym in symbol_table:
        if sym.kind == "function" and (sym.qualified_name.endswith(".main") or sym.qualified_name == "main"):
            parts = sym.qualified_name.split(".")
            if len(parts) <= 2:
                entry_points.add(sym.qualified_name)

    # (b2) Test discovery entry points
    test_entries = extract_test_discovery_entry_points(modules, symbol_table, repo_root)
    entry_points.update(test_entries)

    # (c) Console scripts targets from pyproject.toml / setup.py
    console_scripts = _detect_console_scripts(repo_root)
    for cs in console_scripts:
        if cs in known_symbols:
            entry_points.add(cs)

    # (d) Any dotted names passed via --entry
    if user_entries:
        for entry in user_entries:
            if entry in known_symbols:
                entry_points.add(entry)
            else:
                for sym in symbol_table:
                    if sym.qualified_name.startswith(f"{entry}."):
                        entry_points.add(sym.qualified_name)

    return entry_points
