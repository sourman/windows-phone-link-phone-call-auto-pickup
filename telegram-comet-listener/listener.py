"""
Windows service that long-polls Telegram for COMET triggers and runs the
call + comet voice sequence via pyautomation (Python/PyAutoGUI).

Trigger: COMET message in a private chat.
Phone: hardcoded (matching queue-watcher behaviour).

Supports -NoConsole flag for headless Task Scheduler execution:
  python listener.py           -> console + file logging
  python listener.py -NoConsole -> file logging only

Env:
  TELEGRAM_BOT_TOKEN         — required, from @BotFather
  TELEGRAM_ALLOWED_USER_IDS  — optional, comma-separated numeric user ids (strongly recommended)
"""

from __future__ import annotations

import asyncio
import datetime
import logging
import logging.handlers
import os
import platform
import re
import signal
import subprocess
import sys
import threading
import time
import traceback
from pathlib import Path

# ---------------------------------------------------------------------------
# Dependency check — do this BEFORE anything else so we get clear errors
# ---------------------------------------------------------------------------

_DEPS: list[tuple[str, str]] = []

def _check_import(module_name: str) -> str:
    try:
        mod = __import__(module_name)
        version = getattr(mod, "__version__", "installed (no __version__)")
        _DEPS.append((module_name, version))
        return version
    except ImportError as e:
        _DEPS.append((module_name, f"MISSING: {e}"))
        return ""

_check_import("dotenv")
_check_import("telegram")
_check_import("httpx")
_check_import("apscheduler")

# Now import the ones we actually need — these will fail loudly if missing
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, ContextTypes, MessageHandler, filters

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
from pyautomation import enter_number, open_comet_voice, read_target_url

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

HARDCODED_PHONE = "01280043725"

LOG_FILE = Path(__file__).resolve().parent / "telegram-watcher.log"
HEARTBEAT_FILE = Path(__file__).resolve().parent / "heartbeat.txt"
LIVENESS_FILE = Path(__file__).resolve().parent / "liveness.txt"
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
    logging.root.handlers.clear()

file_handler = logging.handlers.RotatingFileHandler(
    str(LOG_FILE), maxBytes=10*1024*1024, backupCount=5, encoding="utf-8"
)
file_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
logging.root.addHandler(file_handler)

log = logging.getLogger("telegram_watcher")

logging.getLogger("httpx").setLevel(logging.WARNING)


class _TokenRedactingFormatter(logging.Formatter):
    def __init__(self, token: str, *args: object, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)
        self._token = token

    def format(self, record: logging.LogRecord) -> str:
        text = super().format(record)
        return text.replace(self._token, "***")


# ---------------------------------------------------------------------------
# Signal handler
# ---------------------------------------------------------------------------

_shutdown_requested = False
# Note: python-telegram-bot v20+ run_polling() installs its own SIGINT/SIGTERM
# handlers, so custom signal handlers here would be overridden during polling.
# We rely on the framework's signal handling instead.


# ---------------------------------------------------------------------------
# Uncaught exception handler
# ---------------------------------------------------------------------------

def _global_excepthook(exc_type: type, exc_value: BaseException, exc_tb: object) -> None:
    log.critical(
        "UNCAUGHT EXCEPTION: %s: %s\n%s",
        exc_type.__name__, exc_value,
        "".join(traceback.format_exception(exc_type, exc_value, exc_tb)),
    )


sys.excepthook = _global_excepthook


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

_comet_lock: asyncio.Lock | None = None
_last_wake_check = time.time()


def parse_comet_text(text: str) -> bool:
    s = text.strip()
    return bool(re.search(r"\bCOMET\b", s))


def _run_comet_then_call(phone: str, target_url: str | None) -> tuple[bool, bool]:
    # End any existing call before starting a new sequence
    try:
        from pyautomation import end_call
        end_call()
    except Exception as e:
        log.debug("end_call cleanup: %s (ok if no active call)", e)

    comet_ok = open_comet_voice(target_url)
    call_ok = enter_number(phone)
    return comet_ok, call_ok


# ---------------------------------------------------------------------------
# Startup diagnostics
# ---------------------------------------------------------------------------


def _log_startup_diagnostics() -> None:
    log.info("=== Telegram COMET Listener starting ===")
    log.info("Python: %s", sys.version)
    log.info("Platform: %s", platform.platform())
    log.info("CWD: %s", os.getcwd())
    log.info("Script: %s", __file__)
    log.info("REPO_ROOT: %s", REPO_ROOT)
    log.info("ENV_PATH: %s (exists=%s)", ENV_PATH, ENV_PATH.is_file())
    log.info("NO_CONSOLE: %s", NO_CONSOLE)
    log.info("PID: %d", os.getpid())

    log.info("--- Dependency versions ---")
    for name, ver in _DEPS:
        status = "OK" if "MISSING" not in ver else "MISSING"
        log.info("  %s: %s [%s]", name, ver, status)

    # Check APScheduler from already-collected _DEPS (don't call _check_import again)
    if not any(name == "apscheduler" and "MISSING" in ver for name, ver in _DEPS):
        log.warning(
            "APScheduler is NOT installed — job_queue heartbeat will be disabled. "
            "Install with: pip install APScheduler"
        )


# ---------------------------------------------------------------------------
# Startup self-test
# ---------------------------------------------------------------------------


async def _self_test(token: str) -> bool:
    """Verify bot token works before entering polling. Returns True on success."""
    from telegram import Bot
    try:
        async with Bot(token=token) as bot:
            me = await bot.get_me()
            log.info("Self-test PASSED — bot username: @%s (id=%d)", me.username, me.id)
            return True
    except Exception as e:
        log.error("Self-test FAILED — get_me() raised: %s", e)
        return False


# ---------------------------------------------------------------------------
# Telegram error handler (global)
# ---------------------------------------------------------------------------


async def _global_error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Catches ALL unhandled errors from the telegram framework."""
    log.error(
        "Global Telegram error handler triggered: %s\n%s",
        context.error,
        traceback.format_exception(
            type(context.error), context.error, context.error.__traceback__
        ) if context.error else "(no error object)",
    )


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

    if _comet_lock is not None and _comet_lock.locked():
        log.warning("COMET skipped — automation already in progress")
        return

    phone = HARDCODED_PHONE
    target_url = read_target_url()
    log.info("COMET triggered — launching comet (url=%s) then calling %s", target_url or "blank", phone)

    try:
        async with _comet_lock:
            comet_ok, call_ok = await asyncio.to_thread(
                _run_comet_then_call, phone, target_url
            )
            log.info("open_comet_voice=%s enter_number=%s", comet_ok, call_ok)
    except Exception as e:
        log.exception("pyautomation sequence failed: %s", e)


# ---------------------------------------------------------------------------
# Retry config
# ---------------------------------------------------------------------------

MAX_RETRIES = 999
BASE_DELAY = 5
MAX_DELAY = 300
_HEARTBEAT_INTERVAL = 300
_HEARTBEAT_FAIL_THRESHOLD = 5
_LIVENESS_INTERVAL = 30


# ---------------------------------------------------------------------------
# Liveness file writer
# ---------------------------------------------------------------------------


def _write_liveness() -> None:
    try:
        LIVENESS_FILE.write_text(f"{time.time()} ({datetime.datetime.now().isoformat()})\n")
    except Exception as e:
        log.debug("Failed to write liveness file: %s", e)


# ---------------------------------------------------------------------------
# Heartbeat self-test job
# ---------------------------------------------------------------------------

_heartbeat_fail_count = 0


async def _heartbeat_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    global _heartbeat_fail_count
    try:
        await context.bot.get_me()
        _heartbeat_fail_count = 0
        HEARTBEAT_FILE.write_text(f"{time.time()} ({datetime.datetime.now().isoformat()})\n")
        _write_liveness()
        log.debug("Heartbeat OK")
    except Exception as e:
        _heartbeat_fail_count += 1
        log.error(
            "Heartbeat failed (%d/%d): %s",
            _heartbeat_fail_count, _HEARTBEAT_FAIL_THRESHOLD, e,
        )
        if _heartbeat_fail_count >= _HEARTBEAT_FAIL_THRESHOLD:
            log.critical(
                "Heartbeat failed %d times consecutively — exiting for service restart",
                _heartbeat_fail_count,
            )
            os._exit(1)


# ---------------------------------------------------------------------------
# Liveness polling job (every 30s, independent of heartbeat)
# ---------------------------------------------------------------------------


async def _liveness_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    _write_liveness()


# ---------------------------------------------------------------------------
# Wake-from-sleep detection (background thread)
# ---------------------------------------------------------------------------


def _sleep_detection_thread() -> None:
    global _last_wake_check
    while True:
        time.sleep(30)
        now = time.time()
        gap = now - _last_wake_check
        if gap > 90:
            log.warning("Wake from sleep detected (gap %.0fs) — flushing DNS", gap)
            try:
                subprocess.run(
                    ["ipconfig", "/flushdns"],
                    check=True, timeout=10, capture_output=True,
                )
            except Exception as e:
                log.error("DNS flush failed: %s", e)
        _last_wake_check = now


# ---------------------------------------------------------------------------
# Main polling loop with backoff
# ---------------------------------------------------------------------------


def _run_with_backoff(token: str) -> None:
    global _comet_lock, _heartbeat_fail_count

    t = threading.Thread(target=_sleep_detection_thread, daemon=True, name="sleep-detect")
    t.start()

    for attempt in range(1, MAX_RETRIES + 1):
        _heartbeat_fail_count = 0
        log.info(
            ">>> Attempt %d/%d starting at %s",
            attempt, MAX_RETRIES, time.strftime("%Y-%m-%d %H:%M:%S"),
        )

        app = Application.builder().token(token).build()
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))
        app.add_error_handler(_global_error_handler)

        _comet_lock = asyncio.Lock()

        try:
            app.job_queue.run_repeating(
                _heartbeat_job,
                interval=_HEARTBEAT_INTERVAL,
                first=10,
            )
            app.job_queue.run_repeating(
                _liveness_job,
                interval=_LIVENESS_INTERVAL,
                first=5,
            )
        except AttributeError:
            log.warning("JobQueue not available (install APScheduler) — heartbeat/liveness disabled")

        try:
            log.info(
                "Telegram watcher started (attempt %d/%d) — polling COMET -> pyautomation",
                attempt, MAX_RETRIES,
            )
            _write_liveness()
            app.run_polling(
                allowed_updates=Update.ALL_TYPES,
                bootstrap_retries=5,
            )
            log.info("run_polling returned cleanly — shutting down")
            return
        except Exception as exc:
            delay = min(BASE_DELAY * (2 ** (attempt - 1)), MAX_DELAY)
            log.exception(
                "run_polling crashed (attempt %d/%d), retrying in %ds: %s",
                attempt, MAX_RETRIES, delay, exc,
            )
            if attempt == MAX_RETRIES:
                log.error("Max retries (%d) reached — giving up.", MAX_RETRIES)
                raise
            log.info("Sleeping %ds before next attempt...", delay)
            time.sleep(delay)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    _log_startup_diagnostics()

    # Load env file — use __file__-relative path, log clearly
    env_found = ENV_PATH.is_file()
    log.info("Loading env from: %s (file exists=%s)", ENV_PATH, env_found)
    if env_found:
        load_dotenv(ENV_PATH)
        log.info("Env file loaded successfully")
    else:
        log.warning("Env file NOT found at %s — relying on environment variables", ENV_PATH)

    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        log.error("TELEGRAM_BOT_TOKEN is empty or not set. Check %s or environment variables.", ENV_PATH)
        sys.exit(1)

    if ALLOWED_USER_IDS is None:
        log.warning(
            "TELEGRAM_ALLOWED_USER_IDS is unset — any user who messages your bot can trigger COMET. "
            "Set it to your numeric user id (from @userinfobot or similar)."
        )

    # Startup self-test: verify token works
    log.info("Running startup self-test...")
    loop = asyncio.new_event_loop()
    try:
        ok = loop.run_until_complete(_self_test(token))
    finally:
        loop.close()

    if not ok:
        log.error("Startup self-test FAILED — bot token is invalid or Telegram API unreachable. Exiting.")
        sys.exit(1)

    log.info("Startup self-test passed — entering polling loop")

    redacting_fmt = _TokenRedactingFormatter(
        token, "%(asctime)s %(levelname)s %(name)s %(message)s"
    )
    for handler in logging.root.handlers:
        handler.setFormatter(redacting_fmt)

    _run_with_backoff(token)


if __name__ == "__main__":
    main()
