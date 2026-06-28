import asyncio
import hashlib
import hmac
import json
import uuid
from datetime import datetime, timezone

import httpx
from fastapi import FastAPI, Header, HTTPException, status
from pydantic import BaseModel, HttpUrl

from app.rate_limit import RateLimitMiddleware
from app.store import append_delivery, get_webhook, list_deliveries, set_webhook

API_KEYS: dict[str, str] = {"demo-key": "demo-secret"}

app = FastAPI(
    title="Webhook Relay API",
    description="Portfolio demonstration — register webhooks, sign payloads with HMAC, relay with basic retries.",
    version="0.2.0",
)
app.add_middleware(RateLimitMiddleware, rate=5.0, burst=15.0)


class WebhookRegister(BaseModel):
    url: HttpUrl


class EventTrigger(BaseModel):
    event_type: str
    payload: dict


def sign_payload(secret: str, body: bytes) -> str:
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


async def _post_once(client: httpx.AsyncClient, url: str, raw: bytes, signature: str) -> httpx.Response:
    return await client.post(
        url,
        content=raw,
        headers={"Content-Type": "application/json", "X-Webhook-Signature": signature},
    )


async def deliver_with_retry(secret: str, url: str, envelope: dict, max_attempts: int = 3) -> dict:
    raw = json.dumps(envelope).encode()
    signature = sign_payload(secret, raw)
    attempt_log: list[dict] = []

    async with httpx.AsyncClient(timeout=5.0) as client:
        for attempt in range(1, max_attempts + 1):
            try:
                response = await _post_once(client, url, raw, signature)
                attempt_log.append({"attempt": attempt, "http_status": response.status_code})
                if response.is_success:
                    return {"status": "delivered", "attempts": attempt_log}
            except httpx.HTTPError as exc:
                attempt_log.append({"attempt": attempt, "error": str(exc)})
            if attempt < max_attempts:
                await asyncio.sleep(2 ** (attempt - 1))

    return {"status": "failed", "attempts": attempt_log}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "webhook-relay-api"}


@app.post("/webhooks", status_code=status.HTTP_201_CREATED)
def register_webhook(
    body: WebhookRegister,
    x_api_key: str = Header(..., alias="X-API-Key"),
) -> dict[str, str]:
    if x_api_key not in API_KEYS:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")
    set_webhook(x_api_key, str(body.url))
    return {"message": "Webhook registered", "url": str(body.url)}


@app.post("/events/trigger")
async def trigger_event(
    body: EventTrigger,
    x_api_key: str = Header(..., alias="X-API-Key"),
) -> dict:
    if x_api_key not in API_KEYS:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")
    url = get_webhook(x_api_key)
    if not url:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No webhook registered")

    delivery_id = str(uuid.uuid4())
    envelope = {
        "id": delivery_id,
        "type": body.event_type,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "data": body.payload,
    }

    result = await deliver_with_retry(API_KEYS[x_api_key], url, envelope)
    record = {
        "id": delivery_id,
        "api_key": x_api_key,
        "url": url,
        "status": result["status"],
        "attempts": result["attempts"],
    }
    append_delivery(record)
    return {"delivery_id": delivery_id, "status": result["status"], "attempts": result["attempts"]}


@app.get("/deliveries")
def deliveries(x_api_key: str = Header(..., alias="X-API-Key")) -> list[dict]:
    if x_api_key not in API_KEYS:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")
    return list_deliveries(x_api_key)
