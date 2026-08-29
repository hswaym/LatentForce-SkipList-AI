import ast
import copy
import hashlib
from pathlib import Path
from typing import Dict, List, Set, Any, Optional
from skiplist.models import Symbol


def is_docstring_expr(node: ast.AST) -> bool:
    if isinstance(node, ast.Expr):
        val = node.value
        if isinstance(val, ast.Constant) and isinstance(val.value, str):
            return True
    return False


def is_trivial_function(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    """Check if a function body is trivial (empty, docstring-only, pass, bare return/return None, single raise)."""
    body = [stmt for stmt in node.body if not is_docstring_expr(stmt)]

    if not body:
        return True

    if len(body) == 1:
        stmt = body[0]
        if isinstance(stmt, ast.Pass):
            return True
        if isinstance(stmt, ast.Return):
            if stmt.value is None:
                return True
            if isinstance(stmt.value, ast.Constant) and stmt.value.value is None:
                return True
        if isinstance(stmt, ast.Raise):
            return True

    return False


class Canonicalizer(ast.NodeTransformer):
    def __init__(self):
        self.var_map: Dict[str, str] = {}

    def _get_var_alias(self, name: str) -> str:
        if name not in self.var_map:
            self.var_map[name] = f"VAR{len(self.var_map)}"
        return self.var_map[name]

    def visit_arg(self, node: ast.arg):
        node.arg = self._get_var_alias(node.arg)
        node.annotation = None
        self.generic_visit(node)
        return node

    def visit_Name(self, node: ast.Name):
        if not getattr(node, "_is_call_func", False):
            node.id = self._get_var_alias(node.id)
        self.generic_visit(node)
        return node

    def visit_Call(self, node: ast.Call):
        if isinstance(node.func, ast.Name):
            setattr(node.func, "_is_call_func", True)
        self.generic_visit(node)
        return node

    def visit_Attribute(self, node: ast.Attribute):
        node.value = self.visit(node.value)
        return node


def canonicalize_function(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    """Build a canonical string representation of a function AST for structural duplicate hashing."""
    cloned = copy.deepcopy(node)

    cloned.body = [stmt for stmt in cloned.body if not is_docstring_expr(stmt)]
    cloned.name = "FUNC"
    cloned.decorator_list = []

    transformer = Canonicalizer()
    transformed = transformer.visit(cloned)

    return ast.dump(transformed, include_attributes=False)


def hash_canonical_ast(canonical_dump: str) -> str:
    return hashlib.sha256(canonical_dump.encode("utf-8")).hexdigest()


class DuplicateCluster:
    def __init__(self, canonical_hash: str, members: List[Symbol]):
        self.canonical_hash = canonical_hash
        self.members = members
        self.keeper: Optional[Symbol] = None
        self.non_keepers: List[Symbol] = []


def cluster_duplicates(
    modules: Dict[Path, ast.Module],
    symbol_table: List[Symbol],
    reachable_symbols: Set[str],
    repo_root: Optional[Path] = None
) -> List[DuplicateCluster]:
    """Cluster functions with identical normalized AST hashes (excluding trivial functions)."""
    if repo_root is None:
        repo_root = Path.cwd().resolve()
    else:
        repo_root = repo_root.resolve()

    location_map: Dict[tuple[str, int], Symbol] = {
        (sym.file, sym.line_start): sym
        for sym in symbol_table
        if sym.kind in ("function", "method")
    }

    func_hashes: Dict[str, List[Symbol]] = {}

    for file_path, tree in modules.items():
        if tree is None:
            continue

        abs_path = file_path.resolve()
        try:
            rel_file = str(abs_path.relative_to(repo_root)).replace("\\", "/")
        except ValueError:
            rel_file = str(abs_path).replace("\\", "/")

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if is_trivial_function(node):
                    continue

                line_start = getattr(node, "lineno", 1)
                matching_sym = location_map.get((rel_file, line_start))

                if matching_sym:
                    canon_str = canonicalize_function(node)
                    h = hash_canonical_ast(canon_str)
                    func_hashes.setdefault(h, []).append(matching_sym)

    clusters: List[DuplicateCluster] = []
    for h, members in func_hashes.items():
        if len(members) >= 2:
            cluster = DuplicateCluster(canonical_hash=h, members=members)

            sorted_members = sorted(
                members,
                key=lambda s: (0 if s.qualified_name in reachable_symbols else 1, s.qualified_name)
            )
            cluster.keeper = sorted_members[0]
            cluster.non_keepers = sorted_members[1:]
            clusters.append(cluster)

    return clusters
