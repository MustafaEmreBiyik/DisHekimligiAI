# DentAI

Primary project documentation now lives in [`mdfiles/README.md`](mdfiles/README.md).

Repository layout after cleanup:

- `requirements/` for Python dependency manifests
- `config/` for preserved tool configuration files
- `tests/` for automated and manual test assets
- `scripts/` for setup, diagnostics, and one-off utilities
- `db/runtime/` for the local SQLite database file

Common commands:

- Install backend dependencies: `pip install -r requirements/requirements-api.txt`
- Install general Python dependencies: `pip install -r requirements/requirements.txt`
- Run tests: `python -m pytest -q`
- Verify backend setup: `python scripts/setup/verify_setup.py`
