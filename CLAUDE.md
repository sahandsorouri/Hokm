# Hokm Bot

ربات تلگرام برای ثبت نتایج بازی حکم.

## Stack
- Python 3.10+ (تست‌شده روی 3.11)
- python-telegram-bot v21 (async)
- python-dotenv
- ذخیره‌سازی: فایل JSON به ازای هر `chat_id` در `data/`

## Conventions
- همه پیام‌های ربات فارسی، با اعداد فارسی
- Timezone: `Asia/Tehran`
- روز بازی: قبل از ۶ صبح = روز قبل (cutoff در `config.DAY_CUTOFF_HOUR`)
- Undo window پس از پایان بازی: ۵ دقیقه (`config.UNDO_WINDOW_SECONDS`)
- سقف امتیاز بازی: ۷ (`config.WIN_TARGET`)
- پیام‌های موقت ربات بعد از ۵ ثانیه حذف میشن
- Lock کانکارنسی: `asyncio.Lock` per chat_id

## Scoring
- برد عادی: +۱
- کت تیم حاکم: +۲
- کت تیم غیر حاکم (حاکم کت شد): +۳
- حاکم اولیه‌ی هر بازی: random
- حاکم بعدی: برنده‌ی هر دست

## Files
- `main.py` — entry point، register handler ها
- `handlers.py` — همه command و callback handler ها
- `game.py` — منطق pure (امتیاز، حاکم، کت، undo)
- `storage.py` — load/save JSON با backup و lock
- `keyboards.py` — تمام inline keyboard ها
- `messages.py` — متن‌های فارسی + helper اعداد فارسی
- `config.py` — env و constant ها
- `data/` — JSON state per chat (gitignored)
- `deploy/` — systemd unit و deploy script

## Commands
`/start /help /newgame /score /stats /endgame /undo /import`

## Import format
```
/import YYYY-MM-DD red-blue [redKots-blueKots]
/import 2026-04-15 3-1 1-0
/import 2026-04-15 3-1
```

## Deploy
روی سرور با systemd. فایل `deploy/hokm-bot.service` و `deploy/deploy.sh`.
