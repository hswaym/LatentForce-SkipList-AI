import ast
import fnmatch
import re
from pathlib import Path
from typing import List, Set, Dict, Any, Optional
import networkx as nx
from skiplist.models import Symbol
from skiplist.analysis.symbols import get_module_dotted_name


DYNAMIC_PATTERNS = {"getattr", "setattr", "globals", "locals", "eval", "exec", "__import__"}


def is_dunder_symbol(symbol: Symbol) -> bool:
    """Check if a symbol is a dunder method/function (e.g., __init__, __enter__, __repr__)."""
    name_part = symbol.qualified_name.split(".")[-1]
    return bool(re.match(r"^__\w+__$", name_part))


def extract_module_alls(modules: Dict[Path, ast.Module], repo_root: Path) -> Dict[str, Set[str]]:
    """Extract names exported in __all__ per module."""
    module_alls: Dict[str, Set[str]] = {}

    for file_path, tree in modules.items():
        if tree is None:
            continue
        mod_name = get_module_dotted_name(file_path.resolve(), repo_root.resolve())
        exported = set()

        for node in tree.body:
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == "__all__":
                        if isinstance(node.value, (ast.List, ast.Tuple, ast.Set)):
                            for elt in node.value.elts:
                                if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                                    exported.add(elt.value)

        if exported:
            module_alls[mod_name] = exported

    return module_alls


def extract_test_discovery_seeds(
    modules: Dict[Path, ast.Module],
    symbol_table: List[Symbol],
    repo_root: Path
) -> Set[str]:
    """Extract test functions, unittest.TestCase methods, and pytest fixtures as implicitly reachable seeds."""
    test_seeds = set()
    test_case_classes = set()

    for file_path, tree in modules.items():
        if tree is None:
            continue

        file_name = file_path.name
        is_test_file = fnmatch.fnmatch(file_name, "test_*.py") or fnmatch.fnmatch(file_name, "*_test.py")
        mod_name = get_module_dotted_name(file_path.resolve(), repo_root.resolve())

        # First pass: identify classes that subclass TestCase
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                is_test_case = False
                for base in node.bases:
                    if isinstance(base, ast.Name) and "TestCase" in base.id:
                        is_test_case = True
                    elif isinstance(base, ast.Attribute) and "TestCase" in base.attr:
                        is_test_case = True

                if is_test_case or (is_test_file and (node.name.startswith("Test") or node.name.endswith("Test"))):
                    qual_cls = f"{mod_name}.{node.name}" if mod_name else node.name
                    test_case_classes.add(qual_cls)

    # Second pass: mark methods of TestCase classes, test_ functions in test files, and pytest.fixture
    for sym in symbol_table:
        parts = sym.qualified_name.split(".")
        simple_name = parts[-1]
        parent_qual = ".".join(parts[:-1])
        filename = Path(sym.file).name
        is_test_file = fnmatch.fnmatch(filename, "test_*.py") or fnmatch.fnmatch(filename, "*_test.py")

        # 1. Any method in a class that subclasses TestCase or is a Test class in test file
        if parent_qual in test_case_classes:
            test_seeds.add(sym.qualified_name)

        # 2. Any function/method named test_* in test_*.py or *_test.py
        if is_test_file and simple_name.startswith("test_"):
            test_seeds.add(sym.qualified_name)

    # Third pass: check pytest.fixture decorator
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
                        test_seeds.add(qual_name)
                        break

                self.scope.append(node.name)
                self.generic_visit(node)
                self.scope.pop()

        FixtureVisitor().visit(tree)

    return test_seeds


def detect_dynamic_modules(modules: Dict[Path, ast.Module], repo_root: Path) -> Set[str]:
    """Detect modules that use dynamic dispatch patterns (getattr, globals, eval, importlib, etc.)."""
    dynamic_mods: Set[str] = set()

    for file_path, tree in modules.items():
        if tree is None:
            continue
        mod_name = get_module_dotted_name(file_path.resolve(), repo_root.resolve())

        is_dynamic = False
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id in DYNAMIC_PATTERNS:
                    is_dynamic = True
                    break
                elif isinstance(node.func, ast.Attribute):
                    if isinstance(node.func.value, ast.Name) and node.func.value.id == "importlib":
                        is_dynamic = True
                        break
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == "importlib" or alias.name.startswith("importlib."):
                        is_dynamic = True
                        break
            elif isinstance(node, ast.ImportFrom):
                if node.module == "importlib" or (node.module and node.module.startswith("importlib")):
                    is_dynamic = True
                    break

            if is_dynamic:
                break

        if is_dynamic:
            dynamic_mods.add(mod_name)

    return dynamic_mods


def find_dead_code(
    call_graph: nx.DiGraph,
    entry_points: Set[str],
    symbol_table: List[Symbol],
    modules: Optional[Dict[Path, ast.Module]] = None,
    repo_root: Optional[Path] = None
) -> List[Symbol]:
    """Find dead code candidates by computing reachability from entry points over the call graph."""
    reached: Set[str] = set()
    seeds = set(entry_points)

    module_alls = extract_module_alls(modules, repo_root) if modules and repo_root else {}
    test_seeds = extract_test_discovery_seeds(modules, symbol_table, repo_root) if modules and repo_root else set()

    # Add implicit entry points / false positive guards:
    seeds.update(test_seeds)

    for sym in symbol_table:
        # Dunder methods/functions are implicitly reachable
        if is_dunder_symbol(sym):
            seeds.add(sym.qualified_name)

        # Symbols exported in module __all__
        mod_name = ".".join(sym.qualified_name.split(".")[:-1])
        simple_name = sym.qualified_name.split(".")[-1]
        if mod_name in module_alls and simple_name in module_alls[mod_name]:
            seeds.add(sym.qualified_name)

    # Perform BFS / reachability traversal over call_graph
    for seed in seeds:
        if seed in call_graph:
            reached.add(seed)
            descendants = nx.descendants(call_graph, seed)
            reached.update(descendants)

    # Dead candidates = Symbol objects whose qualified_name was never reached
    dead_symbols = [
        sym for sym in symbol_table
        if sym.qualified_name not in reached
    ]

    return dead_symbols
