# AGENTS.md - LineCook Development Guide

## Build/Test Commands
- `uv run python main.py` - Run CLI mode (process files in test_inputs/)
- `uv run python main.py server` - Start FastAPI server  
- `just serve` - Start FastAPI server (alias)
- `just test` - Run API tests
- `uv sync` - Install/sync dependencies
- No formal test framework configured - relies on manual testing via test_inputs/

## Code Style & Conventions
- **Python version**: >=3.11 required
- **Dependency management**: Always use `uv run python` instead of direct python calls
- **Type hints**: Required for all function parameters and return values
- **Imports**: Group stdlib, third-party, then local imports with blank lines between
- **Error handling**: Use specific exception types, log errors with context
- **Naming**: snake_case for functions/variables, PascalCase for classes
- **Settings**: Use pydantic Settings class for configuration (see config.py)
- **Logging**: Use module-level loggers, structured logging with context
- **File structure**: Modular design - services/, api/, config.py separation
- **Constants**: Define in config.py as module-level variables (TARGET_SIZE, etc.)
- **Documentation**: Use docstrings with Args/Returns sections for all public functions