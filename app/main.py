import hashlib
import hmac
import json
import uuid
from datetime import datetime, timezone

import httpx
from fastapi import FastAPI, Header, HTTPException, status
from pydantic import BaseModel, HttpUrl

API_KEYS: dict[str, str] = {"demo-key": "demo-secret"}
WEBHOOKS: dict[str, HttpUrl] = {}
DELIVERIES: list[dict] = []

app = FastAPI(
    title="Webhook Relay API",
    description="Portfolio demonstration — webhook sandbox starter",
    version="0.1.0",
)


class WebhookRegister(BaseModel):
    url: HttpUrl


class EventTrigger(BaseModel):
    event_type: str
    payload: dict


def sign_payload(secret: str, body: bytes) -> str:
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


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
    WEBHOOKS[x_api_key] = body.url
    return {"message": "Webhook registered", "url": str(body.url)}


@app.post("/events/trigger")
async def trigger_event(
    body: EventTrigger,
    x_api_key: str = Header(..., alias="X-API-Key"),
) -> dict:
    if x_api_key not in API_KEYS:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")
    url = WEBHOOKS.get(x_api_key)
    if not url:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No webhook registered")

    delivery_id = str(uuid.uuid4())
    envelope = {
        "id": delivery_id,
        "type": body.event_type,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "data": body.payload,
    }
    raw = json.dumps(envelope).encode()
    signature = sign_payload(API_KEYS[x_api_key], raw)

    attempt = {"id": delivery_id, "status": "pending", "url": str(url)}
    async with httpx.AsyncClient(timeout=5.0) as client:
        try:
            response = await client.post(
                str(url),
                content=raw,
                headers={
                    "Content-Type": "application/json",
                    "X-Webhook-Signature": signature,
                },
            )
            attempt["status"] = "delivered" if response.is_success else "failed"
            attempt["http_status"] = response.status_code
        except httpx.HTTPError as exc:
            attempt["status"] = "failed"
            attempt["error"] = str(exc)

    DELIVERIES.append(attempt)
    return {"delivery_id": delivery_id, "status": attempt["status"]}


@app.get("/deliveries")
def list_deliveries(x_api_key: str = Header(..., alias="X-API-Key")) -> list[dict]:
    if x_api_key not in API_KEYS:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")
    return DELIVERIES
