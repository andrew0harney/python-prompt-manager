# Contributing to Python Prompt Manager

Thank you for your interest in contributing! This guide will help you get started.

## Development Setup

1. **Fork and clone the repository**
   ```bash
   git clone https://github.com/yourusername/python-prompt-manager.git
   cd python-prompt-manager
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install development dependencies**
   ```bash
   make install-dev
   # or manually:
   pip install -r requirements-dev.txt
   pip install -e .
   ```

4. **Set up pre-commit hooks**
   ```bash
   pre-commit install
   ```

## Development Workflow

### Running Tests
```bash
make test           # Run tests
make test-cov       # Run tests with coverage report
```

### Code Quality
```bash
make lint           # Check code style
make format         # Auto-format code
make type-check     # Run type checking
```

### Building Documentation
```bash
make docs           # Build Sphinx documentation
```

## Coding Standards

- Use Black for code formatting (88 character line length)
- Use isort for import sorting
- Add type hints to all new code
- Write docstrings for all public functions and classes
- Maintain test coverage above 80%

## Pull Request Process

1. Create a feature branch from `main`
2. Make your changes following the coding standards
3. Add tests for new functionality
4. Update documentation as needed
5. Run `make lint test` to ensure everything passes
6. Submit a pull request with a clear description

## Testing

- Write tests for all new features
- Use pytest for testing
- Mock external dependencies (OpenAI API, file system, etc.)
- Test both success and error cases

Example test:
```python
def test_prompt_manager_get():
    config = {"prompts": {"test": {"source": "local", "path": "test.txt"}}}
    pm = PromptManager(config)
    
    with mock.patch("builtins.open", mock.mock_open(read_data="Hello {name}")):
        result = pm.get("test", variables={"name": "World"})
        assert result == "Hello World"
```

## Reporting Issues

- Use GitHub Issues for bug reports and feature requests
- Include Python version and package version
- Provide minimal reproducible examples
- Be respectful and constructive

## Questions?

Feel free to open a discussion or reach out to the maintainers.