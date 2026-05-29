from __future__ import annotations
from datetime import datetime

_FA_DIGITS = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")


def fa(n) -> str:
    return str(n).translate(_FA_DIGITS)


def _format_duration(started_at: str, ended_at: str) -> str:
    try:
        start = datetime.fromisoformat(started_at)
        end = datetime.fromisoformat(ended_at)
        total = int((end - start).total_seconds())
        if total < 60:
            return f"{fa(total)} ثانیه"
        minutes = total // 60
        if minutes < 60:
            return f"{fa(minutes)} دقیقه"
        hours = minutes // 60
        mins = minutes % 60
        if mins == 0:
            return f"{fa(hours)} ساعت"
        return f"{fa(hours)} ساعت و {fa(mins)} دقیقه"
    except (TypeError, ValueError):
        return ""


TEAM_LABEL = {"red": "🔴 قرمز", "blue": "🔵 آبی"}
TEAM_COLOR = {"red": "🔴", "blue": "🔵"}
TEAM_NAME = {"red": "قرمز", "blue": "آبی"}


def _last_hand_line(g: dict) -> str:
    if not g["hands"]:
        return "هنوز دستی ثبت نشده"
    last = g["hands"][-1]
    label = TEAM_NAME[last["winner"]]
    if last["kot"]:
        return f"آخرین: {label} کت کرد (+{fa(last['points'])}) ⚡"
    return f"آخرین: {label} برد (+{fa(last['points'])})"


def _relative_time(iso_str: str) -> str:
    """'همین الان' / 'X ثانیه پیش' / 'X دقیقه پیش' / 'X ساعت پیش' from an ISO timestamp."""
    from game import now_tz
    try:
        then = datetime.fromisoformat(iso_str)
    except (TypeError, ValueError):
        return ""
    delta = (now_tz() - then).total_seconds()
    if delta < 10:
        return "همین الان"
    if delta < 60:
        return f"{fa(int(delta))} ثانیه پیش"
    minutes = int(delta // 60)
    if minutes < 60:
        return f"{fa(minutes)} دقیقه پیش"
    hours = minutes // 60
    mins = minutes % 60
    if mins == 0:
        return f"{fa(hours)} ساعت پیش"
    return f"{fa(hours)} ساعت و {fa(mins)} دقیقه پیش"


def score_board_text(g: dict) -> str:
    red = g["score"]["red"]
    blue = g["score"]["blue"]
    hand_num = len(g["hands"]) + 1
    hakem_line = f" • حاکم: {TEAM_COLOR[g['hakem']]}" if g["hands"] else ""
    last_evt = g.get("last_event_at") or g.get("started_at") or ""
    update_line = ""
    if last_evt:
        rel = _relative_time(last_evt)
        if rel:
            label = "آخرین دست" if g["hands"] else "شروع بازی"
            update_line = f"\n🕐 {label}: {rel}"
    return (
        "🃏 <b>بازی در جریان</b>\n"
        f"\n🔴 قرمز  <b>{fa(red)} — {fa(blue)}</b>  آبی 🔵\n"
        "━━━━━━━━━━━━━━━━━\n"
        f"دست {fa(hand_num)}{hakem_line}\n"
        f"{_last_hand_line(g)}"
        f"{update_line}"
    )


def end_game_text(record: dict, today: dict, state: dict | None = None) -> str:
    winner = record["winner"]
    fs = record["final_score"]

    duration = _format_duration(record.get("started_at", ""), record.get("ended_at", ""))
    duration_line = f"\n⏱ مدت بازی: {duration}" if duration else ""

    today_line = (
        f"🔴 {fa(today['today_wins']['red'])} — {fa(today['today_wins']['blue'])} 🔵"
    )

    total_line = (
        f"🔴 {fa(today['total_wins']['red'])} — {fa(today['total_wins']['blue'])} 🔵"
    )
    # The normal/hakem split below already accounts for every kot, so we don't
    # repeat an undifferentiated total line here.
    split_line = _split_kot_line(today.get("split_kots"))

    extras = ""
    if state is not None:
        lifetime = lifetime_extras_text(state)
        pct = end_game_percentile_text(record, state)
        extra_lines = [s for s in (lifetime, pct) if s]
        if extra_lines:
            extras = "\n\n" + "\n\n".join(extra_lines)

    return (
        "🏆 <b>بازی تموم شد!</b>\n"
        f"{TEAM_LABEL[winner]} برنده 🎉\n"
        "\n🎯 <b>نتیجه:</b>\n"
        f"🔴 {fa(fs['red'])} — {fa(fs['blue'])} 🔵"
        f"{duration_line}\n"
        f"\n📅 <b>امروز ({today['today_date']}):</b>\n"
        f"{today_line}\n"
        "\n🏆 <b>مجموع کل:</b>\n"
        f"{total_line}{split_line}"
        f"{extras}"
    )


def _format_hours_minutes(total_seconds: float) -> str:
    s = int(total_seconds)
    h = s // 3600
    m = (s % 3600) // 60
    if h == 0:
        return f"{fa(m)} دقیقه"
    if m == 0:
        return f"{fa(h)} ساعت"
    return f"{fa(h)} ساعت و {fa(m)} دقیقه"


def lifetime_extras_text(state: dict) -> str:
    """Total games / total hands / total hours. Used at end-of-game and in /stats."""
    from game import lifetime_stats

    ls = lifetime_stats(state)
    lines = []
    if ls["games"] > 0:
        lines.append(f"🃏 کل بازی‌ها: {fa(ls['games'])}")
    if ls["hands"] > 0:
        lines.append(f"🎴 کل دست‌ها: {fa(ls['hands'])}")
    if ls["total_seconds"] > 0:
        lines.append(f"⏱ کل زمان بازی: {_format_hours_minutes(ls['total_seconds'])}")
        if ls.get("avg_game_seconds"):
            lines.append(f"⏱ میانگین هر بازی: {_format_hours_minutes(ls['avg_game_seconds'])}")
    if not lines:
        return ""
    return "<b>📈 مجموع تاریخچه</b>\n" + "\n".join(lines)


def end_game_percentile_text(record: dict, state: dict) -> str:
    """One-line speed percentile for the just-finished game, in plain language.
    Empty if not enough data or game pre-dates the cutoff."""
    from datetime import datetime
    from game import lifetime_stats, duration_percentile_faster
    import config as _cfg

    try:
        start = datetime.fromisoformat(record["started_at"])
        end = datetime.fromisoformat(record["ended_at"])
    except (KeyError, TypeError, ValueError):
        return ""
    if start < _cfg.STATS_DURATION_CUTOFF:
        return ""
    dur = (end - start).total_seconds()
    durs = lifetime_stats(state)["durations_after_cutoff"]
    if len(durs) < 5:
        return ""
    pct = duration_percentile_faster(durs, dur)
    if pct is None:
        return ""
    # plain-language phrasing
    if pct >= 80:
        flavor = "🚀 سریع‌ترین‌ها"
    elif pct >= 50:
        flavor = "⏩ بالاتر از میانگین (سریع‌تر)"
    elif pct >= 20:
        flavor = "🐢 آروم‌تر از میانگین"
    else:
        flavor = "🐌 از طولانی‌ترین‌ها"
    return f"🏁 این بازی از {fa(pct)}٪ بازی‌ها سریع‌تر تموم شد — {flavor}"


def _split_kot_line(split: dict | None) -> str:
    if not split:
        return ""
    n = split["normal"]
    h = split["hakem"]
    if not (n["red"] or n["blue"] or h["red"] or h["blue"]):
        return ""
    return (
        f"\n⚡ کت عادی: 🔴×{fa(n['red'])}  🔵×{fa(n['blue'])}"
        f"\n👑⚡ حاکم‌کت: 🔴×{fa(h['red'])}  🔵×{fa(h['blue'])}"
    )


def stats_text(state: dict) -> str:
    from game import daily_breakdown, totals, game_day, now_tz, split_kot_totals

    by = daily_breakdown(state)
    if not by:
        return "📊 هنوز بازی‌ای ثبت نشده.\n`/newgame` بزن شروع کنیم!"

    today = game_day(now_tz())
    days = sorted(by.keys(), reverse=True)
    lines = ["📊 <b>تاریخچه</b>\n"]
    for d in days:
        slot = by[d]
        title = "📅 امروز" if d == today else "📅"
        line = f"{title} {d}\n🔴 {fa(slot['red'])} — {fa(slot['blue'])} 🔵"
        if slot["kots"]["red"] or slot["kots"]["blue"]:
            line += f"  •  ⚡ 🔴×{fa(slot['kots']['red'])}  🔵×{fa(slot['kots']['blue'])}"
        lines.append(line)

    total_w, _ = totals(state)
    lines.append("\n━━━━━━━━━━━━━━━━━")
    lines.append(
        f"🏆 <b>مجموع کل:</b> 🔴 {fa(total_w['red'])} — {fa(total_w['blue'])} 🔵"
    )
    # The normal/hakem split already covers every kot, so no undifferentiated total line.
    split_line = _split_kot_line(split_kot_totals(state))
    if split_line:
        lines.append(split_line.lstrip("\n"))
    extras = lifetime_extras_text(state)
    if extras:
        lines.append("\n" + extras)
    return "\n".join(lines)


def help_text() -> str:
    return (
        "🃏 <b>ربات حکم</b>\n\n"
        "<b>دستورات:</b>\n"
        "• /newgame — شروع بازی جدید\n"
        "• /score — نمایش امتیاز فعلی\n"
        "• /stats — تاریخچه بازی‌ها\n"
        "• /undo — بازگشت آخرین دست\n"
        "• /endgame — پایان دستی بازی\n"
        "• /import — ثبت نتیجه روز قدیم\n"
        "• /help — همین راهنما\n\n"
        "<b>قواعد امتیاز:</b>\n"
        "• برد عادی: +۱\n"
        "• کت تیم حاکم: +۲\n"
        "• کت توسط حریف (حاکم کت شد): +۳\n"
        "• سقف بازی: ۷ امتیاز\n\n"
        "<b>حاکم:</b> اولش رندوم انتخاب میشه. بعدش برنده‌ی هر دست حاکم دست بعد میشه.\n\n"
        "<b>روز بازی:</b> هر چی قبل از ۶ صبح ثبت بشه، روز قبل لاگ میخوره (برای شب‌بازی‌های طولانی).\n\n"
        "<b>Undo:</b> داخل بازی همیشه فعاله. بعد از پایان بازی، تا ۵ دقیقه میتونی برگردونی.\n\n"
        "<b>ایمپورت بازی قدیم:</b>\n"
        "<code>/import YYYY-MM-DD red-blue [redKots-blueKots]</code>\n"
        "مثال: <code>/import 2026-04-15 3-1 1-0</code>"
    )


def start_text() -> str:
    return (
        "🃏 سلام! ربات حکم آماده‌ست.\n"
        "/newgame بزن شروع کنیم.\n"
        "/help برای راهنما."
    )


def confirm_newgame_text() -> str:
    return "⚠️ یه بازی در جریانه. رهاش کنم و جدید شروع کنم؟"


def confirm_endgame_text(g: dict) -> str:
    return (
        "⚠️ بازی فعلی رو دستی تموم کنم؟\n"
        f"امتیاز فعلی: 🔴 {fa(g['score']['red'])} — {fa(g['score']['blue'])} 🔵\n"
        "(بدون ثبت در تاریخچه)"
    )


def import_help_text() -> str:
    return (
        "📥 <b>ایمپورت بازی قدیم</b>\n\n"
        "<code>/import YYYY-MM-DD red-blue [redKots-blueKots]</code>\n\n"
        "مثال‌ها:\n"
        "<code>/import 2026-04-15 3-1</code>\n"
        "<code>/import 2026-04-15 3-1 1-0</code>"
    )


def import_success_text(day: str, r: int, b: int, rk: int, bk: int, replaced: bool) -> str:
    head = "✅ ثبت شد" if not replaced else "♻️ جایگزین شد"
    line = f"{head} • {day}\n🔴 {fa(r)} — {fa(b)} 🔵"
    if rk or bk:
        line += f"  •  ⚡ 🔴×{fa(rk)}  🔵×{fa(bk)}"
    return line


def import_conflict_text(day: str) -> str:
    return f"⚠️ روز <b>{day}</b> قبلاً ثبت شده. اضافه کنم یا جایگزین؟"


def import_invalid_text() -> str:
    return "❌ فرمت اشتباهه. /import بدون آرگومان بزن راهنما ببین."


def no_active_game() -> str:
    return "بازی فعالی نیست. /newgame بزن شروع کنیم."


def cant_undo() -> str:
    return "دستی برای undo نیست!"


def cant_undo_ended() -> str:
    return "وقت undo بازی تموم شده (۵ دقیقه گذشته)."


def stale_button() -> str:
    return "این دکمه دیگه فعال نیست."


def kot_team_prompt() -> str:
    return "⚡ <b>کدوم تیم کت کرد؟</b>"


def kot_first_hand_prompt() -> str:
    return (
        "⚡ <b>کت دست اول</b>\n"
        "چون هنوز هیچ دستی ثبت نشده، باید بگی حاکم کی بود و کی کت کرد:"
    )
