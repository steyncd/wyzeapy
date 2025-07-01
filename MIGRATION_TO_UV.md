# Migration from Poetry to uv

This document summarizes the migration from Poetry to uv for the wyzeapy project.

## Changes Made

### 1. pyproject.toml Updates
- Replaced `[tool.poetry]` section with `[project]` section following PEP 621 standards
- Updated author format from string to structured format
- Changed license format to use `{ text = "GPL-3.0-only" }`
- Moved dependencies from `[tool.poetry.dependencies]` to `[project.dependencies]`
- Converted Poetry version constraints (^) to standard version constraints (>=)
- Moved dev dependencies to `[project.optional-dependencies]` and `[tool.uv]`
- Updated build system from poetry-core to hatchling

### 2. Lock File Changes
- Removed `poetry.lock` (backed up as `poetry.lock.backup`)
- Created new `uv.lock` file with resolved dependencies

### 3. Script Updates
- Updated `scripts/create_pre_release.sh` to use Python script for version bumping instead of `poetry version`
- Replaced `poetry version -s` with custom version extraction

### 4. Virtual Environment
- uv automatically created `.venv` directory (already in .gitignore)
- All dependencies installed and working correctly

## Key Differences Between Poetry and uv

### Dependency Management
- **Poetry**: Used `^` for version constraints (e.g., `^3.11.12`)
- **uv**: Uses standard version constraints (e.g., `>=3.11.12`)

### Project Structure
- **Poetry**: Used `[tool.poetry]` section in pyproject.toml
- **uv**: Uses standard `[project]` section following PEP 621

### Commands
- **Poetry**: `poetry install`, `poetry run`, `poetry version`
- **uv**: `uv sync`, `uv run`, custom version management

### Lock Files
- **Poetry**: `poetry.lock`
- **uv**: `uv.lock`

## Common uv Commands

```bash
# Install dependencies
uv sync

# Run commands in the virtual environment
uv run python script.py

# Add a new dependency
uv add package-name

# Add a development dependency
uv add --dev package-name

# Remove a dependency
uv remove package-name

# Update dependencies
uv lock --upgrade

# Build the package
uv build
```

## Backup Files Created
- `pyproject.toml.backup` - Original Poetry configuration
- `poetry.lock.backup` - Original Poetry lock file

## Verification
The migration has been tested and verified:
- ✅ Package imports successfully
- ✅ Development dependencies are accessible
- ✅ All dependencies resolved correctly
- ✅ Virtual environment created and working

## Next Steps
1. Update any CI/CD pipelines to use uv instead of Poetry
2. Update documentation to reference uv commands
3. Remove backup files once confident in the migration
4. Consider adding uv installation to development setup instructions