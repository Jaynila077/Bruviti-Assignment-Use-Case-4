# Bruviti-Assignment-Use-Case-4

A FastAPI service that answers adoption and spend questions (licensed users, active users,
engagement %, spend, idle spend) for any date window and any organisation unit, built from
five raw CSV exports.

## Install and run

Requires Python 3.10+.

One command (Mac/Linux), run from the repo root:

```bash
python3 -m venv venv && . venv/bin/activate && pip install -r requirements.txt && uvicorn app.main:app --host 0.0.0.0 --port 8000
```

On Windows (PowerShell):

```powershell
python -m venv venv; venv\Scripts\activate; pip install -r requirements.txt; uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Or step by step:

```bash
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

The service is ready once the terminal shows `Application startup complete.` and
`GET http://localhost:8000/health` returns `{"status": "ok"}`.

The service reads CSVs from the `data/` folder at the repository root at startup. To run
against a different export, replace the contents of `data/` (same five filenames, same
columns) before starting the service. Nothing else needs to change.

## Use it

- **UI**: open `http://localhost:8000/` in a browser, pick a from/to date and optionally an
  org unit, click "Run Report".
- **API directly**:
  ```bash
  curl "http://localhost:8000/api/summary?from=2026-07-01&to=2026-07-31"
  curl "http://localhost:8000/api/tools?from=2026-07-01&to=2026-07-31&org=ORG05"
  ```
  `org` is optional (omit it for whole-company numbers). An unknown `org` returns `404`, an
  invalid or out-of-order date range returns `400`.

## Run the tests

```bash
pytest tests/ -v
```

Tests run fully offline against in-memory fixtures and temp folders (no dependency on the
real `data/` folder or network access), and include the worked example from Appendix P as an
exact-match regression test.

## Project layout

```
app/
  main.py           FastAPI app, routes, startup, error handling
  data_loader.py    CSV -> typed records (bad rows skipped with a warning)
  org_tree.py       org-unit subtree resolution
  seat_calendar.py  per-(user, tool) held-day interval math
  metrics.py        the metric definitions from Appendix P
  templates/        the single UI page
data/               the five input CSVs (swapped at grading time)
                    and eda_data.ipynb, the exploration behind DATA.md
tests/              pytest suite, one file per module
```


See `DATA.md` for data issues found and how they're handled, `NOTES.md` for scope decisions,
and `AI.md` for AI tool usage.
