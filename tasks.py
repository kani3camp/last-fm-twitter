"""Tasks: uv run inv --list. e.g. uv run inv lint, uv run inv test"""

from invoke import task


@task
def lint(c):
    """Run ruff format then ruff check --fix"""
    c.run("uv run ruff format .")
    c.run("uv run ruff check --fix .")


@task(pre=[lint])
def check(c):
    """Run lint then test"""
    c.run("uv run pytest tests/ -v")


@task
def test(c):
    """Run pytest"""
    c.run("uv run pytest tests/ -v")
