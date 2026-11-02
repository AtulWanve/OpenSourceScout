# GitHub Configuration & Workflows

## Inputs
- Project test suite in `../tests/`
- Python scripts in `../scripts/`

## Process
Automation workflows executed by GitHub Actions:
- `ci.yml`: Runs `pytest` with coverage on Python 3.11/3.12, Ruff linting, and Bandit security scanning.
- `codeql.yml`: Runs GitHub CodeQL static analysis for Python vulnerabilities.
- `task-list-checker.yml`: Blocks PR merges if markdown checklist items are still incomplete.

## Outputs
- CI build status and GitHub security scanning alerts.
