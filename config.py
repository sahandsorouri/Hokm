import os
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.environ.get("BOT_TOKEN", "").strip()
if not BOT_TOKEN:
    raise SystemExit("BOT_TOKEN env var is required (put it in .env)")

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

TZ = ZoneInfo("Asia/Tehran")
DAY_CUTOFF_HOUR = 6
UNDO_WINDOW_SECONDS = 300
WIN_TARGET = 7
EPHEMERAL_DELETE_SECONDS = 5

# Duration averages / percentiles only consider games started on/after this moment.
# Earlier games predate the bot's reliable timestamping. 2026-05-07 22:00 Dubai (UTC+4)
# == 2026-05-07 21:30 Tehran (UTC+3:30).
STATS_DURATION_CUTOFF = datetime.fromisoformat("2026-05-07T21:30:00+03:30")

# Live scoreboard auto-refresh interval (used in step 5).
LIVE_REFRESH_SECONDS = 60

# Legacy kots (logged before normal/hakem split tracking) are estimated: this
# fraction is assumed to have been hakem-kots (+3), the rest normal kots (+2).
LEGACY_HAKEM_KOT_RATIO = 0.3
