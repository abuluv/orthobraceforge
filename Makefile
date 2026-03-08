.PHONY: test lint coverage install install-dev clean

install:
	pip install -r requirements.txt

install-dev:
	pip install -r requirements.txt
	pip install -r requirements-dev.txt

test:
	python -m pytest -q

lint:
	ruff check .

lint-fix:
	ruff check --fix .

coverage:
	python -m pytest --cov=. --cov-report=term-missing --cov-fail-under=70

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
	rm -rf .pytest_cache htmlcov .coverage
