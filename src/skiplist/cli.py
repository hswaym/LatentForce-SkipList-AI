import click
import sys
from pathlib import Path
from skiplist.analyzer import analyze_directory
from skiplist.reporter import export_json, export_html


@click.group()
def main():
    """SkipList: Pre-migration code-triage tool."""
    pass


@main.command()
@click.argument("target_dir", type=click.Path(exists=True, file_okay=False, dir_okay=True))
@click.option("--html", "html_out", type=click.Path(), help="Path to save HTML report")
@click.option("--json", "json_out", type=click.Path(), help="Path to save JSON findings")
def analyze(target_dir, html_out, json_out):
    """Analyze a project directory for dead code and duplicate blocks."""
    click.echo(f"Analyzing project directory: {target_dir}")
    results = analyze_directory(target_dir)

    summary = results["summary"]
    click.echo("\n--- Triage Summary ---")
    click.echo(f"Files Scanned:       {summary['total_files']}")
    click.echo(f"Lines of Code:       {summary['total_lines']}")
    click.echo(f"Dead Code Symbols:   {summary['dead_functions_count'] + summary['dead_classes_count']}")
    click.echo(f"Duplicate Blocks:    {summary['duplicate_blocks_count']}")

    if json_out:
        export_json(results, json_out)
        click.echo(f"\nJSON report exported to: {json_out}")

    if html_out:
        export_html(results, html_out)
        click.echo(f"HTML report exported to: {html_out}")


if __name__ == "__main__":
    main()
