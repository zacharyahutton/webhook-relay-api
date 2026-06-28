import json
from pathlib import Path
from threading import Lock

DATA_FILE = Path(__file__).resolve().parent.parent / "data" / "store.json"
_lock = Lock()


def _default() -> dict:
    return {"webhooks": {}, "deliveries": []}


def _read() -> dict:
    if not DATA_FILE.exists():
        return _default()
    with DATA_FILE.open(encoding="utf-8") as f:
        return json.load(f)


def _write(data: dict) -> None:
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    with DATA_FILE.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def set_webhook(api_key: str, url: str) -> None:
    with _lock:
        data = _read()
        data["webhooks"][api_key] = url
        _write(data)


def get_webhook(api_key: str) -> str | None:
    data = _read()
    return data["webhooks"].get(api_key)


def append_delivery(record: dict) -> None:
    with _lock:
        data = _read()
        data["deliveries"].append(record)
        _write(data)


def list_deliveries(api_key: str | None = None) -> list[dict]:
    data = _read()
    deliveries = data.get("deliveries", [])
    if api_key is None:
        return deliveries
    return [d for d in deliveries if d.get("api_key") == api_key]
