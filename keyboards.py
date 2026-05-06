from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def main_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🔴 قرمز برد", callback_data="win:red"),
            InlineKeyboardButton("🔵 آبی برد", callback_data="win:blue"),
        ],
        [InlineKeyboardButton("⚡ کت!", callback_data="kot")],
        [
            InlineKeyboardButton("↩️ Undo", callback_data="undo"),
            InlineKeyboardButton("📊 آمار", callback_data="stats"),
        ],
    ])


def kot_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🔴 قرمز کت کرد", callback_data="kotwin:red"),
            InlineKeyboardButton("🔵 آبی کت کرد", callback_data="kotwin:blue"),
        ],
        [InlineKeyboardButton("← برگشت", callback_data="kotwin:cancel")],
    ])


def end_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 بازی جدید", callback_data="newgame")],
        [
            InlineKeyboardButton("↩️ Undo بازی", callback_data="undo_ended"),
            InlineKeyboardButton("📊 تاریخچه", callback_data="stats"),
        ],
    ])


def confirm_kb(action: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ آره", callback_data=f"confirm:{action}"),
            InlineKeyboardButton("❌ نه", callback_data="confirm:cancel"),
        ],
    ])


def import_conflict_kb(day: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("➕ اضافه کن", callback_data=f"imp:add:{day}"),
            InlineKeyboardButton("♻️ جایگزین", callback_data=f"imp:rep:{day}"),
        ],
        [InlineKeyboardButton("❌ لغو", callback_data="imp:cancel")],
    ])
