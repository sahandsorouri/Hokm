from __future__ import annotations

import random
from datetime import datetime, timedelta

import config


def now_tz() -> datetime:
    return datetime.now(config.TZ)


def game_day(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=config.TZ)
    else:
        dt = dt.astimezone(config.TZ)
    if dt.hour < config.DAY_CUTOFF_HOUR:
        d = (dt - timedelta(days=1)).date()
    else:
        d = dt.date()
    return d.isoformat()


def random_hakem() -> str:
    return random.choice(["red", "blue"])


def opposite(team: str) -> str:
    return "blue" if team == "red" else "red"


def points_for_kot(hakem: str, winner: str) -> int:
    return 2 if winner == hakem else 3


def new_game() -> dict:
    now = now_tz()
    hakem = random_hakem()
    return {
        "started_at": now.isoformat(),
        "game_day": game_day(now),
        "score_board_message_id": None,
        "initial_hakem": hakem,
        "hakem": hakem,
        "score": {"red": 0, "blue": 0},
        "hands": [],
    }


def add_hand(g: dict, winner: str, kot: bool) -> int:
    pts = points_for_kot(g["hakem"], winner) if kot else 1
    g["hands"].append({"winner": winner, "points": pts, "kot": kot})
    g["score"][winner] += pts
    g["hakem"] = winner
    return pts


def can_undo(g: dict | None) -> bool:
    return bool(g and g["hands"])


def undo_last(g: dict) -> dict | None:
    if not g["hands"]:
        return None
    last = g["hands"].pop()
    score = {"red": 0, "blue": 0}
    hakem = g["initial_hakem"]
    for h in g["hands"]:
        score[h["winner"]] += h["points"]
        hakem = h["winner"]
    g["score"] = score
    g["hakem"] = hakem
    return last


def game_ended(g: dict) -> bool:
    return g["score"]["red"] >= config.WIN_TARGET or g["score"]["blue"] >= config.WIN_TARGET


def winner_team(g: dict) -> str:
    return "red" if g["score"]["red"] >= g["score"]["blue"] else "blue"


def kots_per_team(g: dict) -> dict:
    out = {"red": 0, "blue": 0}
    for h in g["hands"]:
        if h["kot"]:
            out[h["winner"]] += 1
    return out


def archive_game(state: dict) -> dict:
    g = state["active_game"]
    now = now_tz()
    record = {
        "game_day": g["game_day"],
        "started_at": g["started_at"],
        "ended_at": now.isoformat(),
        "winner": winner_team(g),
        "final_score": dict(g["score"]),
        "kots": kots_per_team(g),
    }
    state["history"].append(record)
    state["last_ended_game"] = {
        "ended_at": now.isoformat(),
        "active_game": g,
        "end_message_id": None,
    }
    state["active_game"] = None
    return record


def can_undo_ended(state: dict) -> bool:
    leg = state.get("last_ended_game")
    if not leg or state.get("active_game"):
        return False
    try:
        ended = datetime.fromisoformat(leg["ended_at"])
    except (TypeError, ValueError):
        return False
    return (now_tz() - ended).total_seconds() <= config.UNDO_WINDOW_SECONDS


def restore_last_game(state: dict) -> bool:
    if not can_undo_ended(state):
        return False
    leg = state["last_ended_game"]
    g = leg["active_game"]
    if state["history"]:
        state["history"].pop()
    state["active_game"] = g
    state["last_ended_game"] = None
    undo_last(g)
    return True


def clear_last_ended(state: dict) -> None:
    state["last_ended_game"] = None


def add_imported_day(state: dict, day: str, red_wins: int, blue_wins: int,
                     red_kots: int, blue_kots: int, replace: bool = False) -> None:
    if replace:
        state["history"] = [r for r in state["history"] if r.get("game_day") != day]
    rec = {
        "game_day": day,
        "imported": True,
        "wins": {"red": red_wins, "blue": blue_wins},
        "kots": {"red": red_kots, "blue": blue_kots},
    }
    state["history"].append(rec)


def has_day(state: dict, day: str) -> bool:
    return any(r.get("game_day") == day for r in state["history"])


def _record_wins_kots(rec: dict) -> tuple[dict, dict]:
    if rec.get("imported"):
        return dict(rec.get("wins", {"red": 0, "blue": 0})), dict(rec.get("kots", {"red": 0, "blue": 0}))
    wins = {"red": 0, "blue": 0}
    wins[rec["winner"]] = 1
    return wins, dict(rec.get("kots", {"red": 0, "blue": 0}))


def daily_breakdown(state: dict) -> dict:
    by_day: dict[str, dict] = {}
    for rec in state["history"]:
        d = rec.get("game_day")
        if not d:
            continue
        slot = by_day.setdefault(d, {"red": 0, "blue": 0, "kots": {"red": 0, "blue": 0}})
        wins, kots = _record_wins_kots(rec)
        slot["red"] += wins["red"]
        slot["blue"] += wins["blue"]
        slot["kots"]["red"] += kots["red"]
        slot["kots"]["blue"] += kots["blue"]
    return by_day


def totals(state: dict) -> tuple[dict, dict]:
    total_w = {"red": 0, "blue": 0}
    total_k = {"red": 0, "blue": 0}
    for rec in state["history"]:
        wins, kots = _record_wins_kots(rec)
        total_w["red"] += wins["red"]
        total_w["blue"] += wins["blue"]
        total_k["red"] += kots["red"]
        total_k["blue"] += kots["blue"]
    return total_w, total_k


def today_summary(state: dict) -> dict:
    today = game_day(now_tz())
    by = daily_breakdown(state)
    today_slot = by.get(today, {"red": 0, "blue": 0, "kots": {"red": 0, "blue": 0}})
    total_w, total_k = totals(state)
    return {
        "today_date": today,
        "today_wins": {"red": today_slot["red"], "blue": today_slot["blue"]},
        "today_kots": dict(today_slot["kots"]),
        "total_wins": total_w,
        "total_kots": total_k,
    }
