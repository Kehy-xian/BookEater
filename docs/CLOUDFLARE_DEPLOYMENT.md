# BookEater Cloudflare deployment

Production Worker information that is safe to keep in source control:

- Worker: `bookeater-api`
- Public endpoint: `https://bookeater-api.bookeater-kehy.workers.dev`
- D1 database name: `bookeater-feedback`
- D1 database ID: `7893f1ad-eb1f-4925-9614-86ad23fba063`
- Cleanup schedule: `17 3 * * *` UTC
- First production deployment: 2026-09-03

The Aladin TTB credential is not stored here, in `wrangler.toml`, in GitHub, or in the Windows
application. It is stored only as the Cloudflare Worker secret `ALADIN_TTB_KEY`.

The public catalog contract is:

- `GET /health`
- `GET /v1/books/search?q=<explicit user query>&max_results=20`
- `GET /v1/books/list?type=Bestseller&max_results=20`

BookEater sends only an explicit search query or a generic list request. Reading notes, local
library contents, hidden traits, growth history and monster lineage are not sent to this service.
Short-lived book search caching uses the Worker Cache API rather than D1.

The D1 binding exists for the future explicit opt-in improvement flow. That desktop upload flow is
disabled until consent, preview, retry and deletion-request UI are implemented and reviewed.
