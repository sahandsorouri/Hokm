# Hokm Bot

ربات تلگرام برای ثبت نتایج بازی **حکم** در گروه‌ها. تیم‌های ثابت 🔴 قرمز و 🔵 آبی، با ردیابی خودکار حاکم و کت.

## امکانات

- ثبت برد عادی، کت، و undo سریع
- روز بازی هوشمند: قبل از ۶ صبح = روز قبل (برای شب‌بازی‌های طولانی)
- تاریخچه روزانه + مجموع کل
- ایمپورت بازی‌های قدیم با یک خط
- پایداری: ذخیره روی JSON با backup خودکار، asyncio lock، systemd auto-restart

## دستورات

| دستور | کار |
|---|---|
| `/newgame` | شروع بازی جدید (تا ۷ امتیاز) |
| `/score` | فرستادن مجدد score board |
| `/stats` | تاریخچه روزانه + مجموع |
| `/undo` | بازگشت آخرین دست (تا ۵ دقیقه پس از پایان بازی هم کار میکنه) |
| `/endgame` | پایان دستی بازی بدون ثبت در تاریخچه |
| `/import YYYY-MM-DD red-blue [redKots-blueKots]` | ثبت نتیجه روز قدیم |
| `/help` | راهنما |

### مثال ایمپورت

```
/import 2026-04-15 3-1
/import 2026-04-15 3-1 1-0
```

## قواعد امتیاز

- برد عادی: **+۱**
- کت توسط تیم حاکم: **+۲**
- کت توسط تیم غیر حاکم (حاکم کت شد): **+۳**
- سقف بازی: **۷ امتیاز**
- حاکم اولیه: random — بعدش برنده‌ی هر دست حاکم میشه

## نصب روی سرور

```bash
ssh user@server
cd ~
REPO_URL=https://github.com/<you>/Hokm.git \
  /tmp/deploy.sh   # یا بعد از clone اولیه:

git clone https://github.com/<you>/Hokm.git hokm-bot
cd hokm-bot
./deploy/deploy.sh           # بار اول .env درست میشه
nano .env                    # BOT_TOKEN رو بذار
./deploy/deploy.sh           # دوباره اجرا — service فعال میشه
```

پس از نصب:

```bash
sudo systemctl status hokm-bot
tail -f ~/hokm-bot/data/bot.log
```

## ساختار پروژه

```
.
├── main.py        # entry point
├── handlers.py    # command + callback handlers
├── game.py        # منطق امتیاز/حاکم/کت/undo
├── storage.py     # JSON + lock + backup
├── keyboards.py   # inline keyboards
├── messages.py    # متن‌های فارسی
├── config.py      # env + constants
├── deploy/
│   ├── hokm-bot.service
│   └── deploy.sh
├── requirements.txt
└── data/          # JSON state per chat (gitignored)
```

## دسترسی‌های لازم در گروه

برای تجربه‌ی بهتر، ربات رو ادمین کن با دسترسی **Delete Messages** تا پیام‌های موقت رو پاک کنه. اگه ادمین نباشه هم کار میکنه ولی پیام‌های اضافی پاک نمیشن.

## توسعه local

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
echo "BOT_TOKEN=your-token" > .env
python main.py
```
