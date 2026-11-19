# SQLPlay — free-service publication log

19 November 2026, Asia/Kolkata (IST). This follow-up preserves the original build evidence rather than rewriting its history.

## Preflight

- Git 2.39.5, GitHub CLI 2.102.0 and Vercel CLI 64.2.0 are installed.
- Ran `gh auth status`; active account is DIVYAPRIYADHARSHINI-GIT. Token-related lines were suppressed before tool output.
- Ran `vercel whoami`; existing authentication succeeded.
- Read only the team slug/id and billing-plan name through the supported Vercel API CLI. Team divya-6411 reports `hobby`. No billing/payment details, credentials or raw authentication files were read.
- Existing SQLPlay repository is clean on main, with initial commit 0d47f28 and no remote. Preserve that commit; do not rewrite history.
- Expanded the root ignore rules to cover build/dist, virtual environments, caches, hosting metadata and every dotenv variant. Public, non-secret templates are named environment.example. Previous .env.example files contain only localhost configuration and will be removed from the current Git index, not erased from history.

## GitHub publication

- Set repository-local identity to Divya Priyadharshini / divyapriyadharshini@softage.ai. Kept main and preserved the original first commit.
- The staged-index/history audit checked 124 text blobs, found no matching credential patterns, and found zero dotenv files in the index. This is a pattern check, not a guarantee of exhaustive secret detection. Historical harmless localhost-only templates remain in the original commit; no history was force-rewritten.
- Created publication preparation commit 077d9f9. The requested repository did not already exist in the account listing.
- Created https://github.com/DIVYAPRIYADHARSHINI-GIT/sqlplay as PUBLIC and pushed main, including screenshots/, bugs/, README.md, DEPLOY.md, FINAL_REPORT.md and its PDF. Verified the remote root tree and main branch through gh.
- GitHub's user endpoint did not expose the account billing-plan field. A public repository is included in GitHub Free; no paid feature, Actions workflow, add-on or plan change was created. Official reference: https://docs.github.com/en/get-started/learning-about-github/githubs-plans .

## Ordered redeployment

- Reused the existing two SQLPlay projects on the verified Hobby team rather than creating duplicate projects or accounts.
- Backend tests passed and the backend was deployed first. Public https://sqlplay-api.vercel.app/health returned HTTP 200 in 0.634077 s, SQLite 3.40.0, 44 challenges and memory-only storage.
- Frontend unit tests passed. Set the public VITE_API_BASE_URL config to https://sqlplay-api.vercel.app and deployed the frontend as the separate sqlplay project; the production alias remains https://sqlplay-xi.vercel.app.
- Then set CORS_ORIGINS to exactly https://sqlplay-xi.vercel.app and redeployed sqlplay-api. Every deployment completed on Hobby; no size/time/quota failure or upgrade was encountered.
- Rechecked Vercel project settings and Git origin/main. The publication commit uses the requested name/email. Automatic Git-to-Vercel integration was not added or claimed; these are verified CLI deployments.
- Completed verification: **162 backend tests**, **38 frontend unit tests**, **104 live API checks** and **33 live Chrome browser tests**, all passing with zero failed checks. The backend suite retains its existing one third-party deprecation warning; deployment warnings are retained in the logs.
- The full live learning journey opened a challenge, ran SQL, submitted wrong/correct answers, displayed feedback and updated progress. No unexpected console/page/CORS error was reported. Intentional negative HTTP tests are documented, not counted as defects.
- Fresh screenshots use the publish-live prefix; inspected the new home, correct-submission and wrong-submission captures with Designer's image viewer. Previous captures and bugs were preserved. No new application, tool or deployment failure occurred in this publication pass, so no new failure screenshot was fabricated.
- Updated README.md, DEPLOY.md and FINAL_REPORT.md with the GitHub URL, both stable production URLs, the free-plan evidence and verification results. Regenerated the companion PDF: 42 pages, 34 verified embedded images, no broken image files. Inspected its GitHub/live-links page and fresh Run/correct-answer evidence in Designer's PDF viewer before the final push. Forced cold starts, physical phones/non-Chrome browsers, sustained load/security audits and automatic Git deployment remain outside the verified scope.

No paid resources, account creation, payment details or plan upgrades are authorised or used.
