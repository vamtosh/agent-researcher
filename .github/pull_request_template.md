# Pull Request Template

## Summary
- What changed and why?
- Link issues (e.g., Closes #123).

## Changes
- 
- 

## How to Test
- Commands to run (backend):
  - `pip install -r requirements.txt`
  - `python run.py` or `uvicorn backend.api.main:app --reload`
- Commands to run (tests):
  - `pytest -q`
- Frontend:
  - Open `frontend/index.html` in a browser

## Screenshots (UI changes)
<!-- Add before/after screenshots or GIFs -->

## Checklist
- [ ] Tests added/updated for new behavior
- [ ] CI green (Python tests + lint, frontend lint)
- [ ] Docs updated (README/AGENTS.md) if commands/env/config changed
- [ ] No secrets committed (.env not included)

