.PHONY: format format-check

format:
	uv run isort .
	uv run black .

format-check:
	uv run isort --check-only .
	uv run black --check .
