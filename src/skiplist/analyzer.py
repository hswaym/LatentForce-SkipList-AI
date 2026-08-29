import ast
import hashlib
from pathlib import Path
from typing import Dict, List, Set, Any


class StructuralNormalizer(ast.NodeTransformer):
    """Normalizes AST by replacing function/variable names and clearing line numbers."""
    def visit_Name(self, node: ast.Name):
        return ast.copy_location(ast.Name(id="_VAR_", ctx=node.ctx), node)

    def visit_arg(self, node: ast.arg):
        return ast.copy_location(ast.arg(arg="_ARG_", annotation=None), node)

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self.generic_visit(node)
        node.name = "_FUNC_"
        return node

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        self.generic_visit(node)
        node.name = "_FUNC_"
        return node


class CodeVisitor(ast.NodeVisitor):
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.defined_functions = []
        self.defined_classes = []
        self.called_names = set()
        self.imported_names = set()
        self.code_blocks = []

    def visit_FunctionDef(self, node: ast.FunctionDef):
        if not (node.name.startswith("__") and node.name.endswith("__")):
            self.defined_functions.append({
                "name": node.name,
                "line": node.lineno,
                "file": self.file_path
            })
            
            if len(node.body) >= 2:
                normalized_dump = self._normalize_node(node)
                snippet = ast.unparse(node) if hasattr(ast, "unparse") else node.name
                self.code_blocks.append({
                    "name": node.name,
                    "type": "function",
                    "file": self.file_path,
                    "line": node.lineno,
                    "lines_count": len(node.body),
                    "hash": hashlib.md5(normalized_dump.encode("utf-8")).hexdigest(),
                    "code_snippet": snippet
                })

        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        if not (node.name.startswith("__") and node.name.endswith("__")):
            self.defined_functions.append({
                "name": node.name,
                "line": node.lineno,
                "file": self.file_path
            })
            if len(node.body) >= 2:
                normalized_dump = self._normalize_node(node)
                snippet = ast.unparse(node) if hasattr(ast, "unparse") else node.name
                self.code_blocks.append({
                    "name": node.name,
                    "type": "function",
                    "file": self.file_path,
                    "line": node.lineno,
                    "lines_count": len(node.body),
                    "hash": hashlib.md5(normalized_dump.encode("utf-8")).hexdigest(),
                    "code_snippet": snippet
                })
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef):
        self.defined_classes.append({
            "name": node.name,
            "line": node.lineno,
            "file": self.file_path
        })
        self.generic_visit(node)

    def visit_Name(self, node: ast.Name):
        if isinstance(node.ctx, ast.Load):
            self.called_names.add(node.id)
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute):
        self.called_names.add(node.attr)
        self.generic_visit(node)

    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            name = alias.asname if alias.asname else alias.name
            self.imported_names.add(name)
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        for alias in node.names:
            name = alias.asname if alias.asname else alias.name
            self.imported_names.add(name)
        self.generic_visit(node)

    def _normalize_node(self, node: ast.AST) -> str:
        try:
            cloned = ast.parse(ast.unparse(node)) if hasattr(ast, "unparse") else node
            normalized_ast = StructuralNormalizer().visit(cloned)
            # dump without line numbers/attributes
            return ast.dump(normalized_ast, include_attributes=False)
        except Exception:
            return ast.dump(node, include_attributes=False)


def analyze_directory(target_dir: str) -> Dict[str, Any]:
    target_path = Path(target_dir).resolve()
    py_files = list(target_path.rglob("*.py"))

    all_functions = []
    all_classes = []
    all_calls = set()
    all_imports = set()
    all_blocks = []
    total_lines = 0

    for py_file in py_files:
        rel_path = str(py_file.relative_to(target_path))
        try:
            content = py_file.read_text(encoding="utf-8")
            total_lines += len(content.splitlines())
            tree = ast.parse(content, filename=str(py_file))
            visitor = CodeVisitor(rel_path)
            visitor.visit(tree)

            all_functions.extend(visitor.defined_functions)
            all_classes.extend(visitor.defined_classes)
            all_calls.update(visitor.called_names)
            all_imports.update(visitor.imported_names)
            all_blocks.extend(visitor.code_blocks)
        except Exception:
            pass

    entry_points = {"main", "run", "cli", "app", "handler"}
    dead_functions = [
        f for f in all_functions
        if f["name"] not in all_calls and f["name"] not in entry_points
    ]

    dead_classes = [
        c for c in all_classes
        if c["name"] not in all_calls
    ]

    hash_map: Dict[str, List[Dict[str, Any]]] = {}
    for block in all_blocks:
        hash_map.setdefault(block["hash"], []).append(block)

    duplicates = []
    for h, blocks in hash_map.items():
        if len(blocks) > 1:
            duplicates.append({
                "count": len(blocks),
                "instances": blocks
            })

    summary = {
        "target_directory": str(target_path),
        "total_files": len(py_files),
        "total_lines": total_lines,
        "total_functions": len(all_functions),
        "total_classes": len(all_classes),
        "dead_functions_count": len(dead_functions),
        "dead_classes_count": len(dead_classes),
        "duplicate_blocks_count": len(duplicates),
    }

    return {
        "summary": summary,
        "dead_code": {
            "functions": dead_functions,
            "classes": dead_classes,
        },
        "duplicates": duplicates
    }
