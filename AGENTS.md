# Repository Guidelines

## Project Structure & Module Organization
- `agents/` — Agent logic: `deep_research`, `synthesizer`, and `orchestrator/workflow.py` (LangGraph flow).
- `backend/` — FastAPI app (`api/`), services (`services/` for cache/export/validation), and Pydantic models (`models/`).
- `config/settings.py` — Central configuration via pydantic-settings reading `.env`.
- `frontend/` — Static UI (`index.html`, `script.js`, `styles.css`).
- `tests/` — Pytest suite (see `tests/test_system.py`).
- `data/` (runtime cache/exports) and `logs/` (ignored by git).

## Build, Test, and Development Commands
- Install deps: `pip install -r requirements.txt`
- Configure env: `cp .env.example .env` and set `OPENAI_API_KEY`.
- Run API (dev): `python run.py`
  - Alt: `uvicorn backend.api.main:app --reload --host 0.0.0.0 --port 8000`
- Open UI: open `frontend/index.html` in a browser.
- Run tests: `pytest -q` (e.g., `pytest tests/test_system.py::TestSystemIntegration -q`).

## Coding Style & Naming Conventions
- Python: PEP 8, 4‑space indent, type hints, concise docstrings for public functions.
- Names: modules/functions `snake_case`; classes `CamelCase`; constants `UPPER_SNAKE_CASE`.
- Models: use Pydantic `BaseModel` in `backend/models`; keep API schemas there.
- JS (frontend): `camelCase` for vars/functions; keep DOM ids in sync with `index.html` and endpoints in `script.js`.

## Testing Guidelines
- Use Pytest; place tests in `tests/` named `test_*.py`.
- Mock external calls (OpenAI, HTTP) in unit/integration tests; avoid real network I/O.
- Cover new code paths and failure cases (validators, cache, exporters, workflow decisions).
- Quick run examples: `pytest -q`, or `pytest -k workflow -q`.

## Commit & Pull Request Guidelines
- Commits: prefer small, focused changes using Conventional Commits (e.g., `feat:`, `fix:`, `refactor:`, `test:`, `docs:`).
- PRs must include: clear description, rationale, testing steps, and linked issues. Add screenshots/GIFs for UI changes.
- Ensure: all tests pass, no secrets committed, docs updated if commands/env/config changed.

## Security & Configuration Tips
- Never commit secrets. `.env` is git‑ignored; use `.env.example` as template.
- Settings live in `config/settings.py`; environment is loaded via pydantic-settings.
- Runtime artifacts are written to `data/` and `logs/`. Do not rely on these for tests; use mocks/fixtures.

## Agent-Specific Instructions
- To add an agent: create `agents/<agent_name>/agent.py` with `async def execute(state)`; extend `agents/state.py` to include its state; wire it into `agents/orchestrator/workflow.py` via nodes/edges and update validation/flow as needed.

