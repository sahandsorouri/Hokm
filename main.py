import logging

from telegram.ext import Application, CallbackQueryHandler, CommandHandler

import config
import handlers

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger("hokm")


def build_app() -> Application:
    app = Application.builder().token(config.BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", handlers.cmd_start))
    app.add_handler(CommandHandler("help", handlers.cmd_help))
    app.add_handler(CommandHandler("newgame", handlers.cmd_newgame))
    app.add_handler(CommandHandler("score", handlers.cmd_score))
    app.add_handler(CommandHandler("stats", handlers.cmd_stats))
    app.add_handler(CommandHandler("undo", handlers.cmd_undo))
    app.add_handler(CommandHandler("endgame", handlers.cmd_endgame))
    app.add_handler(CommandHandler("import", handlers.cmd_import))
    app.add_handler(CallbackQueryHandler(handlers.on_callback))
    app.add_error_handler(handlers.on_error)
    return app


def main():
    log.info("Hokm bot starting…")
    app = build_app()
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
