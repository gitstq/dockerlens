"""
Auto-fixer for DockerLens.
Generates suggested fixes for common Dockerfile issues.
"""

import re
from .parser import Instruction, ParseResult
from .rules import LintIssue, Severity


def fix_latest_tag(instructions: list[Instruction]) -> list[tuple[int, str]]:
    """Fix :latest tags by adding a placeholder version."""
    fixes = []
    for inst in instructions:
        if inst.command == "FROM":
            image = inst.arguments.split()[0]
            if image.endswith(":latest"):
                fixed = inst.raw_line.replace(":latest", ":stable")
                fixes.append((inst.line_number, fixed))
            elif ":" not in image and "@" not in image and image != "scratch":
                fixed = inst.raw_line.replace(image, f"{image}:stable")
                fixes.append((inst.line_number, fixed))
    return fixes


def fix_sudo(instructions: list[Instruction]) -> list[tuple[int, str]]:
    """Remove sudo from RUN commands."""
    fixes = []
    for inst in instructions:
        if inst.command == "RUN" and "sudo " in inst.arguments:
            fixed = inst.raw_line.replace("sudo ", "")
            fixes.append((inst.line_number, fixed))
    return fixes


def fix_add_to_copy(instructions: list[Instruction]) -> list[tuple[int, str]]:
    """Replace ADD with COPY for simple file operations."""
    fixes = []
    for inst in instructions:
        if inst.command == "ADD":
            args = inst.arguments
            has_url = any(a.startswith(("http://", "https://")) for a in args.split())
            has_tar = any(a.endswith((".tar", ".tar.gz", ".tgz", ".tar.bz2", ".tbz2", ".tar.xz")) for a in args.split())
            if not has_url and not has_tar:
                fixed = re.sub(r"^(\s*)ADD\b", r"\1COPY", inst.raw_line, flags=re.IGNORECASE)
                fixes.append((inst.line_number, fixed))
    return fixes


def fix_apt_cache(instructions: list[Instruction]) -> list[tuple[int, str]]:
    """Add rm -rf /var/lib/apt/lists/* to apt-get install RUN layers."""
    fixes = []
    for inst in instructions:
        if inst.command == "RUN":
            args = inst.arguments
            has_apt_install = "apt-get install" in args or "apt install" in args
            has_rm_cache = "rm -rf /var/lib/apt/lists" in args
            if has_apt_install and not has_rm_cache:
                # Append cache cleanup
                fixed = inst.raw_line.rstrip("\\").rstrip()
                if fixed.endswith("&&"):
                    fixed += " rm -rf /var/lib/apt/lists/*"
                else:
                    fixed += " && rm -rf /var/lib/apt/lists/*"
                fixes.append((inst.line_number, fixed))
    return fixes


def fix_apt_install_recommends(instructions: list[Instruction]) -> list[tuple[int, str]]:
    """Add --no-install-recommends to apt-get install."""
    fixes = []
    for inst in instructions:
        if inst.command == "RUN" and "apt-get install" in inst.arguments:
            if "--no-install-recommends" not in inst.arguments:
                fixed = inst.raw_line.replace("apt-get install", "apt-get install --no-install-recommends")
                fixes.append((inst.line_number, fixed))
    return fixes


def fix_shell_form_entrypoint(instructions: list[Instruction]) -> list[tuple[int, str]]:
    """Convert shell form ENTRYPOINT to exec form."""
    fixes = []
    for inst in instructions:
        if inst.command == "ENTRYPOINT" and not inst.arguments.strip().startswith("["):
            args = inst.arguments.strip()
            parts = args.split()
            exec_form = '["' + '", "'.join(parts) + '"]'
            fixed = f"ENTRYPOINT {exec_form}"
            fixes.append((inst.line_number, fixed))
    return fixes


def fix_shell_form_cmd(instructions: list[Instruction]) -> list[tuple[int, str]]:
    """Convert shell form CMD to exec form."""
    fixes = []
    for inst in instructions:
        if inst.command == "CMD" and not inst.arguments.strip().startswith("["):
            args = inst.arguments.strip()
            parts = args.split()
            exec_form = '["' + '", "'.join(parts) + '"]'
            fixed = f"CMD {exec_form}"
            fixes.append((inst.line_number, fixed))
    return fixes


def apply_fixes(content: str, fixes: list[tuple[int, str]]) -> str:
    """Apply a list of (line_number, new_line) fixes to Dockerfile content."""
    lines = content.splitlines()
    # Apply from bottom to top to preserve line numbers
    for line_num, new_line in sorted(fixes, key=lambda x: -x[0]):
        if 0 < line_num <= len(lines):
            lines[line_num - 1] = new_line
    return "\n".join(lines)


FIXERS = {
    "DL0001": fix_latest_tag,
    "DL0003": fix_apt_cache,
    "DL0004": fix_sudo,
    "DL0005": fix_add_to_copy,
    "DL0011": fix_apt_install_recommends,
    "DL0013": fix_shell_form_entrypoint,
    "DL0014": fix_shell_form_cmd,
}
