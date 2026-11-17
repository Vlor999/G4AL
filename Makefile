########################################################################################################################
# Project installation
########################################################################################################################

.PHONY: install
install:
	uv sync
	uv run pre-commit install

########################################################################################################################
# Run
########################################################################################################################

.PHONY: run
run:
	uv run python main.py

########################################################################################################################
# Quality checks
########################################################################################################################

.PHONY: format-check format-fix lint-check lint-fix type-check dead-code test check

format-check:
	uv run ruff format --check .

format-fix:
	uv run ruff format .

lint-check:
	uv run ruff check .

lint-fix:
	uv run ruff check . --fix

type-check:
	uv run mypy

dead-code:
	uv run vulture

test:
	uv run pytest --cov --cov-report=term-missing --cov-report=xml

check: format-check lint-check type-check dead-code test
