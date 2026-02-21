"""Tasks: uv run inv --list. e.g. uv run inv lint, uv run inv test"""
from invoke import task


@task
def lint(c):
    """Run ruff check --fix"""
    c.run("uv run ruff check --fix .")


@task
def test(c):
    """Run pytest"""
    c.run("uv run pytest tests/ -v")
