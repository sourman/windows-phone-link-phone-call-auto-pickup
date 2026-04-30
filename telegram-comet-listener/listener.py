"""
Windows service that long-polls Telegram for COMET triggers and runs the
call + comet voice sequence (same as queue-watcher).

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
import subprocess
import sys
from pathlib import Path

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, ContextTypes, MessageHandler, filters

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

HARDCODED_PHONE = "01280043725"

REPO_ROOT = Path(__file__).resolve().parent.parent
STEP2_SCRIPT = REPO_ROOT / "enter_number_2.ahk"
STEP3_SCRIPT = REPO_ROOT / "open-comet-voice.ahk"
LOG_FILE = Path(__file__).resolve().parent / "telegram-watcher.log"
TARGET_URL_FILE = REPO_ROOT / "target_url.txt"
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


def find_autohotkey_v2_exe() -> Path | None:
    for env in ("ProgramFiles", "ProgramFiles(x86)"):
        base = os.environ.get(env)
        if not base:
            continue
        candidate = Path(base) / "AutoHotkey" / "v2" / "AutoHotkey64.exe"
        if candidate.is_file():
            return candidate
    override = os.environ.get("AUTOHOTKEY_V2_EXE", "").strip()
    if override:
        p = Path(override)
        if p.is_file():
            return p
    return None


def read_target_url() -> str | None:
    """Read the target URL from target_url.txt. Returns None if file is missing or empty."""
    if not TARGET_URL_FILE.exists():
        log.warning("target_url.txt not found at %s — Comet will open blank", TARGET_URL_FILE)
        return None
    url = TARGET_URL_FILE.read_text().strip()
    if not url:
        log.warning("target_url.txt is empty — Comet will open blank")
        return None
    return url


def parse_comet_text(text: str) -> bool:
    """Returns True if the message is a COMET trigger."""
    s = text.strip()
    return bool(re.search(r"\bCOMET\b", s, re.IGNORECASE))


def require_scripts() -> None:
    if not STEP2_SCRIPT.is_file():
        raise RuntimeError(f"Script not found: {STEP2_SCRIPT}")
    if not STEP3_SCRIPT.is_file():
        raise RuntimeError(f"Script not found: {STEP3_SCRIPT}")


def run_call_then_comet(exe: Path, phone: str, target_url: str | None) -> tuple[int, int]:
    r2 = subprocess.run(
        [str(exe), str(STEP2_SCRIPT), phone],
        cwd=str(REPO_ROOT),
    )
    s3_args = [str(exe), str(STEP3_SCRIPT)]
    if target_url:
        s3_args.append(target_url)
    r3 = subprocess.run(s3_args, cwd=str(REPO_ROOT))
    return r2.returncode, r3.returncode


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

    exe = find_autohotkey_v2_exe()
    if not exe:
        log.error(
            "AutoHotkey v2 not found (Program Files\\AutoHotkey\\v2\\AutoHotkey64.exe or AUTOHOTKEY_V2_EXE)"
        )
        return

    try:
        require_scripts()
    except RuntimeError as e:
        log.error("%s", e)
        return

    phone = HARDCODED_PHONE
    target_url = read_target_url()
    log.info("COMET triggered — calling %s then comet (url=%s)", phone, target_url or "blank")

    try:
        rc2, rc3 = await asyncio.to_thread(run_call_then_comet, exe, phone, target_url)
        log.info("enter_number_2 exit=%s open-comet-voice exit=%s", rc2, rc3)
    except Exception as e:
        log.exception("AHK sequence failed: %s", e)


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

    log.info("Telegram watcher started — polling COMET -> %s then %s", STEP2_SCRIPT.name, STEP3_SCRIPT.name)
    try:
        app.run_polling(allowed_updates=Update.ALL_TYPES)
    except Exception:
        log.exception("run_polling crashed, exiting")
        sys.exit(1)


if __name__ == "__main__":
    main()
