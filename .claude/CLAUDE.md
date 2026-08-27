# JobEdge — Project Steering

## Project

JobEdge is an autonomous job search intelligence agent. A scheduled loop
fetches live listings from multiple sources, scores them against TWO resume
profiles, surfaces skill gaps per track, verifies its own output, and
publishes a Streamlit dashboard.

## Tracks (two resumes, one pipeline)

- **Sales**: B2B Sales Executive, preferably IT/HRIS/SaaS or other
  product-based companies.
- **HR/Admin**: HR Generalist / HR Coordinator / Admin roles.

Every listing is scored against BOTH profiles; the higher score decides its
`best_track`, but both scores (and both reasons) are always stored.

## Location

Multi-region, not single-city. Config holds a list of target locations, e.g.
North York/GTA (ON), plus other cities/provinces in Alberta and Quebec. Every
location is config-driven, never hardcoded, and a listing's matched location
is stored alongside it.

## Language

Quebec listings may be in French. The Scorer must match French equivalents of
key titles/skills for that profile (e.g. "ventes B2B", "ressources humaines",
"adjoint administratif"), not just English keywords, or QC coverage will
silently under-report.

## Sources (each its own Fetcher module behind one shared interface)

- **Job Bank** (jobbank.gc.ca) — Government of Canada job board, has an open
  search/XML feed. Highest-reliability, lowest-risk source; treat as
  first-class, not an afterthought.
- **Company career pages** (direct scraping, always allowed and
  highest-signal) — for companies in the North York region.
- **Eluta.ca** (aggregator, tolerant of light scraping).
- **Jobillico** (bilingual, strong Quebec coverage).
- **Talent.com** (Canadian aggregator, decent national coverage).
- **Indeed** public search results, logged out only, slow rate.
- **LinkedIn** public job search pages, logged out only, slow rate, never an
  authenticated session.
- **Monster.ca / ZipRecruiter** (secondary, same caution as Indeed).

Fetchers must be independently swappable/disable-able — if one source starts
returning zero results or errors, the Verifier must flag it as "likely
blocked," never silently record it as "no jobs today."

## Architecture (do not deviate without telling me)

```
Trigger (scheduled) -> Orchestrator -> Fetchers (per source, run in sequence
with delay) -> Scorer (per profile) -> GapAnalyzer (per profile) -> Verifier
-> Storage -> Dashboard (read-only)
```

The Orchestrator reads state and delegates; it never fetches or scores
directly.

## Hard rules

1. Python 3.11+. Standard library first. `requests` + a parser (bs4 or
   similar) are expected for scraping — justify anything beyond that before
   adding it.
2. ALL storage access goes through a single storage module with a thin
   interface. No other module imports `sqlite3` directly.
3. Never hardcode role, city, keywords, or either skills profile. Everything
   profile/location-specific lives in `config.yaml` under a `profiles:` list.
4. No secrets in code. Environment variables only, loaded in one place.
5. Every agent run (including each individual Fetcher) writes a row to
   `cycle_log`: source/agent, when, records touched, pass/fail, retry reason.
6. Fail loudly. No bare `except: pass`. A blocked/broken source must surface,
   not disappear.
7. Respect scraping etiquette: delay between requests, no logged-in LinkedIn
   or Indeed session ever, respect `robots.txt` where present.
8. Type hints on every function signature. Docstrings only where intent isn't
   obvious from the name.
9. Keep files under ~150 lines. Split before that becomes a problem.

## Network & Sources (added once real fetchers start talking to the internet)

10. Every external source lives behind a `Source` class with a uniform
    interface (`jobedge/sources/base.py`). The Fetcher never contains
    source-specific parsing; adding a source must never require editing the
    Fetcher.
11. Every Source returns a list of normalized dicts with EXACTLY these keys:
    `source, external_id, title, company, location, url, description,
    posted_at, raw`. Missing values are `None`, never empty string, never
    `"N/A"`.
12. All network calls go through one helper (`jobedge/sources/http.py`) with
    a timeout (10s default), explicit retry (2 attempts, exponential
    backoff), and a real User-Agent header. No bare `requests.get` anywhere
    else in the codebase.
13. A source failing must NEVER kill the cycle. Catch per-source, log the
    failure to `cycle_log` with status "failed", continue to the next
    source. One dead job board must not stop the others.
14. Secrets come from environment variables via a `.env` file that is
    gitignored. Never a literal key in code, never a key in `config.yaml`.
    If a key is missing, that source skips itself with a clear log line —
    it does not crash the cycle.
15. Respect the source: rate limit to at most 1 request per second per
    source (on top of the general `request_delay_seconds` etiquette in rule
    7), set a real User-Agent, and honour any documented page limits.

## Style

Small, testable functions. Plain readable Python over clever Python. When
asked for one module, build one module — do not scaffold the whole app.
