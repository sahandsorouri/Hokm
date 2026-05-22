"""Structured append-only event log per chat.

One file per chat: data/<chat_id>.events.jsonl. Each line is a JSON object with at
least a `type` and `ts` (ISO timestamp in TZ from config). The log is the source
of truth for retroactive analysis; it complements the JSON state file (which only
holds the current/last-ended game + summarized history).
"""

from __future__ import annotations

import json
import logging
import threading
from datetime import datetime

import config

log = logging.getLogger("hokm.events")

_lock = threading.Lock()


def _path(chat_id: int):
    return config.DATA_DIR / f"{chat_id}.events.jsonl"


def append(chat_id: int, event: dict) -> None:
    """Append a single event line. Best-effort: errors are logged, never raised."""
    try:
        payload = {"ts": datetime.now(config.TZ).isoformat(), **event}
        line = json.dumps(payload, ensure_ascii=False) + "\n"
        with _lock:
            with open(_path(chat_id), "a", encoding="utf-8") as f:
                f.write(line)
    except OSError as e:
        log.warning("events.append failed (chat=%s): %s", chat_id, e)
