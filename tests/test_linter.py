"""Unit tests for DockerLens linter rules."""
import pytest
from dockerlens.linter import lint_dockerfile
from dockerlens.rules import Severity, ALL_RULES


class TestLatestTag:
    def test_latest_tag(self):
        result = lint_dockerfile(content="FROM ubuntu:latest\n")
        issues = [i for i in result.issues if i.rule_id == "DL0001"]
        assert len(issues) == 1
        assert issues[0].severity == Severity.WARNING

    def test_no_tag_implicit_latest(self):
        result = lint_dockerfile(content="FROM ubuntu\n")
        issues = [i for i in result.issues if i.rule_id == "DL0001"]
        assert len(issues) == 1

    def test_pinned_tag_no_issue(self):
        result = lint_dockerfile(content="FROM python:3.12-slim\n")
        issues = [i for i in result.issues if i.rule_id == "DL0001"]
        assert len(issues) == 0


class TestRootUser:
    def test_user_root(self):
        result = lint_dockerfile(content="FROM alpine\nUSER root\n")
        issues = [i for i in result.issues if i.rule_id == "DL0002"]
        assert len(issues) == 1
        assert issues[0].severity == Severity.ERROR

    def test_user_non_root(self):
        result = lint_dockerfile(content="FROM alpine\nUSER appuser\n")
        issues = [i for i in result.issues if i.rule_id == "DL0002"]
        assert len(issues) == 0


class TestAptCache:
    def test_apt_without_cache_cleanup(self):
        content = "FROM ubuntu\nRUN apt-get install -y curl\n"
        result = lint_dockerfile(content=content)
        issues = [i for i in result.issues if i.rule_id == "DL0003"]
        assert len(issues) == 1

    def test_apt_with_cache_cleanup(self):
        content = "FROM ubuntu\nRUN apt-get install -y curl && rm -rf /var/lib/apt/lists/*\n"
        result = lint_dockerfile(content=content)
        issues = [i for i in result.issues if i.rule_id == "DL0003"]
        assert len(issues) == 0


class TestSudo:
    def test_sudo_usage(self):
        content = "FROM ubuntu\nRUN sudo apt-get update\n"
        result = lint_dockerfile(content=content)
        issues = [i for i in result.issues if i.rule_id == "DL0004"]
        assert len(issues) == 1
        assert issues[0].severity == Severity.ERROR


class TestAddVsCopy:
    def test_add_simple_copy(self):
        content = "FROM alpine\nADD . /app\n"
        result = lint_dockerfile(content=content)
        issues = [i for i in result.issues if i.rule_id == "DL0005"]
        assert len(issues) == 1

    def test_add_tar_ok(self):
        content = "FROM alpine\nADD archive.tar.gz /opt/\n"
        result = lint_dockerfile(content=content)
        issues = [i for i in result.issues if i.rule_id == "DL0005"]
        assert len(issues) == 0

    def test_copy_no_issue(self):
        content = "FROM alpine\nCOPY . /app\n"
        result = lint_dockerfile(content=content)
        issues = [i for i in result.issues if i.rule_id == "DL0005"]
        assert len(issues) == 0


class TestConsecutiveRun:
    def test_consecutive_run(self):
        content = "FROM alpine\nRUN echo a\nRUN echo b\n"
        result = lint_dockerfile(content=content)
        issues = [i for i in result.issues if i.rule_id == "DL0006"]
        assert len(issues) >= 1


class TestHealthcheck:
    def test_no_healthcheck(self):
        result = lint_dockerfile(content="FROM alpine\nRUN echo hi\n")
        issues = [i for i in result.issues if i.rule_id == "DL0007"]
        assert len(issues) == 1

    def test_has_healthcheck(self):
        content = "FROM alpine\nHEALTHCHECK CMD curl -f http://localhost/ || exit 1\n"
        result = lint_dockerfile(content=content)
        issues = [i for i in result.issues if i.rule_id == "DL0007"]
        assert len(issues) == 0


class TestEnvSecret:
    def test_env_secret(self):
        content = "FROM alpine\nENV API_KEY=sk-12345\n"
        result = lint_dockerfile(content=content)
        issues = [i for i in result.issues if i.rule_id == "DL0009"]
        assert len(issues) == 1
        assert issues[0].severity == Severity.ERROR

    def test_env_normal(self):
        content = "FROM alpine\nENV APP_HOME=/app\n"
        result = lint_dockerfile(content=content)
        issues = [i for i in result.issues if i.rule_id == "DL0009"]
        assert len(issues) == 0


class TestMissingUser:
    def test_no_user(self):
        result = lint_dockerfile(content="FROM alpine\nRUN echo hi\n")
        issues = [i for i in result.issues if i.rule_id == "DL0015"]
        assert len(issues) == 1
        assert issues[0].severity == Severity.ERROR

    def test_has_user(self):
        content = "FROM alpine\nUSER appuser\n"
        result = lint_dockerfile(content=content)
        issues = [i for i in result.issues if i.rule_id == "DL0015"]
        assert len(issues) == 0


class TestShellFormEntrypoint:
    def test_shell_form(self):
        content = "FROM alpine\nENTRYPOINT python3 app.py\n"
        result = lint_dockerfile(content=content)
        issues = [i for i in result.issues if i.rule_id == "DL0013"]
        assert len(issues) == 1

    def test_exec_form(self):
        content = 'FROM alpine\nENTRYPOINT ["python3", "app.py"]\n'
        result = lint_dockerfile(content=content)
        issues = [i for i in result.issues if i.rule_id == "DL0013"]
        assert len(issues) == 0


class TestLintScore:
    def test_perfect_score(self):
        content = """FROM python:3.12-slim@sha256:abc
RUN adduser --disabled-password appuser && apt-get update && apt-get install --no-install-recommends -y curl=7.88 && rm -rf /var/lib/apt/lists/*
USER appuser
WORKDIR /app
COPY . /app
EXPOSE 8080
HEALTHCHECK --interval=30s CMD curl -f http://localhost:8080/ || exit 1
ENTRYPOINT ["python3", "app.py"]
CMD ["--port", "8080"]
"""
        result = lint_dockerfile(content=content)
        assert result.score >= 70  # May still have info-level issues

    def test_bad_score(self):
        content = "FROM ubuntu\nRUN apt-get install python3\nRUN sudo curl something\n"
        result = lint_dockerfile(content=content)
        assert result.score < 70


class TestSeverityFilter:
    def test_error_only(self):
        content = "FROM ubuntu\nRUN sudo apt-get update\nCOPY . /app\n"
        result = lint_dockerfile(content=content, severity_threshold=Severity.ERROR)
        for issue in result.issues:
            assert issue.severity == Severity.ERROR

    def test_specific_rules(self):
        content = "FROM ubuntu\nRUN sudo apt-get update\nCOPY . /app\n"
        result = lint_dockerfile(content=content, rules=["DL0004"])
        assert all(i.rule_id == "DL0004" for i in result.issues)
