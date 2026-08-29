import ast
from pathlib import Path
from typing import Dict, List, Set, Any, Optional
import networkx as nx
from skiplist.models import Symbol
from skiplist.analysis.symbols import get_module_dotted_name


class ModuleImportMap:
    def __init__(self, current_module: str):
        self.current_module = current_module
        # Local alias name -> qualified symbol prefix or target qualified name
        self.aliases: Dict[str, str] = {}

    def add_import(self, node: ast.Import):
        for alias in node.names:
            local_name = alias.asname if alias.asname else alias.name
            self.aliases[local_name] = alias.name

    def add_import_from(self, node: ast.ImportFrom):
        module_name = node.module or ""
        level = node.level

        # Resolve relative imports
        if level > 0:
            parts = self.current_module.split(".") if self.current_module else []
            if level <= len(parts):
                base_parts = parts[:-level] if level > 0 else parts
                if module_name:
                    base_parts.append(module_name)
                module_name = ".".join(base_parts)
            else:
                module_name = module_name

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
    """Build a directed call graph where nodes are symbol qualified_names and edges represent static calls."""
    graph = nx.DiGraph()
    unresolved_calls: List[Dict[str, Any]] = []
    graph.graph["unresolved_calls"] = unresolved_calls

    known_symbols: Set[str] = {sym.qualified_name for sym in symbol_table}

    # Add all symbols as graph nodes
    for sym in symbol_table:
        graph.add_node(sym.qualified_name, symbol=sym)

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

        # Walk AST tracking current enclosing function/method symbol
        _extract_calls_from_module(
            tree=tree,
            current_module=current_module,
            import_map=import_map,
            known_symbols=known_symbols,
            graph=graph,
            unresolved_calls=unresolved_calls
        )

    return graph


def _extract_calls_from_module(
    tree: ast.AST,
    current_module: str,
    import_map: ModuleImportMap,
    known_symbols: Set[str],
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

            # Visit children functions/classes, but inspect calls inside function body
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

            # Case 1: Direct function call `func()`
            if isinstance(func_expr, ast.Name):
                name = func_expr.id
                # Check import alias first
                if name in import_map.aliases:
                    target_candidate = import_map.aliases[name]
                    if target_candidate in known_symbols:
                        resolved_target = target_candidate
                
                # Check same module bare call `thismodule.func`
                if not resolved_target:
                    same_mod_candidate = f"{current_module}.{name}" if current_module else name
                    if same_mod_candidate in known_symbols:
                        resolved_target = same_mod_candidate

            # Case 2: Attribute call `mod.func()` or `m.func()`
            elif isinstance(func_expr, ast.Attribute) and isinstance(func_expr.value, ast.Name):
                mod_alias = func_expr.value.id
                attr_name = func_expr.attr

                if mod_alias in import_map.aliases:
                    base_mod = import_map.aliases[mod_alias]
                    target_candidate = f"{base_mod}.{attr_name}"
                    if target_candidate in known_symbols:
                        resolved_target = target_candidate

                if not resolved_target:
                    same_mod_sub = f"{current_module}.{mod_alias}.{attr_name}" if current_module else f"{mod_alias}.{attr_name}"
                    if same_mod_sub in known_symbols:
                        resolved_target = same_mod_sub

            # Add edge if resolved and caller in graph
            if resolved_target and graph.has_node(caller_qual) and graph.has_node(resolved_target):
                graph.add_edge(caller_qual, resolved_target)
            else:
                unresolved_calls.append({
                    "caller": caller_qual,
                    "line": call_node.lineno,
                    "expression": ast.unparse(call_node) if hasattr(ast, "unparse") else str(call_node)
                })

    visitor = CallVisitor()
    visitor.visit(tree)
