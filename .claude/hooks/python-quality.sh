#!/usr/bin/env bash
# PostToolUse hook: format-check, lint and type-check a Python file after Claude edits it.
# Exits 2 with the report on stderr so Claude fixes the issues in the same turn.
# Non-mutating on purpose: rewriting the file under Claude would invalidate its read.
set -u

if ! command -v jq >/dev/null 2>&1; then
  echo "python-quality hook skipped: jq is not installed (brew install jq / apt install jq)." >&2
  exit 0
fi

payload=$(cat)
file_path=$(printf '%s' "$payload" | jq -r '.tool_input.file_path // ""' 2>/dev/null)

[[ "$file_path" == *.py && -f "$file_path" ]] || exit 0

repo_root=$(git -C "$(dirname "$file_path")" rev-parse --show-toplevel 2>/dev/null)
cd "${repo_root:-${CLAUDE_PROJECT_DIR:-.}}" || exit 0

rc=0
format_output=$(uv run --quiet ruff format --diff "$file_path" 2>&1) || rc=2
lint_output=$(uv run --quiet ruff check "$file_path" 2>&1) || rc=2
mypy_output=$(uv run --quiet mypy "$file_path" 2>&1) || rc=2

if (( rc != 0 )); then
  {
    echo "Python quality checks failed for $file_path"
    echo "--- ruff format --diff (apply this yourself) ---"
    echo "$format_output"
    echo "--- ruff check ---"
    echo "$lint_output"
    echo "--- mypy ---"
    echo "$mypy_output"
  } >&2
  exit 2
fi
exit 0
