import os
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
