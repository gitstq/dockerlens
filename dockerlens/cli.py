"""
DockerLens CLI - Main entry point.
Smart Dockerfile linter, analyzer & auto-fixer CLI.
"""

import os
import sys

# Fix Windows console encoding for emoji/unicode
if sys.platform == "win32":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from . import __version__
from .linter import lint_dockerfile
from .fixer import FIXERS, apply_fixes
from .parser import parse_dockerfile
from .rules import RULE_DEFINITIONS, Severity

console = Console()


@click.group()
@click.version_option(version=__version__, prog_name="dockerlens")
def main():
    """🔍 DockerLens - Smart Dockerfile linter, analyzer & auto-fixer CLI"""
    pass


@main.command()
@click.argument("path", type=click.Path(exists=True))
@click.option("--rules", "-r", default=None, help="Comma-separated rule IDs to check (e.g. DL0001,DL0002)")
@click.option("--severity", "-s", default="style", type=click.Choice(["error", "warning", "info", "style"]), help="Minimum severity to report")
@click.option("--json-output", "-j", is_flag=True, help="Output results as JSON")
@click.option("--ci", is_flag=True, help="CI mode: exit with code 1 if any errors found")
def lint(path: str, rules: str, severity: str, json_output: bool, ci: bool):
    """🔍 Lint a Dockerfile for anti-patterns and issues."""
    rule_list = [r.strip() for r in rules.split(",")] if rules else None
    severity_map = {
        "error": Severity.ERROR,
        "warning": Severity.WARNING,
        "info": Severity.INFO,
        "style": Severity.STYLE,
    }

    result = lint_dockerfile(
        path=path,
        rules=rule_list,
        severity_threshold=severity_map[severity],
    )

    if json_output:
        import json as json_mod
        data = {
            "file": result.file_path,
            "score": result.score,
            "total_lines": result.total_lines,
            "errors": result.error_count,
            "warnings": result.warning_count,
            "info": result.info_count,
            "style": result.style_count,
            "issues": [
                {
                    "rule_id": i.rule_id,
                    "severity": i.severity.value,
                    "line": i.line_number,
                    "message": i.message,
                    "suggestion": i.suggestion,
                }
                for i in result.issues
            ],
        }
        console.print_json(json_mod.dumps(data, ensure_ascii=False, indent=2))
    else:
        # Display results with Rich
        _print_lint_result(result, path)

    if ci and result.error_count > 0:
        sys.exit(1)


@main.command()
@click.argument("path", type=click.Path(exists=True))
@click.option("--output", "-o", default=None, help="Output file path (default: overwrite in-place)")
@click.option("--dry-run", is_flag=True, help="Show fixes without applying them")
def fix(path: str, output: str, dry_run: bool):
    """🔧 Auto-fix common Dockerfile issues."""
    from pathlib import Path as P

    content = P(path).read_text(encoding="utf-8")
    parse_result = parse_dockerfile(content)
    all_fixes = []

    for rule_id, fixer_func in FIXERS.items():
        try:
            fixes = fixer_func(parse_result.instructions)
            all_fixes.extend(fixes)
        except Exception:
            pass

    if not all_fixes:
        console.print("[bold green]✅ No auto-fixable issues found![/bold green]")
        return

    # Deduplicate fixes by line number (keep last)
    fix_map: dict[int, str] = {}
    for line_num, new_line in all_fixes:
        fix_map[line_num] = new_line

    if dry_run:
        console.print(f"\n[bold]🔧 {len(fix_map)} auto-fix(es) available:[/bold]\n")
        lines = content.splitlines()
        for line_num, new_line in sorted(fix_map.items()):
            old = lines[line_num - 1].strip()
            new = new_line.strip()
            console.print(f"  Line {line_num}:")
            console.print(f"    [red]- {old}[/red]")
            console.print(f"    [green]+ {new}[/green]")
        console.print("\n[dim]Run without --dry-run to apply fixes.[/dim]")
    else:
        fixes_list = list(fix_map.items())
        fixed_content = apply_fixes(content, fixes_list)
        out_path = output or path
        P(out_path).write_text(fixed_content, encoding="utf-8")
        console.print(f"[bold green]✅ Applied {len(fix_map)} fix(es) to {out_path}[/bold green]")


@main.command(name="rules")
def list_rules():
    """📋 List all available lint rules."""
    table = Table(title="📋 DockerLens Lint Rules", show_lines=True)
    table.add_column("Rule ID", style="bold cyan", width=8)
    table.add_column("Name", style="bold", width=25)
    table.add_column("Severity", width=10)
    table.add_column("Description", max_width=55)
    table.add_column("Auto-fix", width=8)

    severity_colors = {
        Severity.ERROR: "bold red",
        Severity.WARNING: "yellow",
        Severity.INFO: "blue",
        Severity.STYLE: "dim",
    }

    for rule_id, rule in sorted(RULE_DEFINITIONS.items()):
        has_fix = "✅" if rule_id in FIXERS else "—"
        table.add_row(
            rule_id,
            rule.name,
            f"[{severity_colors[rule.severity]}]{rule.severity.value}[/{severity_colors[rule.severity]}]",
            rule.description,
            has_fix,
        )

    console.print(table)


@main.command()
@click.argument("path", type=click.Path(exists=True))
def score(path: str):
    """📊 Score a Dockerfile (0-100) based on best practices."""
    result = lint_dockerfile(path=path)

    # Color based on score
    if result.score >= 90:
        color = "bold green"
        emoji = "🌟"
    elif result.score >= 70:
        color = "yellow"
        emoji = "👍"
    elif result.score >= 50:
        color = "bold yellow"
        emoji = "⚠️"
    else:
        color = "bold red"
        emoji = "❌"

    score_text = Text()
    score_text.append(f"\n  {emoji} Dockerfile Score: ", style="bold")
    score_text.append(f"{result.score}/100\n", style=color)

    breakdown = (
        f"  📁 File: {result.file_path}\n"
        f"  📏 Lines: {result.total_lines}\n"
        f"  🔴 Errors: {result.error_count}\n"
        f"  🟡 Warnings: {result.warning_count}\n"
        f"  🔵 Info: {result.info_count}\n"
        f"  ⚪ Style: {result.style_count}\n"
    )

    console.print(Panel(score_text.plain + breakdown, title="DockerLens Score", border_style=color))


def _print_lint_result(result, path: str):
    """Pretty-print lint results with Rich."""
    # Header
    if result.error_count > 0:
        status = "[bold red]❌ Issues found[/bold red]"
    elif result.warning_count > 0:
        status = "[yellow]⚠️ Warnings found[/yellow]"
    else:
        status = "[bold green]✅ All checks passed[/bold green]"

    console.print(f"\n{status} — [dim]{result.file_path}[/dim]\n")

    if not result.issues:
        console.print("[bold green]🎉 No issues found! Your Dockerfile looks great.[/bold green]")
        return

    # Issues table
    table = Table(show_lines=True)
    table.add_column("Line", style="dim", width=5)
    table.add_column("Severity", width=10)
    table.add_column("Rule", style="bold cyan", width=8)
    table.add_column("Message", max_width=50)
    table.add_column("Suggestion", style="green", max_width=35)

    severity_styles = {
        Severity.ERROR: "bold red",
        Severity.WARNING: "yellow",
        Severity.INFO: "blue",
        Severity.STYLE: "dim",
    }

    for issue in result.issues:
        style = severity_styles.get(issue.severity, "")
        table.add_row(
            str(issue.line_number) if issue.line_number > 0 else "—",
            f"[{style}]{issue.severity.value}[/{style}]",
            issue.rule_id,
            issue.message,
            issue.suggestion or "—",
        )

    console.print(table)

    # Summary
    console.print(
        f"\n  🔴 {result.error_count} errors · "
        f"🟡 {result.warning_count} warnings · "
        f"🔵 {result.info_count} info · "
        f"⚪ {result.style_count} style"
    )
    console.print(f"  📊 Score: [bold]{result.score}/100[/bold]\n")


if __name__ == "__main__":
    main()
