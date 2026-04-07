# Repository Guidelines

## Project Structure & Module Organization
This repository is currently a minimal workspace with no committed source tree yet. Keep the top level clean and introduce standard folders as the project grows:

- `src/` for application code
- `tests/` for automated tests
- `assets/` for static files such as images or fixtures
- `docs/` for design notes and operational documentation

Use feature-oriented subdirectories when possible, for example `src/auth/` or `tests/auth/`.

## Build, Test, and Development Commands
No build tooling is configured yet. When tooling is added, document it here and keep commands reproducible from the repository root. Prefer a small, stable command set such as:

- `make setup` to install dependencies
- `make test` to run the full test suite
- `make lint` to run formatting and lint checks
- `make dev` to start the local development environment

If you do not use `make`, provide equivalent package-manager commands in the project `README`.

## Coding Style & Naming Conventions
Use consistent formatting and automate it early. Default conventions for new code:

- 2 spaces for YAML/JSON/Markdown, 4 spaces for Python, project-default indentation for other languages
- `snake_case` for Python files, `kebab-case` for Markdown and asset filenames
- Descriptive module names grouped by feature, not by generic utility buckets

Add formatter and linter configuration before the codebase grows. Examples: Prettier, ESLint, Ruff, or Black.

## Testing Guidelines
Place tests under `tests/` and mirror the source layout where practical. Name test files after the unit under test, such as `tests/auth/test_login.py` or `tests/auth/login.test.ts`.

Aim for meaningful coverage on core paths and regression tests for every bug fix. Keep tests fast, deterministic, and runnable in one command from the repository root.

## Commit & Pull Request Guidelines
Git history is not initialized here yet, so establish conventions from the start:

- Write commit subjects in the imperative mood, for example `Add login form validation`
- Keep commits focused and avoid mixing refactors with behavior changes
- In pull requests, include a short summary, test evidence, and linked issue references when applicable

Add screenshots or sample output for UI or CLI changes. Call out breaking changes and required config updates clearly.

## Configuration & Security
Do not commit secrets, local environment files, or generated credentials. Keep sample configuration in tracked templates such as `.env.example`, and document required environment variables in `README.md`.
