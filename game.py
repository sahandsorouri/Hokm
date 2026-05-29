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
    """Return per-record kot breakdown (normal=+2, hakem=+3).

    Records carry an explicit breakdown once they've been logged/migrated. For any
    still-legacy record we estimate it: assume ~30% of that record's kots were
    hakem-kots (see config.LEGACY_HAKEM_KOT_RATIO)."""
    if rec.get("kots_normal") is not None or rec.get("kots_hakem") is not None:
        return {
            "normal": dict(rec.get("kots_normal", _zero_team())),
            "hakem":  dict(rec.get("kots_hakem",  _zero_team())),
        }
    k = dict(rec.get("kots", _zero_team()))
    hakem = {t: int(k.get(t, 0) * config.LEGACY_HAKEM_KOT_RATIO + 0.5) for t in ("red", "blue")}
    normal = {t: k.get(t, 0) - hakem[t] for t in ("red", "blue")}
    return {"normal": normal, "hakem": hakem}


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
    Legacy records without an explicit breakdown are estimated in _record_split_kots."""
    normal = _zero_team()
    hakem = _zero_team()
    for rec in state["history"]:
        if rec.get("imported"):
            continue
        split = _record_split_kots(rec)
        normal["red"] += split["normal"]["red"]
        normal["blue"] += split["normal"]["blue"]
        hakem["red"] += split["hakem"]["red"]
        hakem["blue"] += split["hakem"]["blue"]
    return {"normal": normal, "hakem": hakem}


def _reconstruct_hands_count(rec: dict) -> int | None:
    """Hands played in a live record. Uses the stored hands_count when present.
    For legacy records (logged before per-hand tracking) it reconstructs the count
    from the final score and kots: every hand scores +1 (normal win), +2 (hakem kot)
    or +3 (hakem-kot). With H = #hands, K = #kots, K3 = #hakem-kots, the points sum to
    H + K + K3, so H = points - K - K3. Yields <= 13 for a single game to 7."""
    hc = rec.get("hands_count")
    if hc is not None:
        return hc
    fs = rec.get("final_score")
    if not fs:
        return None
    points = fs.get("red", 0) + fs.get("blue", 0)
    k = dict(rec.get("kots", _zero_team()))
    total_kots = k.get("red", 0) + k.get("blue", 0)
    split = _record_split_kots(rec)
    hakem_kots = split["hakem"]["red"] + split["hakem"]["blue"]
    return max(0, points - total_kots - hakem_kots)


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

    - games: live records + imported games (imported store a per-day win tally)
    - hands / total_seconds: only games we actually logged (imported games carry
      no per-hand or duration data, so they're not fabricated here)
    - avg_game_seconds / timed_games: average duration over the games that have one
    - durations_after_cutoff: list of durations (sec) for games started >= STATS_DURATION_CUTOFF,
      used for averages/percentiles only.
    """
    games = 0
    hands = 0
    total_seconds = 0.0
    durations_after_cutoff: list[float] = []
    known_durations: list[float] = []
    known_hands: list[int] = []
    imported_games = 0
    for rec in state["history"]:
        if rec.get("imported"):
            wins = rec.get("wins", _zero_team())
            imported_games += int(wins.get("red", 0)) + int(wins.get("blue", 0))
            continue
        games += 1
        hc = _reconstruct_hands_count(rec)
        if hc:
            hands += hc
            known_hands.append(hc)
        dur = _record_duration_sec(rec)
        if dur is None:
            continue
        total_seconds += dur
        known_durations.append(dur)
        try:
            start = datetime.fromisoformat(rec["started_at"])
        except (KeyError, TypeError, ValueError):
            continue
        if start >= config.STATS_DURATION_CUTOFF:
            durations_after_cutoff.append(dur)
    # Imported games count toward the games tally, but they carry no duration or
    # per-hand logs, so we don't fabricate time/hands for them: total_seconds and
    # hands stay grounded in the games we actually logged.
    games += imported_games
    avg_game_seconds = (sum(known_durations) / len(known_durations)) if known_durations else 0.0
    return {
        "games": games,
        "hands": hands,
        "total_seconds": total_seconds,
        "avg_game_seconds": avg_game_seconds,
        "timed_games": len(known_durations),
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
