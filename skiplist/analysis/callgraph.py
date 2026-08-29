import ast
from pathlib import Path
from typing import Dict, List, Set, Any, Optional
import networkx as nx
from skiplist.models import Symbol
from skiplist.analysis.symbols import get_module_dotted_name


class ModuleImportMap:
    def __init__(self, current_module: str):
        self.current_module = current_module
        self.aliases: Dict[str, str] = {}

    def add_import(self, node: ast.Import):
        for alias in node.names:
            local_name = alias.asname if alias.asname else alias.name
            self.aliases[local_name] = alias.name

    def add_import_from(self, node: ast.ImportFrom):
        module_name = node.module or ""
        level = node.level

        if level > 0:
            parts = self.current_module.split(".") if self.current_module else []
            if level <= len(parts):
                base_parts = parts[:-level] if level > 0 else parts
                if module_name:
                    base_parts.append(module_name)
                module_name = ".".join(base_parts)

        for alias in node.names:
            local_name = alias.asname if alias.asname else alias.name
            target = f"{module_name}.{alias.name}" if module_name else alias.name
            self.aliases[local_name] = target


def build_module_import_map(tree: ast.AST, current_module: str) -> ModuleImportMap:
    import_map = ModuleImportMap(current_module)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            import_map.add_import(node)
        elif isinstance(node, ast.ImportFrom):
            import_map.add_import_from(node)
    return import_map


def build_call_graph(modules: Dict[Path, ast.Module], symbol_table: List[Symbol], repo_root: Optional[Path] = None) -> nx.DiGraph:
    """Build a directed call graph keyed strictly by symbol qualified_name."""
    graph = nx.DiGraph()
    unresolved_calls: List[Dict[str, Any]] = []
    graph.graph["unresolved_calls"] = unresolved_calls

    symbol_map: Dict[str, Symbol] = {sym.qualified_name: sym for sym in symbol_table}

    # Add each symbol to graph keyed strictly by qualified_name
    for qual_name, sym in symbol_map.items():
        graph.add_node(qual_name, symbol=sym)

    if repo_root is None:
        repo_root = Path.cwd().resolve()
    else:
        repo_root = repo_root.resolve()

    for file_path, tree in modules.items():
        if tree is None:
            continue

        abs_path = file_path.resolve()
        current_module = get_module_dotted_name(abs_path, repo_root)
        import_map = build_module_import_map(tree, current_module)

        _extract_calls_from_module(
            tree=tree,
            current_module=current_module,
            import_map=import_map,
            symbol_map=symbol_map,
            graph=graph,
            unresolved_calls=unresolved_calls
        )

    return graph


def _extract_calls_from_module(
    tree: ast.AST,
    current_module: str,
    import_map: ModuleImportMap,
    symbol_map: Dict[str, Symbol],
    graph: nx.DiGraph,
    unresolved_calls: List[Dict[str, Any]]
):
    class CallVisitor(ast.NodeVisitor):
        def __init__(self):
            self.scope_stack: List[str] = [current_module] if current_module else []

        def visit_ClassDef(self, node: ast.ClassDef):
            self.scope_stack.append(node.name)
            self.generic_visit(node)
            self.scope_stack.pop()

        def visit_FunctionDef(self, node: ast.FunctionDef):
            self._visit_func(node)

        def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
            self._visit_func(node)

        def _visit_func(self, node: ast.FunctionDef | ast.AsyncFunctionDef):
            caller_qual = f"{'.'.join(self.scope_stack)}.{node.name}" if self.scope_stack else node.name
            self.scope_stack.append(node.name)

            for body_node in node.body:
                self._inspect_calls(body_node, caller_qual)

            self.scope_stack.pop()

        def _inspect_calls(self, body_node: ast.AST, caller_qual: str):
            for n in ast.walk(body_node):
                if isinstance(n, ast.Call):
                    self._resolve_call(n, caller_qual)

        def _resolve_call(self, call_node: ast.Call, caller_qual: str):
            func_expr = call_node.func
            resolved_target = None

            if isinstance(func_expr, ast.Name):
                name = func_expr.id
                if name in import_map.aliases:
                    target_candidate = import_map.aliases[name]
                    if target_candidate in symbol_map:
                        resolved_target = target_candidate

                if not resolved_target:
                    same_mod_candidate = f"{current_module}.{name}" if current_module else name
                    if same_mod_candidate in symbol_map:
                        resolved_target = same_mod_candidate

            elif isinstance(func_expr, ast.Attribute) and isinstance(func_expr.value, ast.Name):
                mod_alias = func_expr.value.id
                attr_name = func_expr.attr

                if mod_alias in import_map.aliases:
                    base_mod = import_map.aliases[mod_alias]
                    target_candidate = f"{base_mod}.{attr_name}"
                    if target_candidate in symbol_map:
                        resolved_target = target_candidate

                if not resolved_target:
                    same_mod_sub = f"{current_module}.{mod_alias}.{attr_name}" if current_module else f"{mod_alias}.{attr_name}"
                    if same_mod_sub in symbol_map:
                        resolved_target = same_mod_sub

            if resolved_target and graph.has_node(caller_qual) and graph.has_node(resolved_target):
                graph.add_edge(caller_qual, resolved_target)
            else:
                unresolved_calls.append({
                    "caller": caller_qual,
                    "line": getattr(call_node, "lineno", 1),
                    "expression": ast.unparse(call_node) if hasattr(ast, "unparse") else str(call_node)
                })

    visitor = CallVisitor()
    visitor.visit(tree)
