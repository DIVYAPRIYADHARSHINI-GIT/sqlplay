# SQLPlay

**Small queries. Big possibilities.** An interactive SQL practice platform with 44 challenges, a free read-only playground and private, browser-local progress. No account or API key is required.

**Live app:** https://sqlplay-xi.vercel.app · **API health:** https://sqlplay-api.vercel.app/health

## Architecture

This repository contains two independently deployable Vercel projects:

```text
sqlplay/
├── frontend/                 # Vite + React + TypeScript
│   ├── src/                  # Screens, UI, typed API client, progress model
│   ├── public/               # Original SVG favicon
│   ├── tests/                # Playwright browser / axe accessibility tests
│   ├── tools/                # Evidence capture and report tooling
│   └── vercel.json
├── backend/                  # Python + FastAPI + standard-library sqlite3
│   ├── main.py               # Validated API, CORS, body/concurrency guards
│   ├── engine.py             # SQLite sandbox and result comparison
│   ├── data/seed.sql         # Deterministic, fictional connected dataset
│   ├── data/challenges.json  # Prompts, 3 hints, reference SQL, order rules
│   ├── tests/                # Safety, seed, checker, all references, API
│   ├── requirements.txt
│   └── vercel.json
├── screenshots/              # Real Chrome captures; local/live labelled
├── bugs/                     # Retained failures and diagnostic captures
├── test-results/             # Actual test output, never estimated counts
├── BUILDER_LOG.md
├── DEPLOY.md
└── FINAL_REPORT.md
```

The frontend requests challenge metadata and schema from FastAPI. CodeMirror runs entirely in the browser and uses schema metadata for SQL autocomplete. Run sends one query to `/run`. Submit sends it to `/challenges/{id}/submit`; the server runs both the learner query and the reference solution on the same immutable seed. Only results and feedback return to the browser. The browser records checked submissions in localStorage and derives completion, topic/level totals, streaks and badges. Query history holds the last 20 queries in component memory only and disappears when leaving the workspace. SQLPlay does not log or persist submitted SQL on its server.

A keeper connection creates the database in RAM at process startup using SQLite's `memdb` VFS. Every execution opens a new connection to that memory database with **`mode=ro`**, enables `query_only`, and applies an authorizer and resource limits. There is no filesystem database, user table, analytics service or authentication system. Runtime instance-local rate-limit counters and concurrency slots contain no IP addresses or user identifiers.

## Local development

Use Python 3.11+ locally with SQLite **3.39+**; the Vercel project requests Python 3.12. Use Node 22.12+ or 24+ and npm. The actual build in this workspace used Node 26.13.1 and Python 3.11.15.

```sh
# Terminal 1, from sqlplay/backend
python3.11 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python -m uvicorn main:app --port 8000 --no-access-log

# Terminal 2, from sqlplay/frontend
npm ci
npm run dev
```

Defaults are frontend `http://127.0.0.1:5173` and backend `http://127.0.0.1:8000`. Both projects provide `.env.example`. Vite loads `.env.local`; for the backend, export `CORS_ORIGINS` in the shell before starting Uvicorn (the app does not silently load dotenv). Never commit `.env` files or credentials.

During this build, 8000 and 5173 belonged to other apps. The verified alternate setup was:

```sh
# backend/
CORS_ORIGINS=http://127.0.0.1:5177,http://localhost:5177 \
  .venv/bin/python -m uvicorn main:app --port 8017 --no-access-log
# frontend/
VITE_API_BASE_URL=http://127.0.0.1:8017 npm run build
npm exec vite preview -- --host 127.0.0.1 --port 5177 --strictPort
```

## Learning features

- Home, searchable/filterable challenge library, challenge workspace, playground and progress dashboard.
- Easy/Medium/Hard, 10 topics, solved/in-progress/not-started filters, shareable filter URLs.
- SQL highlighting, schema-aware completion (`Ctrl+Space`), `Ctrl/Cmd+Enter` to run and `Ctrl/Cmd+Shift+Enter` to submit. Tab leaves the editor when completion is not open; Escape dismisses completion.
- Result table with SQL NULL notation and SQLite execution duration, not a misleading network latency claim.
- Three progressive hints; after three successfully checked submissions, an explicit confirmation reveals a solution. Syntax/safety/network failures do not count as checked submissions. A revealed solution does not itself award completion.
- Schema explorer with an SVG ER diagram, PK/FK details, types, nullability, row counts and three sample rows per table.
- Derived progress, six milestone badges, local-calendar streaks, 14-day activity, JSON backup/import with validation and replace confirmation. A previous solve remains solved after a later mistake. Storage is limited to the latest 50,000 submissions; old history beyond that limit is discarded.
- Light/dark themes, responsive layouts, labelled inputs, live feedback, visible keyboard focus, skip link, semantic tables and reduced-motion support. Fonts are served locally.

## Sample database

All names and transactions are fictional. Currency-like values are generic monetary units; no live commerce data is used.

| Table | Rows | Important relationships / edge cases |
| --- | ---: | --- |
| customers | 16 | Missing emails/cities; some customers have no orders; leap-day join date |
| orders | 24 | customers, employees; guest order and unassigned employee; multiple statuses and dates |
| order_items | 42 | orders, products; quantity, historical price, fractional discount |
| products | 12 | categories; unsold products, equal prices, zero stock, uncategorised product |
| categories | 5 | One empty category |
| employees | 10 | departments and self-referencing manager; tied salaries, unassigned employee |
| departments | 4 | One empty department, missing location |

## Challenge catalogue

Estimated times in the UI are learning estimates, not measured completion times. The checker evaluates results, not whether a particular SQL construct was used.

| # | Challenge | Level | Topic |
| ---: | --- | --- | --- |
| 1 | Meet your customers | Easy | SELECT & WHERE |
| 2 | Hello, Bengaluru | Easy | SELECT & WHERE |
| 3 | The missing addresses | Easy | SELECT & WHERE |
| 4 | The sweet spot | Easy | SELECT & WHERE |
| 5 | Where we call home | Easy | SELECT & WHERE |
| 6 | Top shelf | Easy | ORDER BY & LIMIT |
| 7 | Fresh faces | Easy | ORDER BY & LIMIT |
| 8 | A busy little shop | Easy | Aggregates |
| 9 | A price check | Easy | Aggregates |
| 10 | On the shelves | Easy | Aggregates |
| 11 | Loud and clear | Easy | Strings & dates |
| 12 | The class of 2024 | Easy | Strings & dates |
| 13 | In stock or not? | Easy | CASE expressions |
| 14 | No city, no problem | Easy | Strings & dates |
| 15 | A map of our customers | Medium | GROUP BY & HAVING |
| 16 | Our busiest cities | Medium | GROUP BY & HAVING |
| 17 | Compare the shelves | Medium | GROUP BY & HAVING |
| 18 | A year in orders | Medium | Strings & dates |
| 19 | Put a name to an order | Medium | Joins: INNER |
| 20 | Still just browsing | Medium | Joins: LEFT / anti-join |
| 21 | Every team counts | Medium | Joins: RIGHT |
| 22 | Nobody left behind | Medium | Joins: FULL OUTER |
| 23 | Meet the managers | Medium | Joins: self-join |
| 24 | A planning grid | Medium | Joins: CROSS |
| 25 | A little above average | Medium | Subqueries |
| 26 | Waiting for a first sale | Medium | Subqueries |
| 27 | Something for every budget | Medium | CASE expressions |
| 28 | How long did it take? | Medium | Strings & dates |
| 29 | Read the receipt | Medium | Aggregates |
| 30 | The 500 club | Medium | GROUP BY & HAVING |
| 31 | Make it readable | Hard | CTEs |
| 32 | Ahead of the team | Hard | Subqueries |
| 33 | A fair ranking | Hard | Window functions |
| 34 | Watch the total grow | Hard | Window functions |
| 35 | The order before | Hard | Window functions |
| 36 | The best of each shelf | Hard | Window functions |
| 37 | A slice of inventory | Hard | Window functions |
| 38 | Back for more | Hard | CTEs |
| 39 | Mind the gap | Hard | Window functions |
| 40 | Follow the reporting line | Hard | Recursive CTEs |
| 41 | One row, the whole story | Hard | CASE expressions |
| 42 | A customer's timeline | Hard | CTEs |
| 43 | What really brings it in? | Medium | Joins |
| 44 | Short and sweet | Medium | Strings & dates |

## How answer checking works

1. Validate query length/type and require SELECT or WITH after leading comments.
2. SQLite's own `execute()` enforces a single statement. Its authorizer denies mutation, schema changes, PRAGMA, attachment, system tables, extension loading and unapproved functions. Strings containing semicolons or SQL keywords are not incorrectly rejected as commands.
3. Run user and reference SQL against the same immutable seed. Abort over 500 rows, approximately 200 ms of execution or a 20-million-VM-operation budget. Enforce expression, statement, column, byte-string and compound-query limits as well.
4. Compare column counts, then row counts. Column **names** are ignored; column **positions** matter. NULL equals NULL, not the string `NULL`; numeric text is not automatically a number. Numeric tolerance is `rel_tol=1e-7`, `abs_tol=1e-6`.
5. Ordered challenges compare row by row. Others use multiset matching: duplicates matter, and a bipartite match avoids greedy numeric-tolerance mistakes.
6. Return a helpful count/value/order explanation without sending expected rows or the reference query. Correctness means equivalence on this seed, not a proof for every possible database. A hard-coded answer matching the seed can pass.

The single-process rate bucket allows 120 executions per minute with a burst of 120 and at most four concurrent execution requests. It is privacy-preserving but not a distributed anti-abuse system. Use Vercel edge/firewall controls for production-scale abuse protection. CORS controls browser access, not authentication.

## API

| Method | Path | Response |
| --- | --- | --- |
| GET | `/health` | Status, SQLite version, challenge count, memory-only marker |
| GET | `/challenges` | Public summaries; no solutions |
| GET | `/challenges/{id}` | Prompt, three hints, ordering rule |
| GET | `/schema` | Tables, types, PK/FK, samples, execution limits |
| POST | `/run` | `{columns, rows, row_count, elapsed_ms}` |
| POST | `/challenges/{id}/submit` | Run result plus `{correct, kind, message}` |
| GET | `/challenges/{id}/solution?attempts=3` | Explicit solution reveal |

POST bodies are strictly `{ "query": "SELECT ..." }`. Extra fields and coercions are rejected. Input errors do not echo submitted SQL. The streamed body limit is 16,000 bytes. Responses are `no-store`. There is deliberately no access to reference solutions in challenge list/detail responses, but solution gating is a learning affordance: the server cannot trust an attempt count stored only in a browser.

## SQLite, not MySQL or PostgreSQL

Use `strftime` to extract date parts, `julianday` for elapsed days, `||` for string concatenation and `LIMIT` for row limits. ISO date strings sort chronologically. Integer division truncates: use `100.0`, not `100`, for percentages. RIGHT/FULL OUTER JOIN require SQLite 3.39+, checked at startup. SQLite is permissive about some grouped selects; equality of the result does not prove portable SQL. The UI contains the same dialect guidance.

## Tests and evidence

```sh
# backend/
.venv/bin/python -m pytest -q
# frontend/
npm test
npm run build
npm run test:browser  # real API 8017 + production frontend 5177 must already run
# Use installed Google Chrome; Playwright config sets channel: 'chrome'.
# For another host, install Chrome or change the config to a provisioned Chromium.
BASE_URL=https://YOUR-FRONTEND.vercel.app LIVE=1 \
  PW_REPORT=../test-results/browser-live.json npm run test:browser
```

Unit tests are independent of a live browser. Browser tests run against the real backend except the explicitly labelled loading/error-state tests, which intercept only that state. Axe tests cover serious/critical violations at desktop/mobile widths in both themes; they are not a substitute for a manual screen-reader or physical-phone audit. Failure screenshots are retained outside Playwright's temporary output directory, with timestamped names. Diagnostic screenshots are labelled transcripts, not invented app failures.

See **FINAL_REPORT.md** for the actual test counts, live URLs, screenshots, issues and unverified limitations. See **DEPLOY.md** for the exact two-project deployment sequence. No GitHub remote or automatic Git integration is assumed.
