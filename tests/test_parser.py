"""Unit tests for DockerLens parser."""
import pytest
from dockerlens.parser import parse_dockerfile, Instruction


class TestParseDockerfile:
    def test_empty_dockerfile(self):
        result = parse_dockerfile("")
        assert result.total_lines == 0
        assert result.instructions == []

    def test_from_instruction(self):
        result = parse_dockerfile("FROM python:3.12\n")
        assert len(result.instructions) == 1
        assert result.instructions[0].command == "FROM"
        assert result.instructions[0].arguments == "python:3.12"
        assert result.from_images == ["python:3.12"]

    def test_from_with_stage(self):
        result = parse_dockerfile("FROM python:3.12 AS builder\n")
        assert result.from_images == ["python:3.12"]
        assert result.stages == ["builder"]

    def test_multistage(self):
        content = "FROM golang:1.22 AS builder\nFROM alpine:3.19\n"
        result = parse_dockerfile(content)
        assert len(result.from_images) == 2
        assert result.stages == ["builder"]

    def test_comment(self):
        result = parse_dockerfile("# This is a comment\nFROM alpine\n")
        comments = [i for i in result.instructions if i.is_comment]
        assert len(comments) == 1
        assert comments[0].arguments == "This is a comment"

    def test_blank_lines(self):
        result = parse_dockerfile("FROM alpine\n\nRUN echo hi\n")
        blanks = [i for i in result.instructions if i.is_blank]
        assert len(blanks) == 1

    def test_run_command(self):
        result = parse_dockerfile("RUN apt-get update && apt-get install -y curl\n")
        run = [i for i in result.instructions if i.command == "RUN"]
        assert len(run) == 1
        assert "apt-get update" in run[0].arguments

    def test_all_commands(self):
        content = """FROM alpine
LABEL version="1.0"
RUN echo hi
CMD ["echo"]
EXPOSE 8080
ENV FOO=bar
COPY . /app
ADD file.tar.gz /opt
ENTRYPOINT ["/app"]
VOLUME /data
USER appuser
WORKDIR /app
ARG VERSION=1.0
"""
        result = parse_dockerfile(content)
        commands = [i.command for i in result.instructions if not i.is_blank and not i.is_comment]
        assert "FROM" in commands
        assert "LABEL" in commands
        assert "RUN" in commands
        assert "CMD" in commands
        assert "EXPOSE" in commands
        assert "ENV" in commands
        assert "COPY" in commands
        assert "ADD" in commands
        assert "ENTRYPOINT" in commands
        assert "VOLUME" in commands
        assert "USER" in commands
        assert "WORKDIR" in commands
        assert "ARG" in commands
