"""Unit tests for DockerLens fixer."""
import pytest
from dockerlens.fixer import (
    fix_sudo,
    fix_add_to_copy,
    fix_apt_cache,
    fix_apt_install_recommends,
    fix_shell_form_entrypoint,
    apply_fixes,
)
from dockerlens.parser import parse_dockerfile


class TestFixSudo:
    def test_removes_sudo(self):
        content = "FROM ubuntu\nRUN sudo apt-get update\n"
        result = parse_dockerfile(content)
        fixes = fix_sudo(result.instructions)
        assert len(fixes) == 1
        assert "sudo" not in fixes[0][1]


class TestFixAddToCopy:
    def test_replaces_add_with_copy(self):
        content = "FROM alpine\nADD . /app\n"
        result = parse_dockerfile(content)
        fixes = fix_add_to_copy(result.instructions)
        assert len(fixes) == 1
        assert "COPY" in fixes[0][1]

    def test_keeps_add_for_tar(self):
        content = "FROM alpine\nADD archive.tar.gz /opt/\n"
        result = parse_dockerfile(content)
        fixes = fix_add_to_copy(result.instructions)
        assert len(fixes) == 0


class TestFixAptCache:
    def test_adds_cache_cleanup(self):
        content = "FROM ubuntu\nRUN apt-get install -y curl\n"
        result = parse_dockerfile(content)
        fixes = fix_apt_cache(result.instructions)
        assert len(fixes) == 1
        assert "rm -rf /var/lib/apt/lists/*" in fixes[0][1]


class TestFixAptInstallRecommends:
    def test_adds_flag(self):
        content = "FROM ubuntu\nRUN apt-get install -y curl\n"
        result = parse_dockerfile(content)
        fixes = fix_apt_install_recommends(result.instructions)
        assert len(fixes) == 1
        assert "--no-install-recommends" in fixes[0][1]


class TestFixShellFormEntrypoint:
    def test_converts_to_exec_form(self):
        content = "FROM alpine\nENTRYPOINT python3 app.py\n"
        result = parse_dockerfile(content)
        fixes = fix_shell_form_entrypoint(result.instructions)
        assert len(fixes) == 1
        assert fixes[0][1].startswith("ENTRYPOINT [")
        assert '"python3"' in fixes[0][1]
        assert '"app.py"' in fixes[0][1]


class TestApplyFixes:
    def test_apply_single_fix(self):
        content = "FROM ubuntu\nRUN sudo apt-get update\n"
        result = parse_dockerfile(content)
        fixes = fix_sudo(result.instructions)
        fixed = apply_fixes(content, fixes)
        assert "sudo" not in fixed
        assert "apt-get update" in fixed

    def test_apply_multiple_fixes(self):
        content = "FROM alpine\nADD . /app\nENTRYPOINT python3 app.py\n"
        result = parse_dockerfile(content)
        all_fixes = []
        all_fixes.extend(fix_add_to_copy(result.instructions))
        all_fixes.extend(fix_shell_form_entrypoint(result.instructions))
        fixed = apply_fixes(content, all_fixes)
        assert "COPY . /app" in fixed
        assert 'ENTRYPOINT ["python3", "app.py"]' in fixed
