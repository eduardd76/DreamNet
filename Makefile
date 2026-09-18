.PHONY: install test lint demo clean

install:
	python -m venv .venv
	.venv/bin/pip install -e '.[dev]'

test:
	.venv/bin/pytest

lint:
	.venv/bin/ruff check .

demo:
	.venv/bin/dreamnet demo --output artifacts/demo --train 84 --test 42 --candidates 800

clean:
	find . -type d -name __pycache__ -prune -exec rm -r {} +
	find . -type d -name .pytest_cache -prune -exec rm -r {} +
