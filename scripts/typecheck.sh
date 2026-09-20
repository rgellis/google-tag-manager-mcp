#!/bin/bash
# Lint, type check and test. Requires uv and Python 3.12+.
# No local toolchain? Run the same thing in Docker:
#   docker run --rm -v "$PWD":/app -w /app python:3.12-slim \
#     bash -c 'apt-get update -qq && apt-get install -y -qq libatomic1 \
#              && pip install -q uv && uv sync --extra dev && ./scripts/typecheck.sh'

set -e

echo "Running ruff formatter..."
uv run ruff format .

echo -e "\nRunning ruff linter..."
uv run ruff check . --fix

echo -e "\nRunning pyright type checker..."
uv run pyright

# Invoked as .venv/bin/python rather than `uv run`: constructing a FastMCP
# instance inside a coverage-instrumented module trips a type check in
# cryptography's Rust bindings. See the note in pyproject.toml.
echo -e "\nRunning tests with coverage..."
.venv/bin/python -m pytest -q --cov --cov-report=term-missing

echo -e "\nAll checks passed!"
