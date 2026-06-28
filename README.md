# Webhook Relay API

> **Portfolio demonstration** — a sandbox API for testing outbound webhooks with HMAC signatures, retries, and rate limits. Starter implementation for learning integration patterns, not production webhook infrastructure.

## Problem

Developers need a safe place to observe webhook delivery, signature verification, exponential backoff, and per-key throttling without standing up multiple services.

## Stack

- Python 3.11+ · FastAPI · HMAC-SHA256 · Redis (optional for full rate limiting)

## Quick start

```bash
python -m venv .venv
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Endpoints (starter)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| POST | `/webhooks` | Register a callback URL |
| POST | `/events/trigger` | Queue a signed delivery |
| GET | `/deliveries` | List delivery attempts |

## Disclaimer

Portfolio starter repo linked from [zacharyahutton/portfolio](https://github.com/zacharyahutton/portfolio). Redis-backed token buckets and persistent dead-letter queues are documented in the case study but simplified here.

## License

MIT
