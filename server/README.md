# BookEater Catalog Proxy

Small stateless proxy for real-book discovery. The desktop app does **not** contain the upstream
Kakao REST API key and does **not** send reading notes, monster lineage, hidden growth scores, or
other genetics to this service.

## Public endpoints

- `GET /health`
- `GET /v1/catalog/search?q=<explicit user query>&limit=30`
- `GET /v1/catalog/pool?limit=40`

`/search` forwards only the text the user explicitly searched for. `/pool` uses server-owned broad
terms and is intentionally non-personalized. The desktop ranks the returned real books locally.

## Required environment

- `KAKAO_REST_API_KEY`: server-side Kakao REST API key. Required. Never bundle this into BookEater.

Optional:

- `BOOKEATER_CATALOG_HOST` — default `127.0.0.1` (`0.0.0.0` in the Docker image)
- `BOOKEATER_CATALOG_PORT` — default `8787`

The process validates the Kakao key at startup and exits rather than serving a permanently broken
proxy when the key is missing.

## Local run

```bash
KAKAO_REST_API_KEY=... python -m server.catalog_proxy
```

For local desktop testing:

```bash
BOOKEATER_CATALOG_ENDPOINT=http://localhost:8787 BookEater.exe
```

Plain HTTP is accepted by the desktop only for localhost. A deployed endpoint must be HTTPS.

## Docker

Build from the repository root:

```bash
docker build -f server/Dockerfile -t bookeater-catalog .
docker run --rm -p 8787:8787 \
  -e KAKAO_REST_API_KEY=... \
  bookeater-catalog
```

The image has a `/health` Docker healthcheck and no persistent volume requirement. Put TLS in front
of the container using the hosting platform/reverse proxy. Do not expose the Kakao key to client
build logs or desktop configuration.

## Production notes

- Deploy behind HTTPS.
- Keep the service stateless; do not add reading-profile storage here.
- Keep request/response size and query length caps enabled.
- Do not enable raw request logging that might retain explicit search queries unless there is a
  deliberate privacy policy and retention plan.
- The desktop endpoint URL is public configuration, not a secret. The upstream Kakao key is secret.
- If the proxy is unavailable, the desktop recommendation UI must fail closed: no invented books.
