# AI.md

## What I used

- **Gemini**: primary code generator. I described each endpoint/module against the spec
  in the brief and Gemini wrote the implementation (FastAPI routes, data loading, the
  seat-calendar/held-day logic, metrics.py, tests). I also used it to help build the EDA
  notebook (`data/eda_data.ipynb`).
- **Claude**: acted as reviewer and orchestrator, not code generator. Concretely:
  - Wrote the exact prompts I fed to Gemini for each piece of the build.
  - Reviewed every chunk of Gemini-generated code against the metric definitions in
    Appendix P before I accepted it, including catching a real bug (spend was being
    computed row-by-row instead of off the same deduped day-set used for licensed/active
    counts, which was double-billing overlapping seat rows).
  - Helped me draft DATA.md, NOTES.md, README.md, and this file. I wrote these in my own
    words; Claude pushed back on anything that read as AI-generated boilerplate rather
    than just handing me polished prose.

## What I did myself, not AI-assisted

- The independent verification: I wrote a from-scratch Python script (no reuse of
  app code) that recomputes `/api/summary` and `/api/tools` straight from the raw CSVs for
  org=ORG05, and checked it against the live API's actual output field by field. This is
  how I actually confirmed the metrics logic was right, not just internally consistent.
- The overlap-pricing judgment call (when two overlapping seat rows for the same
  (user, tool) have different prices, I charge the higher one). This isn't specified
  in the brief, it's my own assumption, flagged as such in NOTES.md.
- Every number in the EDA notebook and every data quirk in DATA.md, I checked by hand
  against the real `data/` folder before writing it down. None of it is taken on faith
  from Gemini or Claude.

## Why this split

Gemini is fast at producing a first pass of boilerplate-heavy code (CSV parsing, FastAPI
routing). The part that actually matters for correctness, whether the metric definitions
in Appendix P are implemented right, including edge cases like blank `revoked_on` or
tool E's missing price, isn't something I was willing to accept on Gemini's word. That's
where the manual cross-check and the review pass with Claude came in.