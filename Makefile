.PHONY: setup lint test dbt-build validate check dashboard

setup:
	uv sync
	uv run playwright install --with-deps chromium

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

dashboard:
	uv run streamlit run dashboard/app.py
