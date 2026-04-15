"""
Long-poll Telegram for the bot token; on COMET (private chat), run the same sequence as
call-on-sms: enter_number_2.ahk (dial phone) then open-comet-voice.ahk.

Message: COMET, or COMET +1234567890, or COMET with phone only in AUTO_PICKUP_PHONE / call-on-sms-phone.tmp
(same as the AHK orchestrator).

Env:
  TELEGRAM_BOT_TOKEN   — required, from @BotFather
  TELEGRAM_ALLOWED_USER_IDS — optional, comma-separated numeric user ids (strongly recommended)
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
import subprocess
import sys
from pathlib import Path

from telegram import Update
from telegram.constants import ChatType
from telegram.ext import Application, ContextTypes, MessageHandler, filters

logging.basicConfig(
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
    level=logging.INFO,
)


class _TokenRedactingFormatter(logging.Formatter):
    """Formatter that replaces the bot token in the final rendered log line."""

    def __init__(self, token: str, *args: object, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)
        self._token = token

    def format(self, record: logging.LogRecord) -> str:
        text = super().format(record)
        return text.replace(self._token, "***")


log = logging.getLogger("comet_listener")

REPO_ROOT = Path(__file__).resolve().parent.parent
STEP2_SCRIPT = REPO_ROOT / "enter_number_2.ahk"
STEP3_SCRIPT = REPO_ROOT / "open-comet-voice.ahk"
TEMP_PHONE_FILE = REPO_ROOT / "call-on-sms-phone.tmp"


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


def resolve_phone_fallback() -> str | None:
    env = os.environ.get("AUTO_PICKUP_PHONE", "").strip()
    if env:
        return env
    if TEMP_PHONE_FILE.is_file():
        return TEMP_PHONE_FILE.read_text(encoding="utf-8", errors="replace").strip()
    return None


def parse_comet_text(text: str) -> tuple[bool, str | None]:
    """(is_comet_trigger, phone). Phone None means COMET was sent but no number available."""
    s = text.strip()
    m = re.match(r"^COMET(?:\s+(.+))?$", s, re.IGNORECASE | re.DOTALL)
    if not m:
        return (False, None)
    inner = m.group(1)
    if inner:
        return (True, inner.strip())
    return (True, resolve_phone_fallback())


def require_scripts() -> None:
    if not STEP2_SCRIPT.is_file():
        raise RuntimeError(f"Script not found: {STEP2_SCRIPT}")
    if not STEP3_SCRIPT.is_file():
        raise RuntimeError(f"Script not found: {STEP3_SCRIPT}")


def run_call_then_comet(exe: Path, phone: str) -> tuple[int, int]:
    r2 = subprocess.run(
        [str(exe), str(STEP2_SCRIPT), phone],
        cwd=str(REPO_ROOT),
    )
    r3 = subprocess.run(
        [str(exe), str(STEP3_SCRIPT)],
        cwd=str(REPO_ROOT),
    )
    return r2.returncode, r3.returncode


async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.effective_message
    if not msg or not msg.text:
        return
    if msg.chat.type != ChatType.PRIVATE:
        log.debug("Ignoring non-private chat")
        return

    uid = update.effective_user.id if update.effective_user else None
    if ALLOWED_USER_IDS is not None:
        if uid is None or uid not in ALLOWED_USER_IDS:
            log.warning("Rejected message from user id %s (not in allowlist)", uid)
            return

    is_comet, phone = parse_comet_text(msg.text)
    if not is_comet:
        log.info("Message received (not COMET): %s", msg.text[:40])
        return
    if not phone:
        log.error(
            "COMET but no phone: send e.g. COMET +15551234567, or set AUTO_PICKUP_PHONE, "
            "or write call-on-sms-phone.tmp"
        )
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

    try:
        rc2, rc3 = await asyncio.to_thread(run_call_then_comet, exe, phone)
        log.info("enter_number_2 exit=%s open-comet-voice exit=%s", rc2, rc3)
    except Exception as e:
        log.exception("AHK sequence failed: %s", e)


def main() -> None:
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

    log.info("Polling COMET → %s then %s", STEP2_SCRIPT.name, STEP3_SCRIPT.name)
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
