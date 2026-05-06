from __future__ import annotations

import asyncio
import json
from collections import defaultdict
from pathlib import Path

import config

_locks: dict[int, asyncio.Lock] = defaultdict(asyncio.Lock)


def lock_for(chat_id: int) -> asyncio.Lock:
    return _locks[chat_id]


def _path(chat_id: int) -> Path:
    return config.DATA_DIR / f"{chat_id}.json"


def _bak(chat_id: int) -> Path:
    return config.DATA_DIR / f"{chat_id}.json.bak"


def empty_state(chat_id: int) -> dict:
    return {
        "chat_id": chat_id,
        "active_game": None,
        "last_ended_game": None,
        "history": [],
    }


def load(chat_id: int) -> dict:
    p = _path(chat_id)
    if not p.exists():
        return empty_state(chat_id)
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        b = _bak(chat_id)
        if b.exists():
            try:
                return json.loads(b.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                pass
        return empty_state(chat_id)


def save(chat_id: int, state: dict) -> None:
    p = _path(chat_id)
    if p.exists():
        try:
            _bak(chat_id).write_bytes(p.read_bytes())
        except OSError:
            pass
    tmp = p.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(p)
