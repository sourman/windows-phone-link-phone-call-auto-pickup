"""
Windows service that long-polls Telegram for COMET triggers and runs the
call + comet voice sequence via pyautomation (Python/PyAutoGUI).

Trigger: COMET message in a private chat.
Phone: hardcoded (matching queue-watcher behaviour).

Supports -NoConsole flag for headless Task Scheduler execution:
  python listener.py           → console + file logging
  python listener.py -NoConsole → file logging only

Env:
  TELEGRAM_BOT_TOKEN         — required, from @BotFather
  TELEGRAM_ALLOWED_USER_IDS  — optional, comma-separated numeric user ids (strongly recommended)
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
import sys
from pathlib import Path

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, ContextTypes, MessageHandler, filters

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from pyautomation import enter_number, open_comet_voice, read_target_url

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

HARDCODED_PHONE = "01280043725"

REPO_ROOT = Path(__file__).resolve().parent.parent
LOG_FILE = Path(__file__).resolve().parent / "telegram-watcher.log"
ENV_PATH = REPO_ROOT / ".env.local"

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

NO_CONSOLE = "-NoConsole" in sys.argv

logging.basicConfig(
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
    level=logging.INFO,
)

if NO_CONSOLE:
    # Remove default StreamHandler, add FileHandler only
    logging.root.handlers.clear()

file_handler = logging.FileHandler(str(LOG_FILE), encoding="utf-8")
file_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
logging.root.addHandler(file_handler)

log = logging.getLogger("telegram_watcher")

# Silence noisy httpx polling logs (every getUpdates request)
logging.getLogger("httpx").setLevel(logging.WARNING)


class _TokenRedactingFormatter(logging.Formatter):
    """Formatter that replaces the bot token in the final rendered log line."""

    def __init__(self, token: str, *args: object, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)
        self._token = token

    def format(self, record: logging.LogRecord) -> str:
        text = super().format(record)
        return text.replace(self._token, "***")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse_allowed_ids() -> frozenset[int] | None:
    raw = os.environ.get("TELEGRAM_ALLOWED_USER_IDS", "").strip()
    if not raw:
        return None
    ids: list[int] = []
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        ids.append(int(part))
    return frozenset(ids)


ALLOWED_USER_IDS = _parse_allowed_ids()


def parse_comet_text(text: str) -> bool:
    """Returns True if the message is a COMET trigger."""
    s = text.strip()
    return bool(re.search(r"\bCOMET\b", s))


def _run_comet_then_call(phone: str, target_url: str | None) -> tuple[bool, bool]:
    comet_ok = open_comet_voice(target_url)
    call_ok = enter_number(phone)
    return comet_ok, call_ok


# ---------------------------------------------------------------------------
# Telegram handler
# ---------------------------------------------------------------------------


async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.effective_message
    if not msg or not msg.text:
        return

    uid = update.effective_user.id if update.effective_user else None
    if ALLOWED_USER_IDS is not None:
        if uid is None or uid not in ALLOWED_USER_IDS:
            log.warning("Rejected message from user id %s (not in allowlist)", uid)
            return

    if not parse_comet_text(msg.text):
        log.info("Message received (not COMET): %s", msg.text[:40])
        return

    phone = HARDCODED_PHONE
    target_url = read_target_url()
    log.info("COMET triggered — launching comet (url=%s) then calling %s", target_url or "blank", phone)

    try:
        comet_ok, call_ok = await asyncio.to_thread(
            _run_comet_then_call, phone, target_url
        )
        log.info("open_comet_voice=%s enter_number=%s", comet_ok, call_ok)
    except Exception as e:
        log.exception("pyautomation sequence failed: %s", e)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    if ENV_PATH.is_file():
        load_dotenv(ENV_PATH)

    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        log.error("Set TELEGRAM_BOT_TOKEN")
        sys.exit(1)

    if ALLOWED_USER_IDS is None:
        log.warning(
            "TELEGRAM_ALLOWED_USER_IDS is unset — any user who messages your bot can trigger COMET. "
            "Set it to your numeric user id (from @userinfobot or similar)."
        )

    # Redact the token from ALL log output (httpx, telegram, etc.) at every level.
    redacting_fmt = _TokenRedactingFormatter(
        token, "%(asctime)s %(levelname)s %(name)s %(message)s"
    )
    for handler in logging.root.handlers:
        handler.setFormatter(redacting_fmt)

    app = Application.builder().token(token).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))

    log.info("Telegram watcher started — polling COMET -> pyautomation (open_comet_voice + enter_number)")
    try:
        app.run_polling(allowed_updates=Update.ALL_TYPES)
    except Exception:
        log.exception("run_polling crashed, exiting")
        sys.exit(1)


if __name__ == "__main__":
    main()
