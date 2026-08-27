# Class 2 Prompts — "Build the Radar"
### Week 1 · Session 1.2 · EdgeDash · Proof of Ship, August Cohort

These are every prompt used in Class 2, in order. Paste them into **Kiro** one at a time,
in sequence — each one builds on the last.

## Before you start

1. Your Class 1 repo open in Kiro, with `.kiro/steering/edgedash.md` in place.
2. `python run_cycle.py` runs clean and reports **4 new** on a second run. If it doesn't,
   fix that first — everything today depends on dedup working.
3. `config.yaml` filled in with **your** real role, city, and skills. Not the example.
4. A terminal open in the repo.

**Still no paid anything.** Source 1 needs no signup at all. Source 2 (Apify) has a free
tier that covers far more than this month needs, and the class works fully without it.

## Three rules for using these prompts

**1. Read every diff before you accept it.** Same rule as last week and it matters more now,
because from today your code talks to the internet. Network code is where silent failure
lives.

**2. One prompt at a time.** Each one ends at a point where you should stop and run something.

**3. When a prompt gives you something wrong, describe the symptom, not your guess at the
cause.** There are copy-paste follow-ups at the bottom of this file.

---

## PROMPT C2-P1 — Amend the steering file

**What it does:** Adds the rules that only matter now that we're touching the network. Do
this before any fetching code exists, for the same reason we wrote steering before app code
last week.

```text
Update .kiro/steering/edgedash.md — add a NETWORK & SOURCES section to the
existing rules. Do not rewrite the rest of the file.

NETWORK & SOURCES:
9.  Every external source lives behind a Source class with a uniform interface.
    The Fetcher never contains source-specific parsing. Adding a source must
    never require editing the Fetcher.
10. Every Source returns a list of normalised dicts with EXACTLY these keys:
    source, external_id, title, company, location, url, description,
    posted_at, raw. Missing values are None, never empty string, never "N/A".
11. All network calls go through one helper with a timeout (10s default),
    explicit retry (2 attempts, exponential backoff), and a User-Agent header.
    No bare requests.get anywhere else in the codebase.
12. A source failing must NEVER kill the cycle. Catch per-source, log the
    failure to cycle_log with status "failed", continue to the next source.
    One dead job board must not stop the other sources.
13. Secrets come from environment variables via a .env file that is
    gitignored. Never a literal key in code, never a key in config.yaml.
    If a key is missing, that source skips itself with a clear log line —
    it does not crash the cycle.
14. Respect the source. Rate limit to at most 1 request per second per
    source, set a real User-Agent, and honour any documented page limits.

Then show me the diff of what you added.
```

**Check before moving on:** the file still contains all eight original rules, and the new
section is appended, not substituted. Rule 12 is the one that saves your Sunday.

---

## PROMPT C2-P2 — The Source interface + first real source

**What it does:** Builds the plug-in shape for sources, then the first one — a public API
that needs no key at all, so you get real listings on screen inside two minutes.

```text
Build the source layer. Two files only, no Fetcher changes yet.

1. edgedash/sources/base.py
   - `Source` ABC/protocol: `name: str`, and
     `fetch(config) -> list[dict]` returning normalised rows per steering
     rule 10.
   - A module-level `SOURCES: dict[str, type[Source]]` registry and a
     `register(cls)` decorator, so a new source is added by decorating a
     class and nothing else.
   - `edgedash/sources/http.py`: one `get_json(url, params=None, headers=None)`
     helper implementing steering rule 11 — 10s timeout, 2 retries with
     exponential backoff, real User-Agent, raises a clear custom
     `SourceError` on failure. This is the ONLY place in the project that
     performs an HTTP request.

2. edgedash/sources/arbeitnow.py
   - `ArbeitnowSource`, registered as "arbeitnow". Uses the free public
     Arbeitnow job board API — https://www.arbeitnow.com/api/job-board-api
     It needs NO API key and NO signup.
   - Fetch page 1, and keep paging only while results keep matching the
     config keywords, up to a hard cap of 5 pages.
   - Filter results against config.keywords and config.target_city — but if
     a filter would leave fewer than 5 results, relax the location filter
     first and log that you did. I would rather see remote/nearby roles than
     an empty database.
   - Map their fields onto our normalised keys. `external_id` must be their
     stable slug/id, NOT a hash yet, and NOT a row number.
   - Print how many raw results came back and how many survived filtering.

Add `requests` to requirements.txt if you use it. Show me both files, then
give me a one-line python -c command to fetch and print the first 3 results
without touching the database.
```

**Check before moving on:** run the one-liner it gives you. You should see three real job
titles from a real company, in your terminal, with no API key anywhere. If the count that
survived filtering is 0, your keywords are too narrow — widen them in `config.yaml`, don't
change the code.

---

## PROMPT C2-P3 — The real Fetcher

**What it does:** Replaces the mock with a Fetcher that walks every registered source,
survives one of them dying, and reports what actually happened.

```text
Now replace the mock Fetcher with the real one.

edgedash/agents/fetcher.py — a `Fetcher` implementing the existing Agent
protocol from Class 1. It must:

1. Read the enabled source names from config (add a `sources: list[str]`
   field to Config and config.yaml, defaulting to ["arbeitnow"]).
2. For each enabled source, in order:
   - instantiate it from the SOURCES registry
   - call fetch(config) inside its own try/except per steering rule 12
   - on failure: log the exception to cycle_log with status "failed" and
     the source name, print a clear one-line warning, and CONTINUE
   - on success: log status "ok" with the row count
3. Combine all rows from all sources, then compute the stable listing id
   as a hash of (source + url) — reuse the exact same id function
   storage.py already uses. Do not write a second id implementation.
4. Write via storage.upsert_listings and return an AgentResult whose notes
   read like: "arbeitnow: 47 rows (12 new) | apify: FAILED (timeout)".

Then update the agent registry so "fetcher" resolves to this Fetcher
instead of MockFetcher. Keep mock_fetcher.py on disk — do not delete it —
and add a config flag `use_mock_fetcher: false` that swaps it back in, so I
can develop offline without hitting the network.

Show me the diff. Tell me in one line what changed in the registry.
```

**Check before moving on:** the registry swap is **one line**. If Kiro had to edit the
Orchestrator to make this work, your Class 1 registry pattern wasn't actually decoupled —
say so and have it fixed, because Thursday's whole design rests on it.

**Now run it:**

```bash
python run_cycle.py
python run_cycle.py
```

**This is the moment of the class.** First run: real listings, all new. Second run: the same
listings found, **0–2 new**. Real dedup, on real data, from a real job board.

---

## PROMPT C2-P4 — Second source, with a secret

**What it does:** Adds Apify as a second source. This is where you learn the environment
variable pattern — the thing that stops you leaking a key into GitHub in week 4.

**Skip-safe:** if you don't want to sign up for Apify, skip this prompt. Rule 13 means the
source skips itself and everything else still works. You can do it later.

```text
Add a second source: Apify.

1. edgedash/sources/apify.py — `ApifySource`, registered as "apify".
   - Reads APIFY_TOKEN from the environment. Per steering rule 13: if the
     token is absent, log "apify: no APIFY_TOKEN, skipping" and return an
     empty list. Do NOT raise, do NOT crash the cycle.
   - Calls an Apify job-scraper actor's run-sync-get-dataset-items endpoint
     with config.target_role and config.target_city, via the existing
     get_json helper. Do not write a new HTTP call.
   - Maps the actor's output onto our normalised keys. Their field names
     will not match ours; that mapping is the entire job of this file.
   - Cap results at 100 per run so I cannot burn my free credits by
     accident.

2. Environment loading, in ONE place per steering rule 4:
   - Load a .env file at startup (python-dotenv is fine, tell me why you
     added it).
   - Add .env to .gitignore. Create a .env.example listing APIFY_TOKEN=
     with an empty value, and make sure .env.example IS committed.

3. Add "apify" to the sources list in config.yaml, commented out with a
   one-line note saying it needs APIFY_TOKEN in .env.

Show me .gitignore and confirm .env is in it before anything else.
```

**Check before moving on:** run `git status`. If `.env` appears in the untracked list,
`.gitignore` is wrong — fix it before you commit anything. This is the single most common
way people leak an API key.

---

## PROMPT C2-P5 — Cross-source dedup check (optional, do it on your own)

**What it does:** Two job boards will carry the same role at different URLs. Your
hash(source + url) treats them as different rows — correct for now, and worth measuring
before you decide whether to care.

```text
Add a read-only diagnostic: `python -m edgedash.diagnose`.

It must print, from the existing database only — no new writes, no schema
changes:
- total listings, and a count per source
- how many listings share an identical (title, company) pair across
  DIFFERENT sources — these are probable cross-source duplicates
- the 5 most recent listings with source, title, company
- any listing with a NULL or empty url, title, or company (data quality)

Read-only. Use the existing storage module — no direct sqlite3 per rule 2.
```

**What to do with the number it gives you:** if cross-source duplicates are under ~10% of
your total, leave it. Note it in your README as a known limitation and move on. Don't build
fuzzy title matching in week 1 — that's a rabbit hole and it's not what you're being graded
on.

---

## Your assignment

**Due Sunday:**
- [ ] Real Fetcher live, mock retired behind the `use_mock_fetcher` flag
- [ ] **50+ genuine live listings** in your database — real data, I check
- [ ] At least one source working; two if you did the Apify prompt
- [ ] `python run_cycle.py` twice in a row shows dedup holding on real data
- [ ] One source failing does not kill your cycle — **prove it** (see below)
- [ ] `.env` gitignored, `.env.example` committed
- [ ] 2–3 minute walkthrough video: cycle running, database growing, dedup on run 2
- [ ] Submit GitHub repo link + video

**Prove rule 12 works.** Break a source deliberately — change its URL to something
invalid — then run the cycle. The correct behaviour is a logged failure, a warning line,
and the other sources still writing. Show that in your video. It's the most valuable ten
seconds of footage you can submit, because it's the thing that will actually happen to you
in week 4.

**Badge unlocked:** The Tracker

---

## Fixing common problems

Paste these as follow-ups. Describe the symptom, not your guess at the cause.

**Zero results survive filtering:**
```text
The arbeitnow source fetches raw results but 0 survive filtering. Print the
first 3 raw results in full so I can see the actual field values, then show
me exactly which config field each filter compares against. I suspect my
keywords or city don't match their data format. Do not loosen the filter
until we have looked at the raw data.
```

**One dead source kills the whole cycle (violates rule 12):**
```text
When one source raises, the entire cycle dies instead of continuing. Steering
rule 12 says catch per-source, log status "failed" to cycle_log, and continue
to the next source. Show me the try/except boundary in fetcher.py and fix it
so a raising source is isolated. Then prove it by simulating a failure.
```

**Dedup broke when real data arrived:**
```text
Running run_cycle.py twice on real data reports all listings as new both
times, when the second run should report near zero. Show me the id function
in storage.py and where fetcher.py calls it. The id must be a stable hash of
source + url, computed in ONE place. I suspect the fetcher is building ids
differently from storage, or the url has a changing query parameter — check
both and tell me which it was.
```

**A source-specific `requests.get` leaked in (violates rule 11):**
```text
Check every file for HTTP calls outside edgedash/sources/http.py. Steering
rule 11 says get_json is the only place that performs a request. Move any
stray calls behind it and update the callers, so timeout, retry, and
User-Agent apply everywhere.
```

**`.env` is showing up in git status:**
```text
.env appears in git status, which means it is not ignored and I am about to
leak a token. Show me .gitignore, fix it so .env is ignored, and confirm
.env.example is still tracked. Then tell me the command to check whether
.env was ever committed in a previous commit.
```

**Kiro edited the Orchestrator to swap the Fetcher:**
```text
Swapping the mock for the real Fetcher should be a one-line registry change,
but the Orchestrator was modified too. That means the registry isn't actually
decoupling agents from the loop. Show me how the Orchestrator resolves an
agent, and refactor so registering a different class is the ONLY change
needed.
```

**Rate limited / 429 from a source:**
```text
A source is returning 429. Steering rule 14 says at most 1 request per second
per source. Show me where the delay between requests is applied and confirm
it is per-source, not global. Add exponential backoff on 429 specifically,
and cap total pages so a retry storm is impossible.
```
