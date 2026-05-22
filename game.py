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
        "last_event_at": now.isoformat(),
        "game_day": game_day(now),
        "score_board_message_id": None,
        "initial_hakem": hakem,
        "hakem": hakem,
        "score": {"red": 0, "blue": 0},
        "hands": [],
    }


def _apply_wrap(score: dict, team: str) -> bool:
    """If team's score went strictly above WIN_TARGET, subtract WIN_TARGET.
    Returns True if a wrap happened."""
    if score[team] > config.WIN_TARGET:
        score[team] -= config.WIN_TARGET
        return True
    return False


def add_hand(g: dict, winner: str, kot: bool) -> int:
    hakem_before = g["hakem"]
    pts = points_for_kot(hakem_before, winner) if kot else 1
    g["score"][winner] += pts
    wrapped = _apply_wrap(g["score"], winner)
    g["hands"].append({
        "winner": winner,
        "points": pts,
        "kot": kot,
        "wrapped": wrapped,
        "hakem_at_hand": hakem_before,
    })
    g["hakem"] = winner
    g["last_event_at"] = now_tz().isoformat()
    return pts


def split_kots(g: dict) -> dict:
    """Return separated kot counts per team for an active or just-finished game.
    kots_normal: team kotted as hakem (+2). kots_hakem: team kotted opponent who was hakem (+3)."""
    out = {
        "normal": {"red": 0, "blue": 0},
        "hakem":  {"red": 0, "blue": 0},
    }
    for h in g["hands"]:
        if not h.get("kot"):
            continue
        winner = h["winner"]
        # hakem_at_hand may be missing on legacy records; infer from points (2 -> normal, 3 -> hakem)
        hakem_at = h.get("hakem_at_hand")
        if hakem_at is None:
            bucket = "normal" if h.get("points") == 2 else "hakem"
        else:
            bucket = "normal" if winner == hakem_at else "hakem"
        out[bucket][winner] += 1
    return out


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
        _apply_wrap(score, h["winner"])
        hakem = h["winner"]
    g["score"] = score
    g["hakem"] = hakem
    g["last_event_at"] = now_tz().isoformat()
    return last


def game_ended(g: dict) -> bool:
    return g["score"]["red"] == config.WIN_TARGET or g["score"]["blue"] == config.WIN_TARGET


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
    sk = split_kots(g)
    record = {
        "game_day": g["game_day"],
        "started_at": g["started_at"],
        "ended_at": now.isoformat(),
        "winner": winner_team(g),
        "final_score": dict(g["score"]),
        "kots": kots_per_team(g),           # legacy total, kept for back-compat
        "kots_normal": sk["normal"],         # team kotted as hakem (+2 each)
        "kots_hakem":  sk["hakem"],          # team kotted opponent who was hakem (+3 each)
        "initial_hakem": g.get("initial_hakem"),
        "hands_count": len(g["hands"]),
        "hands": list(g["hands"]),
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


def _zero_team() -> dict:
    return {"red": 0, "blue": 0}


def _record_wins_kots(rec: dict) -> tuple[dict, dict]:
    if rec.get("imported"):
        return dict(rec.get("wins", _zero_team())), dict(rec.get("kots", _zero_team()))
    wins = _zero_team()
    wins[rec["winner"]] = 1
    return wins, dict(rec.get("kots", _zero_team()))


def _record_split_kots(rec: dict) -> dict:
    """Return per-record kot breakdown. For legacy records without the breakdown,
    return None per bucket so callers can show 'unknown' instead of guessing."""
    if rec.get("kots_normal") is not None or rec.get("kots_hakem") is not None:
        return {
            "normal": dict(rec.get("kots_normal", _zero_team())),
            "hakem":  dict(rec.get("kots_hakem",  _zero_team())),
            "known": True,
        }
    return {
        "normal": _zero_team(),
        "hakem":  _zero_team(),
        "known": False,
    }


def daily_breakdown(state: dict) -> dict:
    by_day: dict[str, dict] = {}
    for rec in state["history"]:
        d = rec.get("game_day")
        if not d:
            continue
        slot = by_day.setdefault(d, {"red": 0, "blue": 0, "kots": _zero_team()})
        wins, kots = _record_wins_kots(rec)
        slot["red"] += wins["red"]
        slot["blue"] += wins["blue"]
        slot["kots"]["red"] += kots["red"]
        slot["kots"]["blue"] += kots["blue"]
    return by_day


def totals(state: dict) -> tuple[dict, dict]:
    total_w = _zero_team()
    total_k = _zero_team()
    for rec in state["history"]:
        wins, kots = _record_wins_kots(rec)
        total_w["red"] += wins["red"]
        total_w["blue"] += wins["blue"]
        total_k["red"] += kots["red"]
        total_k["blue"] += kots["blue"]
    return total_w, total_k


def split_kot_totals(state: dict) -> dict:
    """Aggregate split kot counts across all live (non-imported) records.
    Returns counts plus a flag for whether any record was 'unknown' (legacy)."""
    normal = _zero_team()
    hakem = _zero_team()
    has_legacy = False
    legacy_total = _zero_team()
    for rec in state["history"]:
        if rec.get("imported"):
            continue
        split = _record_split_kots(rec)
        if split["known"]:
            normal["red"] += split["normal"]["red"]
            normal["blue"] += split["normal"]["blue"]
            hakem["red"] += split["hakem"]["red"]
            hakem["blue"] += split["hakem"]["blue"]
        else:
            has_legacy = True
            kots = dict(rec.get("kots", _zero_team()))
            legacy_total["red"] += kots["red"]
            legacy_total["blue"] += kots["blue"]
    return {
        "normal": normal,
        "hakem": hakem,
        "has_legacy": has_legacy,
        "legacy_total": legacy_total,
    }


def _record_duration_sec(rec: dict) -> float | None:
    """Wall-clock duration of a live (non-imported) record, in seconds. None if unavailable."""
    if rec.get("imported"):
        return None
    try:
        start = datetime.fromisoformat(rec["started_at"])
        end = datetime.fromisoformat(rec["ended_at"])
        return (end - start).total_seconds()
    except (KeyError, TypeError, ValueError):
        return None


def lifetime_stats(state: dict) -> dict:
    """Lifetime aggregates over the chat's history.

    - games / hands / total_seconds: across ALL live records
    - durations_after_cutoff: list of durations (sec) for games started >= STATS_DURATION_CUTOFF,
      used for averages/percentiles only.
    """
    games = 0
    hands = 0
    total_seconds = 0.0
    durations_after_cutoff: list[float] = []
    for rec in state["history"]:
        if rec.get("imported"):
            continue
        games += 1
        if rec.get("hands_count"):
            hands += rec["hands_count"]
        dur = _record_duration_sec(rec)
        if dur is None:
            continue
        total_seconds += dur
        try:
            start = datetime.fromisoformat(rec["started_at"])
        except (KeyError, TypeError, ValueError):
            continue
        if start >= config.STATS_DURATION_CUTOFF:
            durations_after_cutoff.append(dur)
    return {
        "games": games,
        "hands": hands,
        "total_seconds": total_seconds,
        "durations_after_cutoff": durations_after_cutoff,
    }


def duration_percentile_faster(durations: list[float], this_dur: float) -> int | None:
    """% of `durations` that were SLOWER than `this_dur` (i.e., this game beat that fraction).
    Returns an int 0..100, or None if input is empty."""
    if not durations:
        return None
    slower = sum(1 for d in durations if d > this_dur)
    return round(100 * slower / len(durations))


def today_summary(state: dict) -> dict:
    today = game_day(now_tz())
    by = daily_breakdown(state)
    today_slot = by.get(today, {"red": 0, "blue": 0, "kots": _zero_team()})
    total_w, total_k = totals(state)
    split = split_kot_totals(state)
    return {
        "today_date": today,
        "today_wins": {"red": today_slot["red"], "blue": today_slot["blue"]},
        "today_kots": dict(today_slot["kots"]),
        "total_wins": total_w,
        "total_kots": total_k,
        "split_kots": split,
    }
