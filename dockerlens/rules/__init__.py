"""
Lint rules for DockerLens.
Each rule is a function that checks for a specific Dockerfile anti-pattern.
"""

import re
from dataclasses import dataclass
from enum import Enum
from typing import Optional

from ..parser import Instruction, ParseResult


class Severity(str, Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
    STYLE = "style"


@dataclass
class LintIssue:
    """A single lint issue found in a Dockerfile."""
    rule_id: str
    severity: Severity
    line_number: int
    message: str
    suggestion: str = ""


@dataclass
class LintRule:
    """Definition of a lint rule."""
    rule_id: str
    name: str
    description: str
    severity: Severity


# ──────────────────────── Rule Definitions ────────────────────────

RULE_DEFINITIONS: dict[str, LintRule] = {
    "DL0001": LintRule("DL0001", "latest-tag", "Using ':latest' tag is unreliable and non-reproducible", Severity.WARNING),
    "DL0002": LintRule("DL0002", "root-user", "Container runs as root — use USER directive for security", Severity.ERROR),
    "DL0003": LintRule("DL0003", "apt-cache", "apt-get cache not cleaned in same RUN layer", Severity.WARNING),
    "DL0004": LintRule("DL0004", "sudo-usage", "Using sudo in Dockerfile is unnecessary and risky", Severity.ERROR),
    "DL0005": LintRule("DL0005", "add-vs-copy", "Use COPY instead of ADD for simple file copies", Severity.INFO),
    "DL0006": LintRule("DL0006", "consecutive-run", "Consecutive RUN instructions should be combined", Severity.WARNING),
    "DL0007": LintRule("DL0007", "missing-healthcheck", "No HEALTHCHECK instruction defined", Severity.WARNING),
    "DL0008": LintRule("DL0008", "privileged-ports", "Exposing privileged ports (1-1023) may require root", Severity.INFO),
    "DL0009": LintRule("DL0009", "env-secret", "Possible secret/credential in ENV instruction", Severity.ERROR),
    "DL0010": LintRule("DL0010", "invalid-port", "Invalid EXPOSE port number", Severity.ERROR),
    "DL0011": LintRule("DL0011", "apt-no-install-recommends", "apt-get install without --no-install-recommends bloats image", Severity.WARNING),
    "DL0012": LintRule("DL0012", "apt-no-version-pin", "apt-get install without version pinning is non-reproducible", Severity.INFO),
    "DL0013": LintRule("DL0013", "shell-form-entrypoint", "Use exec form for ENTRYPOINT to receive signals properly", Severity.WARNING),
    "DL0014": LintRule("DL0014", "shell-form-cmd", "Use exec form for CMD to receive signals properly", Severity.WARNING),
    "DL0015": LintRule("DL0015", "missing-user", "No USER instruction — container will run as root by default", Severity.ERROR),
    "DL0016": LintRule("DL0016", "unpinned-from", "FROM image not pinned to a digest for reproducibility", Severity.INFO),
    "DL0017": LintRule("DL0017", "workdir-absolute", "WORKDIR should use absolute paths for clarity", Severity.STYLE),
    "DL0018": LintRule("DL0018", "run-pipe-chain", "Use && to chain RUN commands and reduce layers", Severity.WARNING),
}


# ──────────────────────── Rule Implementations ────────────────────────

def check_latest_tag(result: ParseResult) -> list[LintIssue]:
    """DL0001: FROM image uses :latest tag."""
    issues = []
    for inst in result.instructions:
        if inst.command == "FROM":
            image = inst.arguments.split()[0] if inst.arguments else ""
            if image.endswith(":latest") or (":" not in image and "@" not in image and image != "scratch"):
                issues.append(LintIssue(
                    rule_id="DL0001",
                    severity=Severity.WARNING,
                    line_number=inst.line_number,
                    message=f"Image '{image}' uses implicit :latest tag — pin a specific version",
                    suggestion=f"Replace '{image}' with '{image}:<version>' or use digest '@sha256:...'",
                ))
    return issues


def check_root_user(result: ParseResult) -> list[LintIssue]:
    """DL0002: Container runs as root."""
    has_user = False
    last_user_line = 0
    issues = []
    for inst in result.instructions:
        if inst.command == "USER":
            has_user = True
            last_user_line = inst.line_number
            user = inst.arguments.strip().lower()
            if user == "root" or user == "0":
                issues.append(LintIssue(
                    rule_id="DL0002",
                    severity=Severity.ERROR,
                    line_number=inst.line_number,
                    message="USER set to root — use a non-root user",
                    suggestion="Create and use a non-root user: RUN adduser --disabled-password appuser && USER appuser",
                ))
    # Check if there's no USER at all (covered by DL0015)
    return issues


def check_apt_cache(result: ParseResult) -> list[LintIssue]:
    """DL0003: apt-get cache not cleaned in same RUN."""
    issues = []
    for inst in result.instructions:
        if inst.command == "RUN":
            args = inst.arguments
            has_apt_install = "apt-get install" in args or "apt install" in args
            has_rm_cache = "rm -rf /var/lib/apt/lists" in args
            if has_apt_install and not has_rm_cache:
                issues.append(LintIssue(
                    rule_id="DL0003",
                    severity=Severity.WARNING,
                    line_number=inst.line_number,
                    message="apt-get install without cleaning cache in the same RUN layer",
                    suggestion="Add '&& rm -rf /var/lib/apt/lists/*' at the end of the RUN command",
                ))
    return issues


def check_sudo(result: ParseResult) -> list[LintIssue]:
    """DL0004: Using sudo in Dockerfile."""
    issues = []
    for inst in result.instructions:
        if inst.command == "RUN" and "sudo " in inst.arguments:
            issues.append(LintIssue(
                rule_id="DL0004",
                severity=Severity.ERROR,
                line_number=inst.line_number,
                message="Using sudo in Dockerfile is unnecessary — RUN already executes as root by default",
                suggestion="Remove 'sudo' from the command",
            ))
    return issues


def check_add_vs_copy(result: ParseResult) -> list[LintIssue]:
    """DL0005: Use COPY instead of ADD for simple file operations."""
    issues = []
    for inst in result.instructions:
        if inst.command == "ADD":
            # ADD is fine for URLs or tar archives, flag for simple copies
            args = inst.arguments
            has_url = any(arg.startswith(("http://", "https://")) for arg in args.split())
            has_tar = any(arg.endswith((".tar", ".tar.gz", ".tgz", ".tar.bz2", ".tbz2", ".tar.xz")) for arg in args.split())
            if not has_url and not has_tar:
                issues.append(LintIssue(
                    rule_id="DL0005",
                    severity=Severity.INFO,
                    line_number=inst.line_number,
                    message="Use COPY instead of ADD for simple file copies — ADD has extra tar/URL behavior",
                    suggestion=f"Replace 'ADD {args}' with 'COPY {args}'",
                ))
    return issues


def check_consecutive_run(result: ParseResult) -> list[LintIssue]:
    """DL0006: Consecutive RUN should be combined."""
    issues = []
    prev_run: Optional[Instruction] = None
    for inst in result.instructions:
        if inst.command == "RUN":
            if prev_run is not None:
                issues.append(LintIssue(
                    rule_id="DL0006",
                    severity=Severity.WARNING,
                    line_number=inst.line_number,
                    message=f"Consecutive RUN instructions (line {prev_run.line_number} and {inst.line_number}) should be combined with &&",
                    suggestion="Combine RUN commands with && to reduce image layers",
                ))
            prev_run = inst
        elif not inst.is_blank and not inst.is_comment:
            prev_run = None
    return issues


def check_healthcheck(result: ParseResult) -> list[LintIssue]:
    """DL0007: No HEALTHCHECK defined."""
    has_healthcheck = any(
        inst.command == "HEALTHCHECK" for inst in result.instructions
    )
    if not has_healthcheck:
        return [LintIssue(
            rule_id="DL0007",
            severity=Severity.WARNING,
            line_number=0,
            message="No HEALTHCHECK instruction defined — container orchestration won't detect failures",
            suggestion="Add: HEALTHCHECK --interval=30s CMD curl -f http://localhost/ || exit 1",
        )]
    return []


def check_privileged_ports(result: ParseResult) -> list[LintIssue]:
    """DL0008: Exposing privileged ports."""
    issues = []
    for inst in result.instructions:
        if inst.command == "EXPOSE":
            ports = re.findall(r"\d+", inst.arguments)
            for port in ports:
                if 1 <= int(port) <= 1023:
                    issues.append(LintIssue(
                        rule_id="DL0008",
                        severity=Severity.INFO,
                        line_number=inst.line_number,
                        message=f"Port {port} is privileged (1-1023) — may require root to bind",
                        suggestion=f"Use a non-privileged port (>1023) and map at runtime with -p",
                    ))
    return issues


def check_env_secret(result: ParseResult) -> list[LintIssue]:
    """DL0009: Possible secret in ENV."""
    secret_patterns = [
        (r"(?i)(PASSWORD|SECRET|TOKEN|API_KEY|PRIVATE_KEY|ACCESS_KEY)\s*=\s*\S+", "secret/credential"),
    ]
    issues = []
    for inst in result.instructions:
        if inst.command == "ENV":
            for pattern, desc in secret_patterns:
                if re.search(pattern, inst.arguments):
                    issues.append(LintIssue(
                        rule_id="DL0009",
                        severity=Severity.ERROR,
                        line_number=inst.line_number,
                        message=f"Possible {desc} exposed in ENV — secrets should use runtime injection",
                        suggestion="Use Docker secrets, --env-file, or runtime -e flags instead of hardcoding in ENV",
                    ))
    return issues


def check_invalid_port(result: ParseResult) -> list[LintIssue]:
    """DL0010: Invalid EXPOSE port number."""
    issues = []
    for inst in result.instructions:
        if inst.command == "EXPOSE":
            ports = re.findall(r"\d+", inst.arguments)
            for port in ports:
                p = int(port)
                if p < 1 or p > 65535:
                    issues.append(LintIssue(
                        rule_id="DL0010",
                        severity=Severity.ERROR,
                        line_number=inst.line_number,
                        message=f"Invalid port number: {port} (must be 1-65535)",
                        suggestion="Use a valid port number between 1 and 65535",
                    ))
    return issues


def check_apt_no_install_recommends(result: ParseResult) -> list[LintIssue]:
    """DL0011: apt-get install without --no-install-recommends."""
    issues = []
    for inst in result.instructions:
        if inst.command == "RUN" and "apt-get install" in inst.arguments:
            if "--no-install-recommends" not in inst.arguments:
                issues.append(LintIssue(
                    rule_id="DL0011",
                    severity=Severity.WARNING,
                    line_number=inst.line_number,
                    message="apt-get install without --no-install-recommends installs unnecessary packages",
                    suggestion="Add --no-install-recommends to apt-get install",
                ))
    return issues


def check_apt_no_version_pin(result: ParseResult) -> list[LintIssue]:
    """DL0012: apt-get install without version pinning."""
    issues = []
    for inst in result.instructions:
        if inst.command == "RUN" and "apt-get install" in inst.arguments:
            # Find packages after 'apt-get install'
            match = re.search(r"apt-get\s+install\s+(.+?)(?:\s*&&|$)", inst.arguments)
            if match:
                packages = match.group(1).strip()
                # Remove flags
                packages = re.sub(r"--\S+\s*", "", packages).strip()
                if packages and "=" not in packages:
                    issues.append(LintIssue(
                        rule_id="DL0012",
                        severity=Severity.INFO,
                        line_number=inst.line_number,
                        message="apt-get install without version pinning — builds may not be reproducible",
                        suggestion="Pin package versions: apt-get install package=version",
                    ))
    return issues


def check_shell_form_entrypoint(result: ParseResult) -> list[LintIssue]:
    """DL0013: Shell form used for ENTRYPOINT."""
    issues = []
    for inst in result.instructions:
        if inst.command == "ENTRYPOINT":
            if not inst.arguments.strip().startswith("["):
                issues.append(LintIssue(
                    rule_id="DL0013",
                    severity=Severity.WARNING,
                    line_number=inst.line_number,
                    message="Shell form ENTRYPOINT won't receive signals (SIGTERM) properly",
                    suggestion="Use exec form: ENTRYPOINT [\"executable\", \"arg\"]",
                ))
    return issues


def check_shell_form_cmd(result: ParseResult) -> list[LintIssue]:
    """DL0014: Shell form used for CMD."""
    issues = []
    for inst in result.instructions:
        if inst.command == "CMD":
            if not inst.arguments.strip().startswith("["):
                issues.append(LintIssue(
                    rule_id="DL0014",
                    severity=Severity.WARNING,
                    line_number=inst.line_number,
                    message="Shell form CMD won't receive signals (SIGTERM) properly",
                    suggestion="Use exec form: CMD [\"executable\", \"arg\"]",
                ))
    return issues


def check_missing_user(result: ParseResult) -> list[LintIssue]:
    """DL0015: No USER instruction."""
    has_user = any(inst.command == "USER" for inst in result.instructions)
    if not has_user:
        return [LintIssue(
            rule_id="DL0015",
            severity=Severity.ERROR,
            line_number=0,
            message="No USER instruction — container will run as root by default",
            suggestion="Add a non-root user: RUN adduser --disabled-password appuser && USER appuser",
        )]
    return []


def check_unpinned_from(result: ParseResult) -> list[LintIssue]:
    """DL0016: FROM image not pinned to digest."""
    issues = []
    for inst in result.instructions:
        if inst.command == "FROM":
            image = inst.arguments.split()[0] if inst.arguments else ""
            if "@" not in image and image != "scratch":
                issues.append(LintIssue(
                    rule_id="DL0016",
                    severity=Severity.INFO,
                    line_number=inst.line_number,
                    message=f"Image '{image}' not pinned to a digest — builds may drift over time",
                    suggestion=f"Pin to digest: FROM {image}@sha256:<hash>",
                ))
    return issues


def check_workdir_absolute(result: ParseResult) -> list[LintIssue]:
    """DL0017: WORKDIR should use absolute paths."""
    issues = []
    for inst in result.instructions:
        if inst.command == "WORKDIR":
            path = inst.arguments.strip()
            if not path.startswith("/") and not path.startswith("$"):
                issues.append(LintIssue(
                    rule_id="DL0017",
                    severity=Severity.STYLE,
                    line_number=inst.line_number,
                    message=f"WORKDIR '{path}' is a relative path — use absolute for clarity and predictability",
                    suggestion=f"Use absolute path: WORKDIR /{path}",
                ))
    return issues


# ──────────────────────── Rule Registry ────────────────────────

ALL_RULES: dict[str, callable] = {
    "DL0001": check_latest_tag,
    "DL0002": check_root_user,
    "DL0003": check_apt_cache,
    "DL0004": check_sudo,
    "DL0005": check_add_vs_copy,
    "DL0006": check_consecutive_run,
    "DL0007": check_healthcheck,
    "DL0008": check_privileged_ports,
    "DL0009": check_env_secret,
    "DL0010": check_invalid_port,
    "DL0011": check_apt_no_install_recommends,
    "DL0012": check_apt_no_version_pin,
    "DL0013": check_shell_form_entrypoint,
    "DL0014": check_shell_form_cmd,
    "DL0015": check_missing_user,
    "DL0016": check_unpinned_from,
    "DL0017": check_workdir_absolute,
}
