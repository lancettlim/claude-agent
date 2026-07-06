.PHONY: setup lint test dbt-build validate check

setup:
	uv sync

lint:
	uv run ruff check .
	uv run ruff format --check .

test:
	uv run pytest

dbt-build:
	cd dbt && uv run dbt build

validate:
	uv run python -m pipelines.cli validate

check: lint test validate
