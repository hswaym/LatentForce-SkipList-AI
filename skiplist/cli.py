import argparse
import ast
import sys
from pathlib import Path
from skiplist.analysis.discovery import find_python_files
from skiplist.analysis.parsing import parse_file


def count_ast_nodes(tree: ast.AST) -> tuple[int, int]:
    """Walk an AST tree and count total function/method defs and class defs."""
    functions = 0
    classes = 0

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            functions += 1
        elif isinstance(node, ast.ClassDef):
            classes += 1

    return functions, classes


def analyze_command(args: argparse.Namespace) -> None:
    """Execute the walking skeleton analyze command."""
    target_path = Path(args.path)
    files = find_python_files(target_path, exclude=args.exclude)

    files_parsed = 0
    total_functions = 0
    total_classes = 0

    for file_path in files:
        tree = parse_file(file_path)
        if tree is not None:
            files_parsed += 1
            funcs, cls = count_ast_nodes(tree)
            total_functions += funcs
            total_classes += cls

    print(f"Parsed {files_parsed} files, found {total_functions} functions, {total_classes} classes.")


def main() -> None:
    parser = argparse.ArgumentParser(prog="skiplist", description="SkipList: Pre-migration code-triage tool.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    analyze_parser = subparsers.add_parser("analyze", help="Analyze a Python codebase for dead and duplicate code.")
    analyze_parser.add_argument("path", help="Path to Python codebase root directory")
    analyze_parser.add_argument("--entry", action="append", default=[], help="Specify entry point file/module (repeatable)")
    analyze_parser.add_argument("--exclude", action="append", default=[], help="Exclude file/directory path pattern (repeatable)")
    analyze_parser.add_argument("--out", default="report.html", help="Output file path (default: report.html)")
    analyze_parser.add_argument("--format", choices=["html", "json"], default="html", help="Report format (default: html)")

    args = parser.parse_args()

    if args.command == "analyze":
        analyze_command(args)


if __name__ == "__main__":
    main()
