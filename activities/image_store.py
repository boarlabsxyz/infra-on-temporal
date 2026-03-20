"""
In-memory image store to avoid passing large base64 payloads through Temporal workflow history.

Activities store image data here and pass only a lightweight key through the workflow.
Since all activities run in the same worker process, they share this store.
"""

import uuid
import time
from typing import Optional

_store: dict[str, dict] = {}

TTL_SECONDS = 30 * 60  # 30 minutes


def put(image_data: str) -> str:
    """Store base64 image data and return a key."""
    _cleanup()
    key = str(uuid.uuid4())
    _store[key] = {"data": image_data, "ts": time.time()}
    return key


def get(key: Optional[str]) -> Optional[str]:
    """Retrieve and delete base64 image data by key. Returns None if missing/expired."""
    if not key or key not in _store:
        return None
    entry = _store.pop(key)
    if time.time() - entry["ts"] > TTL_SECONDS:
        return None
    return entry["data"]


def _cleanup():
    """Remove expired entries."""
    now = time.time()
    expired = [k for k, v in _store.items() if now - v["ts"] > TTL_SECONDS]
    for k in expired:
        del _store[k]
