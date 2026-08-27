# JobEdge — Steering File & Prompt Sequence for Claude Code

Adapted from your professor's EdgeDash architecture (Lec 1) for a dual-resume,
multi-source job search agent targeting North York, ON.

Paste PROMPT 1 into Claude Code first. Nothing else should be built until it's in place.
One prompt at a time — review each diff before moving to the next.

---

## PROMPT 1 — Steering file

```text
Create a Claude Code steering/context file at .claude/CLAUDE.md (or CONTEXT.md,
whichever this project convention uses) that applies to every interaction. Capture:

PROJECT: JobEdge — an autonomous job search intelligence agent. A scheduled loop
that fetches live listings from multiple sources, scores them against TWO resume
profiles, surfaces skill gaps per track, verifies its own output, and publishes a
Streamlit dashboard.

TRACKS (two resumes, one pipeline):
- Sales: B2B Sales Executive, preferably IT/HRIS/SaaS or other product-based companies
- HR/Admin: HR Generalist / HR Coordinator / Admin roles
Every listing is scored against BOTH profiles; the higher score decides its track,
but both scores are stored.

LOCATION: multi-region, not single-city. Config holds a list of target locations,
e.g. North York/GTA (ON), and other cities/provinces in Alberta and Quebec. Every
location is config-driven, never hardcoded, and a listing's matched location is
stored alongside it.

LANGUAGE: Quebec listings may be in French. The Scorer must match French
equivalents of key titles/skills for that profile (e.g. "ventes B2B", "ressources
humaines", "adjoint administratif"), not just English keywords, or QC coverage
will silently under-report.

SOURCES (each its own Fetcher module behind one shared interface):
- Job Bank (jobbank.gc.ca) — Government of Canada job board, has an open
  search/XML feed. Highest-reliability, lowest-risk source; treat as first-class,
  not an afterthought.
- Company career pages (direct scraping, always allowed and highest-signal)
- Eluta.ca (aggregator, tolerant of light scraping)
- Jobillico (bilingual, strong Quebec coverage)
- Talent.com (Canadian aggregator, decent national coverage)
- Indeed public search results, logged out only, slow rate
- LinkedIn public job search pages, logged out only, slow rate, never an
  authenticated session
- Monster.ca / ZipRecruiter (secondary, same caution as Indeed)
Fetchers must be independently swappable/disable-able — if one source starts
returning zero results or errors, the Verifier must flag it as "likely blocked,"
never silently record it as "no jobs today."

ARCHITECTURE (do not deviate without telling me):
Trigger (scheduled) -> Orchestrator -> Fetchers (per source, run in sequence with
delay) -> Scorer (per profile) -> GapAnalyzer (per profile) -> Verifier -> Storage
-> Dashboard (read-only).
The Orchestrator reads state and delegates; it never fetches or scores directly.

HARD RULES:
1. Python 3.11+. Standard library first. requests + a parser (bs4 or similar) are
   expected for scraping — justify anything beyond that before adding it.
2. ALL storage access goes through a single storage module with a thin interface.
   No other module imports sqlite3 directly.
3. Never hardcode role, city, keywords, or either skills profile. Everything
   profile/location-specific lives in config.yaml under a `profiles:` list.
4. No secrets in code. Environment variables only, loaded in one place.
5. Every agent run (including each individual Fetcher) writes a row to cycle_log:
   source/agent, when, records touched, pass/fail, retry reason.
6. Fail loudly. No bare `except: pass`. A blocked/broken source must surface, not
   disappear.
7. Respect scraping etiquette: delay between requests, no logged-in LinkedIn or
   Indeed session ever, respect robots.txt where present.
8. Type hints on every function signature. Docstrings only where intent isn't
   obvious from the name.
9. Keep files under ~150 lines. Split before that becomes a problem.

STYLE: Small, testable functions. Plain readable Python over clever Python.
When I ask for one module, build one module — do not scaffold the whole app.
```

**Check before moving on:** the file exists, and the two-profile / multi-source /
"flag blocked sources" rules are all in it clearly.

---

## PROMPT 2 — Config + storage layer

```text
Build two modules only. No agents, no fetchers, no loop yet.

1. jobedge/config.py
   - A dataclass `Profile`: name (str, e.g. "sales" or "hr"), target_titles
     (list[str]), keywords (list[str]), my_skills (list[str]),
     experience_years (int), resume_path (str).
   - A dataclass `Config`: profiles (list[Profile]), target_locations
     (list[dict] — e.g. {city, province}), db_path (str), min_fit_score (int),
     sources (list[str] — which fetchers are enabled), request_delay_seconds
     (float).
   - Each Profile also needs: keywords_fr (list[str], optional) for French
     equivalents used when scoring Quebec listings.
   - Load from config.yaml at repo root with sensible defaults where reasonable,
     fail clearly if config.yaml is missing or a profile is malformed.
   - Write an example config.yaml with two profiles filled in: a Sales profile
     (B2B Sales Executive, IT/HRIS/SaaS keywords, French equivalents) and an
     HR/Admin profile, with target_locations covering North York (ON), plus one
     Alberta city and one Quebec city as placeholders.

2. jobedge/storage.py
   - The ONLY module allowed to touch sqlite3.
   - init_db(path) creating tables:
       listings(id TEXT PRIMARY KEY, title, company, location, url, description,
                source, posted_at, fetched_at,
                sales_fit_score INTEGER NULL, sales_fit_reason TEXT NULL,
                hr_fit_score INTEGER NULL, hr_fit_reason TEXT NULL,
                best_track TEXT NULL)
       skill_gaps(profile TEXT, skill TEXT, frequency INTEGER, last_seen TEXT,
                  PRIMARY KEY (profile, skill))
       cycle_log(id INTEGER PRIMARY KEY AUTOINCREMENT, agent TEXT, started_at,
                 finished_at, records_touched INTEGER, status TEXT, notes TEXT)
   - Functions: upsert_listings(rows) -> int (count of NEW rows only);
     count_unscored(); last_fetch_time(source); log_cycle(...);
     get_listings(profile, limit, min_score).
   - INSERT OR IGNORE on primary key for dedup. Listing id = stable hash of
     source + url.

Type hints throughout. Show me the files, then one line on how to init the db.
```

---

## PROMPT 3 — Orchestrator skeleton + mock Fetchers

```text
Now the loop skeleton, still no real network calls.

1. jobedge/agents/base.py — Agent protocol/ABC (name, run(config, storage) ->
   AgentResult) and AgentResult dataclass (agent, status "ok"|"failed"|"blocked",
   records_touched, notes).

2. jobedge/agents/mock_fetchers.py — one MockFetcher per source (company_pages,
   eluta, indeed, linkedin). Each returns realistic fake listings tagged with
   real B2B sales / HR skill keywords so scoring later has something to bite on.
   4 listings per source must be identical across runs (stable id) to prove dedup.

3. jobedge/orchestrator.py — run_cycle(config):
   a. init db
   b. read state per source: last_fetch_time, count_unscored per profile
   c. print the plan it decided and why
   d. run each enabled fetcher with request_delay_seconds respected (even mocked)
   e. log every agent run to cycle_log
   f. print a cycle summary: per source, per profile
   Registry pattern so real fetchers swap in by changing one line each.
   Scorer and GapAnalyzer: registered as clearly marked "not implemented yet."

4. run_cycle.py at repo root as entry point.

Console output must be genuinely readable — I'll be screen-recording this.
```

Run it twice — first run should show all listings as new, second run should show
only the 4×(sources) that were deliberately duplicated as new=0.

---

## Prompts 4+ (once P1–P3 are solid)

- P4: Real Fetchers, one at a time — start with **Job Bank** (official feed,
  safest), then **company career pages**, then Eluta/Jobillico/Talent.com, then
  Indeed/LinkedIn public search last, with delay and a "blocked" detection path
  in the Verifier.
- P5: Scorer — runs each listing against both profiles, writes both scores,
  sets best_track.
- P6: GapAnalyzer — per profile, ranks missing skills by how many listings they'd
  unlock (matches your Skill Gap Report panel).
- P7: Verifier — rejects degenerate scoring (e.g. everything >90, or a source
  silently returning 0), forces a rescore/refetch, logs the retry.
- P8: Dashboard — Streamlit, read-only from storage, two views (Sales feed / HR
  feed) matching your Opportunity Feed panel: fit score, role, company, and the
  "why" reason string.

Same rule as the original class: one prompt at a time, read every diff, and if
something's wrong describe the symptom and let Claude Code fix the module rather
than hand-patching it.
