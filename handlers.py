import asyncio
import logging
import re

from telegram import Update
from telegram.constants import ParseMode
from telegram.error import BadRequest, TelegramError
from telegram.ext import ContextTypes

import config
import game
import keyboards as kb
import messages as msg
import storage

log = logging.getLogger("hokm.handlers")

IMPORT_RE = re.compile(
    r"^(?P<date>\d{4}-\d{2}-\d{2})\s+(?P<r>\d+)-(?P<b>\d+)(?:\s+(?P<rk>\d+)-(?P<bk>\d+))?$"
)


# ── tiny helpers ───────────────────────────────────────────────────────────────

async def _safe_delete(bot, chat_id: int, message_id: int):
    try:
        await bot.delete_message(chat_id=chat_id, message_id=message_id)
    except TelegramError:
        pass


async def _delete_after(bot, chat_id: int, message_id: int, delay: int):
    await asyncio.sleep(delay)
    await _safe_delete(bot, chat_id, message_id)


def _schedule_delete(bot, chat_id: int, message_id: int, delay: int = config.EPHEMERAL_DELETE_SECONDS):
    asyncio.create_task(_delete_after(bot, chat_id, message_id, delay))


async def _delete_user_message(update: Update):
    if update.message:
        try:
            await update.message.delete()
        except TelegramError:
            pass


async def _ephemeral(context: ContextTypes.DEFAULT_TYPE, chat_id: int, text: str):
    try:
        m = await context.bot.send_message(chat_id=chat_id, text=text, parse_mode=ParseMode.HTML)
        _schedule_delete(context.bot, chat_id, m.message_id)
    except TelegramError as e:
        log.warning("ephemeral send failed: %s", e)


async def _send_scoreboard_fresh(context, chat_id: int, state: dict):
    """Send a new scoreboard at the bottom; delete the old one if any."""
    g = state["active_game"]
    old_id = g.get("score_board_message_id")
    if old_id:
        await _safe_delete(context.bot, chat_id, old_id)
    m = await context.bot.send_message(
        chat_id=chat_id,
        text=msg.score_board_text(g),
        reply_markup=kb.main_kb(),
        parse_mode=ParseMode.HTML,
    )
    g["score_board_message_id"] = m.message_id
    storage.save(chat_id, state)


async def _edit_scoreboard(context, chat_id: int, state: dict, *,
                           extra_text: str = "", reply_markup=None):
    g = state["active_game"]
    if not g:
        return
    msg_id = g.get("score_board_message_id")
    text = msg.score_board_text(g)
    if extra_text:
        text = text + "\n\n" + extra_text
    if reply_markup is None:
        reply_markup = kb.main_kb()
    if not msg_id:
        await _send_scoreboard_fresh(context, chat_id, state)
        return
    try:
        await context.bot.edit_message_text(
            chat_id=chat_id, message_id=msg_id,
            text=text, reply_markup=reply_markup,
            parse_mode=ParseMode.HTML,
        )
    except BadRequest as e:
        if "not modified" in str(e).lower():
            return
        await _send_scoreboard_fresh(context, chat_id, state)


# ── commands ───────────────────────────────────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _delete_user_message(update)
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=msg.start_text(),
        parse_mode=ParseMode.HTML,
    )


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _delete_user_message(update)
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=msg.help_text(),
        parse_mode=ParseMode.HTML,
    )


async def cmd_newgame(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    await _delete_user_message(update)
    async with storage.lock_for(chat_id):
        state = storage.load(chat_id)
        if state.get("active_game"):
            m = await context.bot.send_message(
                chat_id=chat_id,
                text=msg.confirm_newgame_text(),
                reply_markup=kb.confirm_kb("newgame"),
                parse_mode=ParseMode.HTML,
            )
            return
        await _start_new_game(context, chat_id, state)


async def _start_new_game(context, chat_id: int, state: dict):
    state["last_ended_game"] = None
    state["active_game"] = game.new_game()
    await _send_scoreboard_fresh(context, chat_id, state)


async def cmd_score(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    await _delete_user_message(update)
    async with storage.lock_for(chat_id):
        state = storage.load(chat_id)
        if not state.get("active_game"):
            await _ephemeral(context, chat_id, msg.no_active_game())
            return
        await _send_scoreboard_fresh(context, chat_id, state)


async def cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    await _delete_user_message(update)
    state = storage.load(chat_id)
    await context.bot.send_message(
        chat_id=chat_id,
        text=msg.stats_text(state),
        parse_mode=ParseMode.HTML,
    )


async def cmd_undo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    await _delete_user_message(update)
    async with storage.lock_for(chat_id):
        state = storage.load(chat_id)
        await _do_undo(context, chat_id, state)


async def _do_undo(context, chat_id: int, state: dict):
    g = state.get("active_game")
    if g and game.can_undo(g):
        game.undo_last(g)
        storage.save(chat_id, state)
        await _edit_scoreboard(context, chat_id, state)
        return
    if game.can_undo_ended(state):
        if game.restore_last_game(state):
            storage.save(chat_id, state)
            await _send_scoreboard_fresh(context, chat_id, state)
            return
    await _ephemeral(context, chat_id, msg.cant_undo())


async def cmd_endgame(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    await _delete_user_message(update)
    async with storage.lock_for(chat_id):
        state = storage.load(chat_id)
        g = state.get("active_game")
        if not g:
            await _ephemeral(context, chat_id, msg.no_active_game())
            return
        await context.bot.send_message(
            chat_id=chat_id,
            text=msg.confirm_endgame_text(g),
            reply_markup=kb.confirm_kb("endgame"),
            parse_mode=ParseMode.HTML,
        )


async def cmd_import(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    text = (update.message.text or "").strip() if update.message else ""
    await _delete_user_message(update)
    args = text.split(maxsplit=1)
    if len(args) < 2:
        await context.bot.send_message(
            chat_id=chat_id, text=msg.import_help_text(), parse_mode=ParseMode.HTML
        )
        return
    payload = args[1].strip()
    m = IMPORT_RE.match(payload)
    if not m:
        await _ephemeral(context, chat_id, msg.import_invalid_text())
        return
    day = m.group("date")
    r, b = int(m.group("r")), int(m.group("b"))
    rk = int(m.group("rk") or 0)
    bk = int(m.group("bk") or 0)
    async with storage.lock_for(chat_id):
        state = storage.load(chat_id)
        if game.has_day(state, day):
            context.chat_data["pending_import"] = {
                "day": day, "r": r, "b": b, "rk": rk, "bk": bk,
            }
            await context.bot.send_message(
                chat_id=chat_id,
                text=msg.import_conflict_text(day),
                reply_markup=kb.import_conflict_kb(day),
                parse_mode=ParseMode.HTML,
            )
            return
        game.add_imported_day(state, day, r, b, rk, bk, replace=False)
        storage.save(chat_id, state)
        await context.bot.send_message(
            chat_id=chat_id,
            text=msg.import_success_text(day, r, b, rk, bk, replaced=False),
            parse_mode=ParseMode.HTML,
        )


# ── callbacks ──────────────────────────────────────────────────────────────────

async def on_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if not q:
        return
    data = q.data or ""
    chat_id = q.message.chat.id

    async with storage.lock_for(chat_id):
        state = storage.load(chat_id)

        if data.startswith("win:"):
            await _cb_win(q, context, chat_id, state, data.split(":", 1)[1])
        elif data == "kot":
            await _cb_kot_open(q, context, chat_id, state)
        elif data.startswith("kotwin:"):
            await _cb_kot_choose(q, context, chat_id, state, data.split(":", 1)[1])
        elif data == "undo":
            await q.answer()
            await _do_undo(context, chat_id, state)
        elif data == "undo_ended":
            await _cb_undo_ended(q, context, chat_id, state)
        elif data == "newgame":
            await _cb_newgame(q, context, chat_id, state)
        elif data == "stats":
            await q.answer()
            await context.bot.send_message(
                chat_id=chat_id,
                text=msg.stats_text(state),
                parse_mode=ParseMode.HTML,
            )
        elif data.startswith("confirm:"):
            await _cb_confirm(q, context, chat_id, state, data.split(":", 1)[1])
        elif data.startswith("imp:"):
            await _cb_import(q, context, chat_id, state, data)
        else:
            await q.answer(msg.stale_button())


async def _cb_win(q, context, chat_id, state, team):
    g = state.get("active_game")
    if not g or game.game_ended(g):
        await q.answer(msg.stale_button())
        return
    if team not in ("red", "blue"):
        await q.answer()
        return
    pts = game.add_hand(g, team, kot=False)
    await q.answer(f"+{pts} {msg.TEAM_NAME[team]}")
    if game.game_ended(g):
        await _finish_game(context, chat_id, state)
    else:
        storage.save(chat_id, state)
        await _edit_scoreboard(context, chat_id, state)


async def _cb_kot_open(q, context, chat_id, state):
    g = state.get("active_game")
    if not g or game.game_ended(g):
        await q.answer(msg.stale_button())
        return
    await q.answer()
    await _edit_scoreboard(
        context, chat_id, state,
        extra_text=msg.kot_team_prompt(),
        reply_markup=kb.kot_kb(),
    )


async def _cb_kot_choose(q, context, chat_id, state, choice):
    g = state.get("active_game")
    if not g or game.game_ended(g):
        await q.answer(msg.stale_button())
        return
    if choice == "cancel":
        await q.answer()
        await _edit_scoreboard(context, chat_id, state)
        return
    if choice not in ("red", "blue"):
        await q.answer()
        return
    pts = game.add_hand(g, choice, kot=True)
    await q.answer(f"⚡ +{pts} {msg.TEAM_NAME[choice]}")
    if game.game_ended(g):
        await _finish_game(context, chat_id, state)
    else:
        storage.save(chat_id, state)
        await _edit_scoreboard(context, chat_id, state)


async def _cb_undo_ended(q, context, chat_id, state):
    if not game.can_undo_ended(state):
        await q.answer(msg.cant_undo_ended())
        return
    if game.restore_last_game(state):
        storage.save(chat_id, state)
        await q.answer("بازی برگشت")
        try:
            await q.message.delete()
        except TelegramError:
            pass
        await _send_scoreboard_fresh(context, chat_id, state)
    else:
        await q.answer(msg.cant_undo_ended())


async def _cb_newgame(q, context, chat_id, state):
    if state.get("active_game"):
        await q.answer()
        await context.bot.send_message(
            chat_id=chat_id,
            text=msg.confirm_newgame_text(),
            reply_markup=kb.confirm_kb("newgame"),
            parse_mode=ParseMode.HTML,
        )
        return
    await q.answer()
    try:
        await q.message.edit_reply_markup(reply_markup=None)
    except TelegramError:
        pass
    await _start_new_game(context, chat_id, state)


async def _cb_confirm(q, context, chat_id, state, action):
    try:
        await q.message.delete()
    except TelegramError:
        pass
    if action == "cancel":
        await q.answer("لغو شد")
        return
    if action == "newgame":
        if state.get("active_game"):
            old_id = state["active_game"].get("score_board_message_id")
            if old_id:
                await _safe_delete(context.bot, chat_id, old_id)
            state["active_game"] = None
        await q.answer("بازی جدید!")
        await _start_new_game(context, chat_id, state)
        return
    if action == "endgame":
        if state.get("active_game"):
            old_id = state["active_game"].get("score_board_message_id")
            if old_id:
                await _safe_delete(context.bot, chat_id, old_id)
            state["active_game"] = None
            state["last_ended_game"] = None
            storage.save(chat_id, state)
        await q.answer("بازی تموم شد")
        await _ephemeral(context, chat_id, "بازی فعلی بدون ثبت تموم شد.")


async def _cb_import(q, context, chat_id, state, data):
    parts = data.split(":")
    if len(parts) < 2:
        await q.answer()
        return
    op = parts[1]
    pending = context.chat_data.get("pending_import")
    try:
        await q.message.delete()
    except TelegramError:
        pass
    if op == "cancel":
        context.chat_data.pop("pending_import", None)
        await q.answer("لغو شد")
        return
    if not pending:
        await q.answer(msg.stale_button())
        return
    day = pending["day"]
    r, b, rk, bk = pending["r"], pending["b"], pending["rk"], pending["bk"]
    replaced = (op == "rep")
    game.add_imported_day(state, day, r, b, rk, bk, replace=replaced)
    storage.save(chat_id, state)
    context.chat_data.pop("pending_import", None)
    await q.answer("ثبت شد")
    await context.bot.send_message(
        chat_id=chat_id,
        text=msg.import_success_text(day, r, b, rk, bk, replaced),
        parse_mode=ParseMode.HTML,
    )


async def _finish_game(context, chat_id: int, state: dict):
    g = state["active_game"]
    record = game.archive_game(state)
    today = game.today_summary(state)
    storage.save(chat_id, state)
    sb_id = g.get("score_board_message_id")
    if sb_id:
        try:
            await context.bot.edit_message_text(
                chat_id=chat_id, message_id=sb_id,
                text=msg.score_board_text(g),
                reply_markup=None,
                parse_mode=ParseMode.HTML,
            )
        except TelegramError:
            pass
    end_msg = await context.bot.send_message(
        chat_id=chat_id,
        text=msg.end_game_text(record, today),
        reply_markup=kb.end_kb(),
        parse_mode=ParseMode.HTML,
    )
    if state.get("last_ended_game"):
        state["last_ended_game"]["end_message_id"] = end_msg.message_id
        storage.save(chat_id, state)


async def on_error(update: object, context: ContextTypes.DEFAULT_TYPE):
    log.exception("handler error: %s", context.error)
