"""
Daemon that polls the Cloudflare Queue from sms2queue and triggers the
call + comet sequence when a COMET message arrives.

Trigger logic matches the Telegram bot (listener.py):
  - "COMET"              → trigger, use hardcoded phone
  - "COMET +1234567890"  → trigger, use provided phone (ignored for now)

Polls every 5 seconds. ACKs all messages regardless of content.
Reads credentials from sms2queue/.env.local.
"""

import json
import logging
import os
import re
import subprocess
import sys
import time
import base64
from datetime import datetime, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

POLL_INTERVAL = 5
MAX_RETRIES = 10

# TODO: Read sender phone from the queue message instead of hardcoding.
#       The queue message body contains {"sender": "+1234567890", ...}.
HARDCODED_PHONE = "01280043725"

REPO_ROOT = Path(__file__).resolve().parent.parent
STEP2_SCRIPT = REPO_ROOT / "enter_number_2.ahk"
STEP3_SCRIPT = REPO_ROOT / "open-comet-voice.ahk"
LOG_FILE = Path(__file__).resolve().parent / "queue-watcher.log"
ENV_PATH = Path(__file__).resolve().parent.parent / ".env.local"
TARGET_URL_FILE = REPO_ROOT / "target_url.txt"

ACCOUNT_URL = "https://api.cloudflare.com/client/v4/accounts/{account_id}/queues/{queue_id}"
PULL_URL = ACCOUNT_URL + "/messages/pull"
ACK_URL = ACCOUNT_URL + "/messages/ack"

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    filename=str(LOG_FILE),
    format="%(asctime)s %(levelname)s %(message)s",
    level=logging.INFO,
)
log = logging.getLogger("queue_watcher")

# ---------------------------------------------------------------------------
# AHK helpers (from listener.py)
# ---------------------------------------------------------------------------


def to_win_path(p: Path) -> str:
    """Convert a WSL path (/mnt/c/...) to a Windows path (C:\\...) for Windows processes."""
    s = str(p)
    if s.startswith("/mnt/"):
        drive = s[5].upper()
        return f"{drive}:{s[6:]}"
    return s


def find_autohotkey_v2_exe() -> Path | None:
    # Check Windows Program Files via WSL mount first
    wsl_candidates = [
        Path("/mnt/c/Program Files/AutoHotkey/v2/AutoHotkey64.exe"),
        Path("/mnt/c/Program Files (x86)/AutoHotkey/v2/AutoHotkey64.exe"),
    ]
    for candidate in wsl_candidates:
        if candidate.is_file():
            return candidate

    # Check native Windows env vars (works when running on Windows Python)
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


def run_call_then_comet(ahk_exe: Path, phone: str, target_url: str | None) -> tuple[int, int]:
    # AHK exe launched via WSL path (Python resolves it), script args as Windows paths (AHK reads them)
    s2 = to_win_path(STEP2_SCRIPT)
    s3 = to_win_path(STEP3_SCRIPT)
    r2 = subprocess.run([str(ahk_exe), s2, phone])
    s3_args = [str(ahk_exe), s3]
    if target_url:
        s3_args.append(target_url)
    r3 = subprocess.run(s3_args)
    return r2.returncode, r3.returncode


# ---------------------------------------------------------------------------
# COMET parsing (same logic as listener.py)
# ---------------------------------------------------------------------------


def parse_comet_text(text: str) -> tuple[bool, str | None]:
    """Returns (is_comet_trigger, phone_or_None)."""
    s = text.strip()
    m = re.match(r"^COMET(?:\s+(.+))?$", s, re.IGNORECASE | re.DOTALL)
    if not m:
        return (False, None)
    inner = m.group(1)
    if inner:
        return (True, inner.strip())
    return (True, None)


# ---------------------------------------------------------------------------
# Queue helpers (from sms_consumer.py)
# ---------------------------------------------------------------------------


def load_config() -> tuple[str, str, str]:
    if not ENV_PATH.exists():
        log.error("Config not found: %s  (run sms2queue/setup.sh)", ENV_PATH)
        sys.exit(1)

    load_dotenv(ENV_PATH)

    account_id = os.getenv("CLOUDFLARE_ACCOUNT_ID", "")
    queue_id = os.getenv("CLOUDFLARE_QUEUE_ID", "")
    api_token = os.getenv("CLOUDFLARE_API_TOKEN", "")

    missing = []
    if not account_id:
        missing.append("CLOUDFLARE_ACCOUNT_ID")
    if not queue_id:
        missing.append("CLOUDFLARE_QUEUE_ID")
    if not api_token:
        missing.append("CLOUDFLARE_API_TOKEN")

    if missing:
        log.error("Missing credentials in %s: %s", ENV_PATH, ", ".join(missing))
        sys.exit(1)

    return account_id, queue_id, api_token


def pull_messages(
    account_id: str, queue_id: str, api_token: str, retry_count: list[int]
) -> list[dict]:
    url = PULL_URL.format(account_id=account_id, queue_id=queue_id)
    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json",
    }
    payload = {
        "visibility_timeout_ms": 300 * 1000,
        "batch_size": 10,
    }

    resp = requests.post(url, headers=headers, json=payload, timeout=30)

    if resp.status_code == 401:
        log.error("Unauthorized — check CLOUDFLARE_API_TOKEN")
        sys.exit(1)

    if resp.status_code == 403:
        retry_count[0] += 1
        if retry_count[0] >= MAX_RETRIES:
            log.error("Forbidden after %d retries, giving up", MAX_RETRIES)
            sys.exit(1)
        backoff = min(2 ** retry_count[0], 300)
        log.warning("403 Forbidden, retry %d/%d in %ds", retry_count[0], MAX_RETRIES, backoff)
        time.sleep(backoff)
        return pull_messages(account_id, queue_id, api_token, retry_count)

    if retry_count[0] > 0:
        retry_count[0] = 0

    if resp.status_code >= 500:
        log.warning("Server error %d, will retry", resp.status_code)
        return []

    if resp.status_code != 200:
        log.warning("Unexpected status %d: %s", resp.status_code, resp.text[:200])
        return []

    data = resp.json()
    return data.get("result", {}).get("messages", [])


def ack_messages(account_id: str, queue_id: str, api_token: str, lease_ids: list[str]):
    if not lease_ids:
        return

    url = ACK_URL.format(account_id=account_id, queue_id=queue_id)
    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json",
    }
    payload = {"acks": [{"lease_id": lid} for lid in lease_ids], "retries": []}

    resp = requests.post(url, headers=headers, json=payload, timeout=30)
    if resp.status_code not in (200, 204):
        log.warning("ACK failed %d: %s", resp.status_code, resp.text[:200])


def extract_sms_body(msg_body) -> dict | None:
    """Unwrap Cloudflare push envelope and return the inner SMS dict."""
    if isinstance(msg_body, str):
        try:
            msg_body = json.loads(msg_body)
        except json.JSONDecodeError:
            return None

    if not isinstance(msg_body, dict):
        return None

    # Unwrap push envelope
    if "content_type" in msg_body and "body" in msg_body:
        inner = msg_body["body"]
        if isinstance(inner, str):
            try:
                inner = json.loads(base64.b64decode(inner))
            except Exception:
                try:
                    inner = json.loads(inner)
                except json.JSONDecodeError:
                    return None
        msg_body = inner

    if isinstance(msg_body, dict) and "sender" in msg_body:
        return msg_body
    return None


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------


def main() -> None:
    account_id, queue_id, api_token = load_config()

    for script in (STEP2_SCRIPT, STEP3_SCRIPT):
        if not script.is_file():
            log.error("Script not found: %s", script)
            sys.exit(1)

    ahk_exe = find_autohotkey_v2_exe()
    if not ahk_exe:
        log.warning(
            "AutoHotkey v2 not found (Program Files\\AutoHotkey\\v2\\AutoHotkey64.exe "
            "or set AUTOHOTKEY_V2_EXE) — will detect COMET but skip AHK execution"
        )

    log.info("Queue watcher started — polling every %ds", POLL_INTERVAL)

    target_url = read_target_url()
    if target_url:
        log.info("Target URL: %s", target_url)
    else:
        log.info("No target URL configured — Comet will open blank")

    retry_count = [0]
    while True:
        try:
            messages = pull_messages(account_id, queue_id, api_token, retry_count)
            ack_ids = []

            for msg in messages:
                ack_ids.append(msg["lease_id"])
                sms = extract_sms_body(msg.get("body", "{}"))
                if not sms:
                    log.debug("Non-SMS message acked and skipped")
                    continue

                body_text = sms.get("body", "")
                sender = sms.get("sender", "Unknown")
                is_comet, phone_arg = parse_comet_text(body_text)

                if not is_comet:
                    log.info("SMS from %s (not COMET): %.80s", sender, body_text)
                    continue

                # Use hardcoded phone for now; phone_arg and sender ignored
                # TODO: change to  phone = phone_arg or sender  once testing is done
                phone = HARDCODED_PHONE

                log.info(
                    "COMET triggered by %s — calling %s then comet",
                    sender, phone,
                )
                if not ahk_exe:
                    log.warning("AHK not available — skipping call + comet execution")
                else:
                    rc2, rc3 = run_call_then_comet(ahk_exe, phone, target_url)
                    log.info("enter_number_2 exit=%d open-comet-voice exit=%d", rc2, rc3)

            ack_messages(account_id, queue_id, api_token, ack_ids)

        except requests.exceptions.ConnectionError:
            log.warning("Connection error, retrying")
        except requests.exceptions.Timeout:
            log.warning("Request timed out, retrying")
        except KeyboardInterrupt:
            log.info("Stopped by user")
            sys.exit(0)
        except Exception:
            log.exception("Unexpected error")

        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
