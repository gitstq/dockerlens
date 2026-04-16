"""
Dockerfile parser for DockerLens.
Parses a Dockerfile into a structured list of instructions.
"""

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class Instruction:
    """Represents a single Dockerfile instruction."""
    line_number: int
    command: str          # FROM, RUN, COPY, etc.
    arguments: str        # Everything after the command
    raw_line: str         # Original line text
    is_comment: bool = False
    is_blank: bool = False


@dataclass
class ParseResult:
    """Result of parsing a Dockerfile."""
    instructions: list[Instruction]
    total_lines: int
    from_images: list[str] = field(default_factory=list)
    stages: list[str] = field(default_factory=list)


# Dockerfile commands (case-insensitive)
DOCKERFILE_COMMANDS = {
    "from", "run", "cmd", "label", "maintainer", "expose", "env",
    "add", "copy", "entrypoint", "volume", "user", "workdir",
    "arg", "onbuild", "stopsignal", "healthcheck", "shell",
}


def parse_dockerfile(content: str) -> ParseResult:
    """Parse Dockerfile content into structured instructions."""
    instructions: list[Instruction] = []
    from_images: list[str] = []
    stages: list[str] = []
    lines = content.splitlines()

    for i, line in enumerate(lines, start=1):
        stripped = line.strip()

        # Blank line
        if not stripped:
            instructions.append(Instruction(
                line_number=i, command="", arguments="",
                raw_line=line, is_blank=True,
            ))
            continue

        # Comment line
        if stripped.startswith("#"):
            instructions.append(Instruction(
                line_number=i, command="#", arguments=stripped[1:].strip(),
                raw_line=line, is_comment=True,
            ))
            continue

        # Parse command
        # Handle continuation lines (\)
        # For simplicity, we handle each line independently
        match = re.match(r"^(\S+)\s+(.*)", stripped)
        if match:
            cmd = match.group(1).upper()
            args = match.group(2)
            inst = Instruction(
                line_number=i, command=cmd, arguments=args,
                raw_line=line,
            )
            instructions.append(inst)

            # Track FROM images and build stages
            if cmd == "FROM":
                # FROM image AS stage or FROM image
                from_match = re.match(
                    r"^(.+?)\s+AS\s+(\S+)",
                    args,
                    re.IGNORECASE,
                )
                if from_match:
                    from_images.append(from_match.group(1).strip())
                    stages.append(from_match.group(2))
                else:
                    from_images.append(args.strip())
        else:
            # Could be a syntax error or continuation
            instructions.append(Instruction(
                line_number=i, command=stripped, arguments="",
                raw_line=line,
            ))

    return ParseResult(
        instructions=instructions,
        total_lines=len(lines),
        from_images=from_images,
        stages=stages,
    )


def parse_dockerfile_file(path: str | Path) -> ParseResult:
    """Parse a Dockerfile from a file path."""
    content = Path(path).read_text(encoding="utf-8")
    return parse_dockerfile(content)
