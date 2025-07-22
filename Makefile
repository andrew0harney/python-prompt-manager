# Makefile for python-prompt-manager development

.PHONY: help install install-dev test test-cov lint format type-check clean build upload docs

help:
	@echo "Available commands:"
	@echo "  make install      Install package in development mode"
	@echo "  make install-dev  Install package with dev dependencies"
	@echo "  make test         Run tests"
	@echo "  make test-cov     Run tests with coverage"
	@echo "  make lint         Run linting (flake8)"
	@echo "  make format       Format code (black + isort)"
	@echo "  make type-check   Run type checking (mypy)"
	@echo "  make clean        Clean build artifacts"
	@echo "  make build        Build distribution packages"
	@echo "  make upload       Upload to PyPI (requires credentials)"
	@echo "  make docs         Build documentation"

install:
	pip install -e .

install-dev:
	pip install -e ".[dev]"
	pre-commit install

test:
	pytest tests/

test-cov:
	pytest tests/ --cov=prompt_manager --cov-report=html --cov-report=term

lint:
	flake8 src/ tests/
	black --check src/ tests/
	isort --check-only src/ tests/

format:
	black src/ tests/
	isort src/ tests/

type-check:
	mypy src/

clean:
	rm -rf build/ dist/ *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf .coverage htmlcov/ .pytest_cache/ .mypy_cache/

build: clean
	python -m build

upload: build
	python -m twine upload dist/*

upload-test: build
	python -m twine upload --repository testpypi dist/*

docs:
	cd docs && make html