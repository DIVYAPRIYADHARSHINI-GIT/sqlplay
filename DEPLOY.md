# SQLPlay — two-project Vercel deployment

## Production addresses

- Frontend project **sqlplay**: https://sqlplay-xi.vercel.app
- Backend project **sqlplay-api**: https://sqlplay-api.vercel.app
- Public health: https://sqlplay-api.vercel.app/health

The Vercel team used for this build is `divya-6411`. The stable frontend alias was assigned by Vercel; do not assume `sqlplay.vercel.app` belongs to this project. This is a CLI deployment of one repository, not a claimed GitHub auto-deploy setup.

## 1. Prerequisites: stop if authentication is unavailable

From a terminal:

```sh
command -v vercel
vercel --version
vercel whoami
```

If the CLI is missing, the account owner should run `npm install -g vercel`. If not authenticated, the account owner should run `vercel login` and complete Vercel's browser flow. Do not create a new account automatically, paste a token in source files, or share a token in chat. This build used the existing authenticated Vercel CLI 64.2.0.

Run the local test gates before deploying:

```sh
cd backend
.venv/bin/python -m pytest -q
cd ../frontend
npm ci
npm test
npm run build
# With local API/frontend servers running, as described in README.md:
npm run test:browser
cd ..
```

## 2. Deploy the backend first

Run all following Vercel commands from the **sqlplay repository root**, not from its parent starter workspace. The remote project root is the backend subdirectory.

For a new account/project only (do not recreate or overwrite an existing unrelated project):

```sh
vercel project create sqlplay-api
vercel project update sqlplay-api --root-directory backend --framework other --yes
```

Deploy:

```sh
vercel deploy --project sqlplay-api --prod --yes </dev/null
curl -fsS https://sqlplay-api.vercel.app/health
```

Use the actual production alias printed by your deployment if different. Expect HTTP 200 and JSON containing `status: ok`, `database: SQLite`, `challenges: 44` and `storage: memory-only`. Do not proceed just because the CLI says Ready. The first build of this project said Ready but failed at runtime; the final manifest includes the fix.

### Backend files that matter

- `backend/vercel.json` uses `@vercel/python` for `main.py` and routes all paths there.
- `backend/pyproject.toml` selects Python 3.12 and declares all runtime dependencies.
- `backend/requirements.txt` contains the same dependency pins for local pip installs.
- **Keep those dependency lists in sync.** Vercel used pyproject.toml preferentially; a regression test enforces equality.
- `backend/data/` must be uploaded. The database is built from seed.sql entirely in memory at runtime. Never upload a user database.
- The host's Python build omits `enable_load_extension` because extension loading is compiled out. The final engine checks for that optional method, and the authorizer always denies the SQL function. Do not reintroduce an unconditional call.
- `/health` now executes a real restricted `SELECT 1`; a metadata-only health response missed the host-specific execution defect during initial deployment. Check an actual POST `/run` as well.

Vercel warns that explicit `builds` overrides dashboard Build/Development settings. This configuration intentionally keeps the backend routing/build explicit. The remote **root directory still must be backend**.

## 3. Deploy the frontend with the real API URL

For a new project only:

```sh
vercel project create sqlplay
vercel project update sqlplay --root-directory frontend --framework vite --node-version 24.x --yes
```

Set the public build configuration and deploy:

```sh
vercel env add VITE_API_BASE_URL production --project sqlplay \
  --value https://sqlplay-api.vercel.app --no-sensitive --yes </dev/null
vercel deploy --project sqlplay --prod --yes </dev/null
```

For updates to an existing variable, add `--force`. Use only the actual backend alias. `VITE_API_BASE_URL` is deliberately public, not a secret; Vite embeds it into the bundle. Changing it requires a new frontend build.

During this build, an `env add` command printed success but did not exit. Sending EOF through the task tool did not fix that process. It was stopped, the saved variable was verified with a separate `vercel env ls production --project sqlplay --scope divya-6411`, and deployment was run separately with closed stdin. If the same symptom appears, verify the saved state rather than blindly creating duplicate variables.

## 4. Restrict backend CORS to the final frontend origin

For this deployment the exact origin is `https://sqlplay-xi.vercel.app` (no path or trailing slash):

```sh
vercel env add CORS_ORIGINS production --project sqlplay-api \
  --scope divya-6411 --value https://sqlplay-xi.vercel.app \
  --no-sensitive --yes </dev/null
vercel deploy --project sqlplay-api --prod --yes </dev/null
```

Again, use `--force` only when deliberately updating the existing config. A comma-separated list is supported for explicitly allowed origins. Do not use `*`; the app rejects wildcard configuration. Do not include arbitrary preview domains. Preview origins require their own explicit environment configuration and may be protected by Vercel authentication.

## 5. Verify the live deployment

### Health and CORS

```sh
curl -i https://sqlplay-api.vercel.app/health
curl -i -X OPTIONS https://sqlplay-api.vercel.app/run \
  -H 'Origin: https://sqlplay-xi.vercel.app' \
  -H 'Access-Control-Request-Method: POST' \
  -H 'Access-Control-Request-Headers: content-type'
```

Expect `access-control-allow-origin: https://sqlplay-xi.vercel.app`. An unlisted origin must not receive that header. CORS is a browser policy, not authentication or an abuse firewall.

### Every reference solution and wrong answer, against the real API

From the repository root:

```sh
backend/.venv/bin/python backend/tests/verify_live.py \
  https://sqlplay-api.vercel.app https://sqlplay-xi.vercel.app \
  test-results/live-api.json
```

This makes 104 checks: repeated health, metadata, all 44 correct references, 44 deliberately wrong answers, seven safety probes, both CORS directions, strict type validation and seed integrity. It records network timings without logging submitted query text.

### Actual browser journey

From frontend/ (Google Chrome must be installed):

```sh
BASE_URL=https://sqlplay-xi.vercel.app LIVE=1 \
  PW_REPORT=../test-results/browser-live.json npm run test:browser
```

The suite covers actual Run/Submit, wrong/correct feedback, hints, solution reveal, schema samples, history, table/column completion, keyboard shortcuts/exit, progress persistence/import/export, themes and responsive layouts. Only the tests explicitly named for simulated API error/loading intercept a request. Screenshots are prefixed `live-`. Failure captures always go to timestamped names in `bugs/`, never to a directory the runner clears.

Also manually open the stable frontend in a clean browser session, refresh a deep challenge link and inspect the Network/Console panels. Do not use an authenticated `vercel curl` response as evidence that public browser access works. This build verified the stable production aliases publicly; Vercel's preview protection warning was not itself evidence of a production login wall.

### Runtime diagnostics

```sh
vercel logs --scope divya-6411 --project sqlplay-api --limit 10 --json
```

An explicit scope was necessary for this CLI's log command. A Python import traceback was labelled `info` on stderr, so filtering only `level:error` hid the useful record. Do not enable query-body logging. Hosting infrastructure can retain request metadata independently of application logging; SQLPlay does not claim control over Vercel's internal telemetry.

## Environment variables

| Project | Variable | Local default | Production |
| --- | --- | --- | --- |
| frontend | VITE_API_BASE_URL | http://127.0.0.1:8000 | https://sqlplay-api.vercel.app |
| backend | CORS_ORIGINS | http://localhost:5173,http://127.0.0.1:5173 | https://sqlplay-xi.vercel.app |

No API keys or tokens are required by SQLPlay. Both projects have non-secret `environment.example` templates. Every `.env` variant, `.vercel`, venv, node_modules, dist and build folder is ignored by Git. The earlier harmless `.env.example` templates are no longer tracked at the branch tip; their historical contents contain only public localhost URLs. `.vercelignore` also excludes evidence, local dependencies and build output from deployment uploads.

## Limits and operations

SQLite execution is bounded to roughly 200 ms / 20 million VM operations, 500 returned rows, 8,000 SQL characters, 64 output columns, a 100,000-byte SQLite value limit and a 16,000-byte HTTP body. These are application limits, not Vercel's overall function duration. Four execution slots and 120 requests/minute are enforced per process, so a scaled deployment has independent buckets. Cold starts create a fresh seed; user progress is never on that server. The browser has a 20-second API timeout and friendly retry messages.

Infrastructure cold starts cannot be forced reliably by this test harness. First post-deployment health timings and repeated warm-path requests are recorded, but they are not a proven cold-start benchmark. There is no uptime SLA, distributed rate limiter, independent penetration test or large-concurrency load test. Add edge/firewall limits before opening the API to heavy untrusted traffic.

Progress is device-local and user-editable. Solution-reveal attempt counts are advisory. The checker proves equivalence only on this fixed sample dataset; it does not verify SQL syntax choices or mathematical equivalence on all possible data. A cross-browser/physical-device audit and manual screen-reader review remain outside the verified scope.

## Rollback and report regeneration

Use the Vercel project's Deployments UI to promote a previously verified production deployment. Recheck health and CORS after a rollback, because frontend/API environment compatibility matters. No destructive remote cleanup or account changes are needed.

After updating FINAL_REPORT.md, regenerate its HTML/PDF from frontend/:

```sh
node tools/export-report.mjs
```

The exporter verifies that every embedded screenshot loads before printing the PDF. The Markdown report remains the source of truth.
