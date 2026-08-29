import ast
from pathlib import Path
from typing import List, Dict, Optional
from skiplist.models import Symbol


def get_module_dotted_name(file_path: Path, repo_root: Path) -> str:
    """Compute dotted Python module path for a file relative to repo root."""
    try:
        rel_path = file_path.relative_to(repo_root)
    except ValueError:
        rel_path = file_path

    parts = list(rel_path.parts)
    if not parts:
        return ""

    # Strip .py extension
    if parts[-1].endswith(".py"):
        parts[-1] = parts[-1][:-3]

    # Handle __init__.py
    if parts[-1] == "__init__":
        parts.pop()

    return ".".join(parts)


class SymbolVisitor(ast.NodeVisitor):
    def __init__(self, module_dotted_name: str, rel_file_path: str):
        self.module_dotted_name = module_dotted_name
        self.rel_file_path = rel_file_path
        self.symbols: List[Symbol] = []
        self.scope_stack: List[str] = [module_dotted_name] if module_dotted_name else []

    def _get_current_qualified_name(self, name: str) -> str:
        if self.scope_stack:
            return f"{'.'.join(self.scope_stack)}.{name}"
        return name

    def _get_line_end(self, node: ast.AST) -> int:
        end = getattr(node, "end_lineno", None)
        if end is not None:
            return end
        return getattr(node, "lineno", 1)

    def visit_ClassDef(self, node: ast.ClassDef):
        qual_name = self._get_current_qualified_name(node.name)
        line_start = node.lineno
        line_end = self._get_line_end(node)
        lines = line_end - line_start + 1

        self.symbols.append(
            Symbol(
                qualified_name=qual_name,
                kind="class",
                file=self.rel_file_path,
                line_start=line_start,
                line_end=line_end,
                lines=lines
            )
        )

        self.scope_stack.append(node.name)
        self.generic_visit(node)
        self.scope_stack.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self._visit_func(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        self._visit_func(node)

    def _visit_func(self, node: ast.FunctionDef | ast.AsyncFunctionDef):
        qual_name = self._get_current_qualified_name(node.name)
        line_start = node.lineno
        line_end = self._get_line_end(node)
        lines = line_end - line_start + 1

        # Check if enclosing parent in scope stack is a class or function
        is_in_class = False
        if len(self.scope_stack) > 1:
            # Check if immediately preceding element is a class name (best-effort check during traversal)
            is_in_class = True  # method if enclosed inside class or nested function

        # Distinguish method vs function: if immediately enclosed by a class
        kind = "method" if is_in_class and self._is_parent_class() else "function"

        self.symbols.append(
            Symbol(
                qualified_name=qual_name,
                kind=kind,
                file=self.rel_file_path,
                line_start=line_start,
                line_end=line_end,
                lines=lines
            )
        )

        self.scope_stack.append(node.name)
        self.generic_visit(node)
        self.scope_stack.pop()

    def _is_parent_class(self) -> bool:
        # We track whether parent scope was a ClassDef node or FunctionDef node in AST stack
        return getattr(self, "_current_is_class", False)


class ScopedSymbolVisitor(ast.NodeVisitor):
    def __init__(self, module_dotted_name: str, rel_file_path: str):
        self.module_dotted_name = module_dotted_name
        self.rel_file_path = rel_file_path
        self.symbols: List[Symbol] = []
        # Store tuples of (name, is_class)
        self.scope: List[tuple[str, bool]] = []
        if module_dotted_name:
            self.scope.append((module_dotted_name, False))

    def _current_qual_name(self, name: str) -> str:
        prefix = ".".join(s[0] for s in self.scope)
        if prefix:
            return f"{prefix}.{name}"
        return name

    def _get_line_end(self, node: ast.AST) -> int:
        end = getattr(node, "end_lineno", None)
        return end if end is not None else getattr(node, "lineno", 1)

    def visit_ClassDef(self, node: ast.ClassDef):
        qual_name = self._current_qual_name(node.name)
        line_start = node.lineno
        line_end = self._get_line_end(node)
        lines = line_end - line_start + 1

        self.symbols.append(
            Symbol(
                qualified_name=qual_name,
                kind="class",
                file=self.rel_file_path,
                line_start=line_start,
                line_end=line_end,
                lines=lines
            )
        )

        self.scope.append((node.name, True))
        self.generic_visit(node)
        self.scope.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self._handle_func(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        self._handle_func(node)

    def _handle_func(self, node: ast.FunctionDef | ast.AsyncFunctionDef):
        qual_name = self._current_qual_name(node.name)
        line_start = node.lineno
        line_end = self._get_line_end(node)
        lines = line_end - line_start + 1

        kind = "function"
        if self.scope and self.scope[-1][1]:
            kind = "method"

        self.symbols.append(
            Symbol(
                qualified_name=qual_name,
                kind=kind,
                file=self.rel_file_path,
                line_start=line_start,
                line_end=line_end,
                lines=lines
            )
        )

        self.scope.append((node.name, False))
        self.generic_visit(node)
        self.scope.pop()


def build_symbol_table(modules: Dict[Path, ast.Module], repo_root: Path) -> List[Symbol]:
    """Walk each module AST and record every FunctionDef, AsyncFunctionDef, and ClassDef."""
    symbols: List[Symbol] = []
    root_path = repo_root.resolve()

    for file_path, tree in modules.items():
        if tree is None:
            continue
        
        abs_path = file_path.resolve()
        try:
            rel_file_path = str(abs_path.relative_to(root_path)).replace("\\", "/")
        except ValueError:
            rel_file_path = str(abs_path).replace("\\", "/")

        mod_dotted = get_module_dotted_name(abs_path, root_path)
        visitor = ScopedSymbolVisitor(mod_dotted, rel_file_path)
        visitor.visit(tree)
        symbols.extend(visitor.symbols)

    return symbols
