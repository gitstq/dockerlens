"""
Linter engine for DockerLens.
Orchestrates rule execution and collects results.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from .parser import ParseResult, parse_dockerfile, parse_dockerfile_file
from .rules import ALL_RULES, RULE_DEFINITIONS, LintIssue, Severity


@dataclass
class LintResult:
    """Result of linting a Dockerfile."""
    file_path: str
    issues: list[LintIssue] = field(default_factory=list)
    total_lines: int = 0
    error_count: int = 0
    warning_count: int = 0
    info_count: int = 0
    style_count: int = 0

    @property
    def score(self) -> int:
        """Calculate a 0-100 score based on issues found."""
        if not self.issues:
            return 100
        penalty = (
            self.error_count * 15 +
            self.warning_count * 5 +
            self.info_count * 2 +
            self.style_count * 1
        )
        return max(0, 100 - penalty)


def lint_dockerfile(
    content: Optional[str] = None,
    path: Optional[str | Path] = None,
    rules: Optional[list[str]] = None,
    severity_threshold: Severity = Severity.STYLE,
) -> LintResult:
    """
    Lint a Dockerfile and return structured results.

    Args:
        content: Dockerfile content string (takes precedence over path)
        path: Path to Dockerfile
        rules: Specific rule IDs to run (None = all rules)
        severity_threshold: Minimum severity to report

    Returns:
        LintResult with issues and statistics
    """
    if content is not None:
        parse_result = parse_dockerfile(content)
    elif path is not None:
        parse_result = parse_dockerfile_file(path)
    else:
        raise ValueError("Either content or path must be provided")

    # Run rules
    rule_ids = rules if rules else list(ALL_RULES.keys())
    all_issues: list[LintIssue] = []

    for rule_id in rule_ids:
        if rule_id not in ALL_RULES:
            continue
        rule_func = ALL_RULES[rule_id]
        try:
            issues = rule_func(parse_result)
            all_issues.extend(issues)
        except Exception:
            pass  # Don't let a single rule crash the linter

    # Filter by severity threshold
    severity_order = {
        Severity.STYLE: 0,
        Severity.INFO: 1,
        Severity.WARNING: 2,
        Severity.ERROR: 3,
    }
    threshold_level = severity_order.get(severity_threshold, 0)
    filtered_issues = [
        i for i in all_issues
        if severity_order.get(i.severity, 0) >= threshold_level
    ]

    # Sort by line number, then severity
    filtered_issues.sort(key=lambda i: (i.line_number, -severity_order.get(i.severity, 0)))

    # Count severities
    result = LintResult(
        file_path=str(path) if path else "<stdin>",
        issues=filtered_issues,
        total_lines=parse_result.total_lines,
    )
    for issue in filtered_issues:
        if issue.severity == Severity.ERROR:
            result.error_count += 1
        elif issue.severity == Severity.WARNING:
            result.warning_count += 1
        elif issue.severity == Severity.INFO:
            result.info_count += 1
        elif issue.severity == Severity.STYLE:
            result.style_count += 1

    return result
