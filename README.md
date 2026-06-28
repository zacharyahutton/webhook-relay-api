# Webhook Relay API

Webhook Relay is a **portfolio demonstration** sandbox for testing outbound webhooks. Register a callback URL with an API key, trigger signed JSON events (HMAC-SHA256), and inspect delivery attempts. It uses file-backed storage and an in-memory token-bucket rate limiter—not production-grade Redis infrastructure.

## Stack

- Python 3.11+
- FastAPI, httpx, Pydantic
- HMAC-SHA256 signatures
- JSON file store under `data/`
- In-memory rate limiting middleware

## Prerequisites

- Python 3.11+
- A public HTTPS URL (or local tunnel) if you want to receive real callbacks; use https://webhook.site for quick tests

## Setup

```bash
git clone https://github.com/zacharyahutton/webhook-relay-api.git
cd webhook-relay-api
python -m venv .venv
.venv\Scripts\activate   # Windows
# source .venv/bin/activate
pip install -r requirements.txt
```

## How to run

```bash
uvicorn app.main:app --reload
```

Docs: http://127.0.0.1:8000/docs

Demo API key: `demo-key` (secret used for signing: `demo-secret` — hard-coded for learning only).

## How to test

### Curl flow

1. Register a webhook (use a URL from webhook.site):

```bash
curl -s -X POST http://127.0.0.1:8000/webhooks \
  -H "X-API-Key: demo-key" \
  -H "Content-Type: application/json" \
  -d "{\"url\":\"https://webhook.site/your-uuid\"}"
```

2. Trigger an event:

```bash
curl -s -X POST http://127.0.0.1:8000/events/trigger \
  -H "X-API-Key: demo-key" \
  -H "Content-Type: application/json" \
  -d "{\"event_type\":\"order.created\",\"payload\":{\"orderId\":\"42\"}}"
```

Sample response:

```json
{"delivery_id":"<uuid>","status":"delivered","attempts":[{"attempt":1,"http_status":200}]}
```

3. List deliveries:

```bash
curl -s http://127.0.0.1:8000/deliveries -H "X-API-Key: demo-key"
```

Verify the receiver got header `X-Webhook-Signature` (hex HMAC of the raw JSON body).

### Rate limits

Excessive requests with the same `X-API-Key` return `429` with `Retry-After: 1`.

## API endpoints

| Method | Path | Headers | Description |
|--------|------|---------|-------------|
| GET | `/health` | — | Health check |
| POST | `/webhooks` | `X-API-Key` | Register callback URL |
| POST | `/events/trigger` | `X-API-Key` | Deliver signed event (retries with backoff) |
| GET | `/deliveries` | `X-API-Key` | Delivery history for this key |

## Project structure

```
app/
  main.py         Routes and delivery engine
  store.py        JSON file persistence
  rate_limit.py   Token-bucket middleware
data/
  store.json      Created at runtime (gitignored)
```

## Portfolio disclaimer

Linked from the [Webhook Relay case study](https://github.com/zacharyahutton/portfolio). The portfolio write-up discusses Redis token buckets, dead-letter queues, and replay endpoints; **this repo implements a simplified, honest slice** so you can clone and run it without Redis.

## VS Code

1. **File → Open Folder** and select this repository root.
2. Install recommended extensions when prompted (Python or Node/Java packs).
3. **Run and Debug** (`F5`): choose **FastAPI (uvicorn) depending on the repo.
4. **Terminal → Run Task**: `dev: uvicorn`, `npm: dev`, or `mvn: test`.

Workspace settings live in `.vscode/` (`extensions.json`, `launch.json`, `tasks.json`, `settings.json`).

## Future improvements

- Redis-backed rate limits and delivery queue
- Replay endpoint for failed deliveries
- Configurable API keys via environment variables
- Signature verification helper script for consumers

## License

MIT
