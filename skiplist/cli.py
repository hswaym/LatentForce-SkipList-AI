import argparse
import ast
import sys
import time
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from skiplist.analysis.discovery import find_python_files
from skiplist.analysis.parsing import parse_file
from skiplist.analysis.symbols import build_symbol_table
from skiplist.analysis.callgraph import build_call_graph, build_graph_export
from skiplist.analysis.entrypoints import detect_entry_points
from skiplist.analysis.reachability import find_dead_code, detect_dynamic_modules
from skiplist.analysis.duplicates import cluster_duplicates
from skiplist.analysis.scoring import compute_priority_score
from skiplist.models import Report, Meta, Summary, Finding, Evidence
from skiplist.report.json_writer import write_json
from skiplist.report.html_writer import write_html

VERSION = "0.1.0"
TAGLINE = "Know what to skip before you migrate."

ASCII_LOGO = r"""
   _____ k  _         _       _   
  / ____| |(_)       | |     | |  
 | (___ | | _ _ __   | |     | |  
  \___ \| || | '_ \  | |     | |  
  ____) | || | |_) | | |____ |_|  
 |_____/|_||_| .__/  |______|(_)  
             | |                  
             |_|                  
"""

console = Console()
err_console = Console(stderr=True)


def print_banner():
    console.print(f"[bold cyan]{ASCII_LOGO}[/bold cyan]")
    console.print(f"[bold indigo]SkipList[/bold indigo] [dim]v{VERSION}[/dim] - [italic]{TAGLINE}[/italic]\n")


def analyze_command(args: argparse.Namespace) -> None:
    """Execute the full analysis pipeline and emit report."""
    start_time = time.time()
    repo_root = Path(args.path).resolve()

    if not repo_root.exists():
        err_console.print(f"[bold red]Error:[/bold red] Target path '[bold]{args.path}[/bold]' does not exist.")
        err_console.print("[dim]Actionable suggestion: Verify the directory path and try again.[/dim]")
        sys.exit(1)

    if not repo_root.is_dir():
        err_console.print(f"[bold red]Error:[/bold red] Target path '[bold]{args.path}[/bold]' is a file, not a directory.")
        err_console.print("[dim]Actionable suggestion: Provide a project directory path to analyze.[/dim]")
        sys.exit(1)

    print_banner()

    # Stage 1: File Discovery
    console.print("[cyan][1/5][/cyan] Discovering Python source files...")
    files = find_python_files(repo_root, exclude=args.exclude)

    modules = {}
    total_lines = 0
    for file_path in files:
        tree = parse_file(file_path)
        if tree is not None:
            modules[file_path] = tree
            try:
                content = file_path.read_text(encoding="utf-8")
                total_lines += len(content.splitlines())
            except Exception:
                pass

    # Stage 2: Symbol Extraction
    console.print("[cyan][2/5][/cyan] Extracting symbol table...")
    symbol_table = build_symbol_table(modules, repo_root)

    # Stage 3: Call Graph & Reachability
    console.print("[cyan][3/5][/cyan] Building call graph & tracing reachability...")
    call_graph = build_call_graph(modules, symbol_table, repo_root)
    entry_points = detect_entry_points(
        modules,
        symbol_table,
        user_entries=args.entry,
        repo_root=repo_root,
        frameworks_enabled=getattr(args, "frameworks", False)
    )

    dead_symbols = find_dead_code(call_graph, entry_points, symbol_table, modules, repo_root)
    dead_symbol_names = {s.qualified_name for s in dead_symbols}
    reachable_symbols = {s.qualified_name for s in symbol_table if s.qualified_name not in dead_symbol_names}

    # Stage 4: Duplicate Clustering
    console.print("[cyan][4/5][/cyan] Clustering structural duplicate functions...")
    dup_clusters = cluster_duplicates(modules, symbol_table, reachable_symbols, repo_root)
    dynamic_modules = detect_dynamic_modules(modules, repo_root)

    # Stage 5: Findings & Reports
    console.print("[cyan][5/5][/cyan] Scoring findings & generating reports...")

    findings: list[Finding] = []
    non_keeper_names = set()
    duplicate_findings_count = 0
    duplicate_lines_sum = 0

    for cluster in dup_clusters:
        keeper_name = cluster.keeper.qualified_name if cluster.keeper else "unknown"
        for non_keeper in cluster.non_keepers:
            non_keeper_names.add(non_keeper.qualified_name)
            duplicate_findings_count += 1
            duplicate_lines_sum += non_keeper.lines

            findings.append(
                Finding(
                    id="",
                    type="duplicate",
                    symbol=non_keeper.qualified_name,
                    file=non_keeper.file,
                    line_start=non_keeper.line_start,
                    line_end=non_keeper.line_end,
                    lines=non_keeper.lines,
                    reason=f"Structurally identical duplicate of {keeper_name}.",
                    evidence=Evidence(callers=[], duplicate_of=[keeper_name]),
                    confidence="high",
                    caveats=[],
                    priority_score=compute_priority_score(non_keeper.lines, "high", "duplicate")
                )
            )

    filtered_dead = [s for s in dead_symbols if s.qualified_name not in non_keeper_names]

    for sym in filtered_dead:
        mod_name = ".".join(sym.qualified_name.split(".")[:-1])
        if mod_name in dynamic_modules:
            conf = "low"
            reason = "Statically unreachable, but its module uses dynamic dispatch — may be invoked at runtime."
            caveats = [f"Module '{mod_name}' uses dynamic dispatch (getattr/globals/eval/import); this function may be reached dynamically."]
        else:
            conf = "high"
            reason = "Unreachable symbol never called from entry points."
            caveats = []

        findings.append(
            Finding(
                id="",
                type="dead_code",
                symbol=sym.qualified_name,
                file=sym.file,
                line_start=sym.line_start,
                line_end=sym.line_end,
                lines=sym.lines,
                reason=reason,
                evidence=Evidence(callers=[], duplicate_of=[]),
                confidence=conf,
                caveats=caveats,
                priority_score=compute_priority_score(sym.lines, conf, "dead_code")
            )
        )

    sorted_findings = sorted(findings, key=lambda f: (-f.priority_score, f.symbol))

    for idx, f in enumerate(sorted_findings, start=1):
        f.id = f"F{idx:03d}"

    high_dead_findings = [f for f in sorted_findings if f.type == "dead_code" and f.confidence != "low"]
    low_conf_findings = [f for f in sorted_findings if f.confidence == "low"]

    dead_functions_count = len(high_dead_findings)
    dead_lines_sum = sum(f.lines for f in high_dead_findings)

    needs_review_count = len(low_conf_findings)
    needs_review_lines_sum = sum(f.lines for f in low_conf_findings)

    safe_to_skip_lines = dead_lines_sum + duplicate_lines_sum
    safe_to_skip_pct = round(safe_to_skip_lines / total_lines * 100, 1) if total_lines > 0 else 0.0

    meta = Meta(
        repo_path=str(repo_root),
        analyzed_at=datetime.now(timezone.utc).isoformat(),
        tool_version=VERSION,
        files_analyzed=len(files),
        total_functions=len([s for s in symbol_table if s.kind in ("function", "method")]),
        total_lines=total_lines,
        entry_points=sorted(list(entry_points))
    )

    summary = Summary(
        dead_functions=dead_functions_count,
        dead_lines=dead_lines_sum,
        needs_review_functions=needs_review_count,
        needs_review_lines=needs_review_lines_sum,
        duplicate_clusters=len(dup_clusters),
        duplicate_lines=duplicate_lines_sum,
        safe_to_skip_lines=safe_to_skip_lines,
        safe_to_skip_pct=safe_to_skip_pct
    )

    graph_export = build_graph_export(call_graph, symbol_table, sorted_findings)

    report = Report(
        meta=meta,
        summary=summary,
        findings=sorted_findings,
        graph=graph_export
    )

    report_dict = asdict(report)

    out_html_path = None
    out_json_path = None

    if args.format == "json":
        write_json(report, args.out)
        out_json_path = args.out
    elif args.format == "html":
        write_html(report_dict, args.out)
        out_html_path = args.out
    elif args.format == "both":
        out_html_path = args.out if args.out.endswith(".html") else "report.html"
        json_out = "findings.json" if args.out == "report.html" else (args.out.rsplit(".", 1)[0] + ".json")
        write_html(report_dict, out_html_path)
        write_json(report, json_out)

    elapsed_time = round(time.time() - start_time, 2)

    # Standard output line for test suite compatibility
    print(
        f"Safe to skip: {safe_to_skip_lines} lines across {len(sorted_findings)} findings "
        f"({dead_functions_count} dead, {duplicate_findings_count} duplicate, {needs_review_count} needs review)"
    )

    # Rich Summary Table
    table = Table(title="[bold green]Triage Summary[/bold green]", show_header=True, header_style="bold magenta", border_style="dim")
    table.add_column("Metric", style="bold")
    table.add_column("Value", justify="right")

    table.add_row("Scanned Directory", f"{repo_root.name}")
    table.add_row("Files / Functions / LOC", f"{len(files)} files / {meta.total_functions} functions / {total_lines:,} LOC")
    table.add_row("Safe to Skip Lines", f"[bold green]{safe_to_skip_lines:,} lines ({safe_to_skip_pct}%)[/bold green]")
    table.add_row("Dead Functions", f"{dead_functions_count} ({dead_lines_sum:,} lines)")
    table.add_row("Duplicate Clusters", f"{len(dup_clusters)} ({duplicate_lines_sum:,} lines)")
    table.add_row("Needs Review (Dynamic)", f"[bold yellow]{needs_review_count}[/bold yellow] ({needs_review_lines_sum:,} lines)")
    table.add_row("Execution Time", f"{elapsed_time}s")

    console.print("\n", table)

    if out_html_path:
        console.print(f"[bold green]+[/bold green] HTML report generated: [underline]{out_html_path}[/underline]")
    if out_json_path:
        console.print(f"[bold green]+[/bold green] JSON findings exported: [underline]{out_json_path}[/underline]")


def symbols_command(args: argparse.Namespace) -> None:
    """Execute the symbols command to list all defined symbols in the codebase."""
    repo_root = Path(args.path).resolve()
    if not repo_root.exists() or not repo_root.is_dir():
        err_console.print(f"[bold red]Error:[/bold red] Target path '[bold]{args.path}[/bold]' is invalid.")
        sys.exit(1)

    print_banner()

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
    if not repo_root.exists() or not repo_root.is_dir():
        err_console.print(f"[bold red]Error:[/bold red] Target path '[bold]{args.path}[/bold]' is invalid.")
        sys.exit(1)

    print_banner()

    files = find_python_files(repo_root, exclude=args.exclude)
    modules = {}
    for file_path in files:
        tree = parse_file(file_path)
        if tree is not None:
            modules[file_path] = tree

    symbol_table = build_symbol_table(modules, repo_root)
    call_graph = build_call_graph(modules, symbol_table, repo_root)
    entry_points = detect_entry_points(
        modules,
        symbol_table,
        user_entries=args.entry,
        repo_root=repo_root,
        frameworks_enabled=getattr(args, "frameworks", False)
    )

    dead_symbols = find_dead_code(call_graph, entry_points, symbol_table, modules, repo_root)

    sorted_entries = sorted(list(entry_points))
    print(f"Entry points: {sorted_entries}")

    sorted_dead = sorted(dead_symbols, key=lambda s: (s.file, s.line_start))
    print("Dead candidates:")
    for sym in sorted_dead:
        location = f"{sym.file}:{sym.line_start}-{sym.line_end}"
        print(f"  {sym.qualified_name:<35} {location:<30} {sym.lines}")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="skiplist",
        description=f"SkipList v{VERSION} - {TAGLINE}",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--version", action="version", version=f"skiplist v{VERSION}")

    subparsers = parser.add_subparsers(dest="command", required=True)

    # Analyze command
    analyze_parser = subparsers.add_parser(
        "analyze",
        help="Analyze a Python codebase for dead and duplicate code.",
        description="Run a full triage analysis on a Python codebase and generate HTML/JSON reports."
    )
    analyze_parser.add_argument("path", help="Path to Python codebase root directory")
    analyze_parser.add_argument("--entry", action="append", default=[], help="Specify custom entry point file/module (repeatable)")
    analyze_parser.add_argument("--exclude", action="append", default=[], help="Exclude file/directory path pattern (repeatable)")
    analyze_parser.add_argument("--out", default="report.html", help="Output file path (default: report.html)")
    analyze_parser.add_argument("--format", choices=["html", "json", "both"], default="html", help="Report format (default: html)")
    analyze_parser.add_argument("--frameworks", action="store_true", help="Enable framework-aware entry point detection (Flask/FastAPI/Click/Celery)")

    # Symbols command
    symbols_parser = subparsers.add_parser(
        "symbols",
        help="Build and print symbol table for a Python codebase.",
        description="List all defined functions, classes, and methods with line ranges and LOC."
    )
    symbols_parser.add_argument("path", help="Path to Python codebase root directory")
    symbols_parser.add_argument("--exclude", action="append", default=[], help="Exclude file/directory path pattern (repeatable)")

    # Deadcode command
    deadcode_parser = subparsers.add_parser(
        "deadcode",
        help="Find dead code symbols using call graph reachability.",
        description="Inspect entry points and unreachable candidate symbols."
    )
    deadcode_parser.add_argument("path", help="Path to Python codebase root directory")
    deadcode_parser.add_argument("--entry", action="append", default=[], help="Specify custom entry point file/module (repeatable)")
    deadcode_parser.add_argument("--exclude", action="append", default=[], help="Exclude file/directory path pattern (repeatable)")
    deadcode_parser.add_argument("--frameworks", action="store_true", help="Enable framework-aware entry point detection")

    try:
        args = parser.parse_args()
        if args.command == "analyze":
            analyze_command(args)
        elif args.command == "symbols":
            symbols_command(args)
        elif args.command == "deadcode":
            deadcode_command(args)
    except Exception as exc:
        if "--debug" in sys.argv:
            raise exc
        err_console.print(f"[bold red]Error:[/bold red] {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
