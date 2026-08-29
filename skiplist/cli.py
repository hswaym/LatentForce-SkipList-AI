import argparse
import ast
import sys
from pathlib import Path
from skiplist.analysis.discovery import find_python_files
from skiplist.analysis.parsing import parse_file
from skiplist.analysis.symbols import build_symbol_table
from skiplist.analysis.callgraph import build_call_graph
from skiplist.analysis.entrypoints import detect_entry_points
from skiplist.analysis.reachability import find_dead_code


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


def symbols_command(args: argparse.Namespace) -> None:
    """Execute the symbols command to list all defined symbols in the codebase."""
    repo_root = Path(args.path).resolve()
    files = find_python_files(repo_root, exclude=args.exclude)

    modules = {}
    for file_path in files:
        tree = parse_file(file_path)
        if tree is not None:
            modules[file_path] = tree

    symbols = build_symbol_table(modules, repo_root)

    sorted_symbols = sorted(symbols, key=lambda s: (s.file, s.line_start))

    for sym in sorted_symbols:
        location = f"{sym.file}:{sym.line_start}-{sym.line_end}"
        print(f"{sym.qualified_name:<35} {location:<30} {sym.lines:<6} {sym.kind}")


def deadcode_command(args: argparse.Namespace) -> None:
    """Execute the deadcode command to find and print unreachable symbols."""
    repo_root = Path(args.path).resolve()
    files = find_python_files(repo_root, exclude=args.exclude)

    modules = {}
    for file_path in files:
        tree = parse_file(file_path)
        if tree is not None:
            modules[file_path] = tree

    symbol_table = build_symbol_table(modules, repo_root)
    call_graph = build_call_graph(modules, symbol_table, repo_root)
    entry_points = detect_entry_points(modules, symbol_table, user_entries=args.entry, repo_root=repo_root)

    dead_symbols = find_dead_code(call_graph, entry_points, symbol_table)

    sorted_entries = sorted(list(entry_points))
    print(f"Entry points: {sorted_entries}")

    sorted_dead = sorted(dead_symbols, key=lambda s: (s.file, s.line_start))
    print("Dead candidates:")
    for sym in sorted_dead:
        location = f"{sym.file}:{sym.line_start}-{sym.line_end}"
        print(f"  {sym.qualified_name:<35} {location:<30} {sym.lines}")


def main() -> None:
    parser = argparse.ArgumentParser(prog="skiplist", description="SkipList: Pre-migration code-triage tool.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Analyze command
    analyze_parser = subparsers.add_parser("analyze", help="Analyze a Python codebase for dead and duplicate code.")
    analyze_parser.add_argument("path", help="Path to Python codebase root directory")
    analyze_parser.add_argument("--entry", action="append", default=[], help="Specify entry point file/module (repeatable)")
    analyze_parser.add_argument("--exclude", action="append", default=[], help="Exclude file/directory path pattern (repeatable)")
    analyze_parser.add_argument("--out", default="report.html", help="Output file path (default: report.html)")
    analyze_parser.add_argument("--format", choices=["html", "json"], default="html", help="Report format (default: html)")

    # Symbols command
    symbols_parser = subparsers.add_parser("symbols", help="Build and print symbol table for a Python codebase.")
    symbols_parser.add_argument("path", help="Path to Python codebase root directory")
    symbols_parser.add_argument("--exclude", action="append", default=[], help="Exclude file/directory path pattern (repeatable)")

    # Deadcode command
    deadcode_parser = subparsers.add_parser("deadcode", help="Find dead code symbols using call graph reachability.")
    deadcode_parser.add_argument("path", help="Path to Python codebase root directory")
    deadcode_parser.add_argument("--entry", action="append", default=[], help="Specify entry point file/module (repeatable)")
    deadcode_parser.add_argument("--exclude", action="append", default=[], help="Exclude file/directory path pattern (repeatable)")

    args = parser.parse_args()

    if args.command == "analyze":
        analyze_command(args)
    elif args.command == "symbols":
        symbols_command(args)
    elif args.command == "deadcode":
        deadcode_command(args)


if __name__ == "__main__":
    main()
