_FA_DIGITS = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")


def fa(n) -> str:
    return str(n).translate(_FA_DIGITS)


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


def score_board_text(g: dict) -> str:
    red = g["score"]["red"]
    blue = g["score"]["blue"]
    hand_num = len(g["hands"]) + 1
    hakem_line = f" • حاکم: {TEAM_COLOR[g['hakem']]}" if g["hands"] else ""
    return (
        "🃏 <b>بازی در جریان</b>\n"
        f"\n🔴 قرمز  <b>{fa(red)} — {fa(blue)}</b>  آبی 🔵\n"
        "━━━━━━━━━━━━━━━━━\n"
        f"دست {fa(hand_num)}{hakem_line}\n"
        f"{_last_hand_line(g)}"
    )


def end_game_text(record: dict, today: dict) -> str:
    winner = record["winner"]
    fs = record["final_score"]

    today_line = (
        f"🔴 {fa(today['today_wins']['red'])} — {fa(today['today_wins']['blue'])} 🔵"
    )

    total_line = (
        f"🔴 {fa(today['total_wins']['red'])} — {fa(today['total_wins']['blue'])} 🔵"
    )
    tlk = today["total_kots"]
    total_kot_line = ""
    if tlk["red"] or tlk["blue"]:
        total_kot_line = f"\n⚡ 🔴×{fa(tlk['red'])}  🔵×{fa(tlk['blue'])}"

    return (
        "🏆 <b>بازی تموم شد!</b>\n"
        f"{TEAM_LABEL[winner]} برنده 🎉\n"
        "\n🎯 <b>نتیجه:</b>\n"
        f"🔴 {fa(fs['red'])} — {fa(fs['blue'])} 🔵\n"
        f"\n📅 <b>امروز ({today['today_date']}):</b>\n"
        f"{today_line}\n"
        "\n🏆 <b>مجموع کل:</b>\n"
        f"{total_line}{total_kot_line}"
    )


def stats_text(state: dict) -> str:
    from game import daily_breakdown, totals, game_day, now_tz

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

    total_w, total_k = totals(state)
    lines.append("\n━━━━━━━━━━━━━━━━━")
    lines.append(
        f"🏆 <b>مجموع کل:</b> 🔴 {fa(total_w['red'])} — {fa(total_w['blue'])} 🔵"
    )
    if total_k["red"] or total_k["blue"]:
        lines.append(f"⚡ کت‌ها: 🔴×{fa(total_k['red'])}  🔵×{fa(total_k['blue'])}")
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
