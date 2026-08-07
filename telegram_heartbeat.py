"""Telegram heartbeat notifier for the blink-detection agent.

Token is read at runtime from bot_telegram.md (git-ignored).
State is persisted in .telegram_agent_state.json.

CLI usage
---------
  python telegram_heartbeat.py check                    # verify bot is reachable
  python telegram_heartbeat.py startup                  # announce agent started
  python telegram_heartbeat.py heartbeat                # send one heartbeat message
  python telegram_heartbeat.py key --message MSG        # send a key update
  python telegram_heartbeat.py urgent --message MSG     # send an urgent alert
  python telegram_heartbeat.py set-state --current-task T --last-step L --next-step N
  python telegram_heartbeat.py daemon [--interval 1800] # run heartbeat loop in foreground
  python telegram_heartbeat.py test                     # send a test message
  python telegram_heartbeat.py photo --path P [--caption C]  # send an image file
"""

from __future__ import annotations

import argparse
import json
import mimetypes
import sys
import time
import urllib.parse
import urllib.request
import uuid
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
TOKEN_FILE = REPO_ROOT / "bot_telegram.md"
STATE_FILE = REPO_ROOT / ".telegram_agent_state.json"
CHAT_ID = "7784180158"


# ---------------------------------------------------------------------------
# Core send helpers
# ---------------------------------------------------------------------------

def _load_token() -> str | None:
    if not TOKEN_FILE.exists():
        return None
    return TOKEN_FILE.read_text(encoding="utf-8").strip()


def send_telegram_message(text: str) -> bool:
    """Send a single Telegram message. Returns True on success."""
    token = _load_token()
    if not token:
        print("[telegram] bot_telegram.md not found — skip send", file=sys.stderr)
        return False
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = urllib.parse.urlencode({"chat_id": CHAT_ID, "text": text}).encode()
    try:
        urllib.request.urlopen(url, data=data, timeout=10)
        return True
    except Exception as exc:
        print(f"[telegram] send failed: {exc}", file=sys.stderr)
        return False


def send_telegram_chunked(text: str, chunk_size: int = 4000) -> None:
    """Split a long message and send each chunk."""
    for i in range(0, max(1, len(text)), chunk_size):
        send_telegram_message(text[i : i + chunk_size])


def send_telegram_photo(path: str | Path, caption: str = "") -> bool:
    """Send a single image file via sendPhoto. Returns True on success."""
    token = _load_token()
    if not token:
        print("[telegram] bot_telegram.md not found — skip send", file=sys.stderr)
        return False
    file_path = Path(path)
    if not file_path.exists():
        print(f"[telegram] photo not found: {file_path}", file=sys.stderr)
        return False

    url = f"https://api.telegram.org/bot{token}/sendPhoto"
    boundary = uuid.uuid4().hex
    mime = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"

    parts: list[bytes] = []

    def _field(name: str, value: str) -> None:
        parts.append(
            (f"--{boundary}\r\nContent-Disposition: form-data; "
             f'name="{name}"\r\n\r\n{value}\r\n').encode("utf-8")
        )

    _field("chat_id", CHAT_ID)
    if caption:
        _field("caption", caption)
    parts.append(
        (f"--{boundary}\r\nContent-Disposition: form-data; "
         f'name="photo"; filename="{file_path.name}"\r\n'
         f"Content-Type: {mime}\r\n\r\n").encode("utf-8")
    )
    parts.append(file_path.read_bytes())
    parts.append(f"\r\n--{boundary}--\r\n".encode("utf-8"))
    body = b"".join(parts)

    req = urllib.request.Request(
        url, data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
    )
    try:
        urllib.request.urlopen(req, timeout=30)
        return True
    except Exception as exc:
        print(f"[telegram] photo send failed: {exc}", file=sys.stderr)
        return False


# ---------------------------------------------------------------------------
# Named send functions
# ---------------------------------------------------------------------------

def send_heartbeat(extra: str = "") -> None:
    state = _load_state()
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [f"[Heartbeat] {ts}"]
    if state.get("current_task"):
        lines.append(f"Task:      {state['current_task']}")
    if state.get("last_step"):
        lines.append(f"Last step: {state['last_step']}")
    if state.get("next_step"):
        lines.append(f"Next step: {state['next_step']}")
    if extra:
        lines.append(extra)
    send_telegram_message("\n".join(lines))


def send_key_update(message: str) -> None:
    ts = datetime.now().strftime("%H:%M")
    send_telegram_chunked(f"[Key update {ts}]\n{message}")


def send_urgent_update(message: str) -> None:
    ts = datetime.now().strftime("%H:%M")
    send_telegram_chunked(f"⚠️ URGENT {ts}\n{message}")


def start_heartbeat_loop(interval_s: int = 1800) -> None:
    """Block and send heartbeats at the given interval (run in a daemon thread or foreground)."""
    print(f"[telegram] heartbeat loop every {interval_s}s — Ctrl-C to stop")
    while True:
        send_heartbeat()
        time.sleep(interval_s)


# ---------------------------------------------------------------------------
# State management
# ---------------------------------------------------------------------------

def _load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def _save_state(state: dict) -> None:
    STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")


def set_state(current_task: str | None = None,
              last_step: str | None = None,
              next_step: str | None = None) -> None:
    state = _load_state()
    if current_task is not None:
        state["current_task"] = current_task
    if last_step is not None:
        state["last_step"] = last_step
    if next_step is not None:
        state["next_step"] = next_step
    state["updated_at"] = datetime.now().isoformat()
    _save_state(state)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="telegram_heartbeat.py",
        description="Telegram heartbeat notifier for the blink-detection agent.",
    )
    sub = p.add_subparsers(dest="command", required=True)

    sub.add_parser("check", help="Verify bot token and connectivity")
    sub.add_parser("startup", help="Send agent-started announcement")
    sub.add_parser("heartbeat", help="Send one heartbeat message")
    sub.add_parser("test", help="Send a test message")

    key = sub.add_parser("key", help="Send a key update")
    key.add_argument("--message", "-m", required=True, help="Message text")

    urg = sub.add_parser("urgent", help="Send an urgent alert")
    urg.add_argument("--message", "-m", required=True, help="Message text")

    pho = sub.add_parser("photo", help="Send an image file")
    pho.add_argument("--path", required=True, help="Path to the image file")
    pho.add_argument("--caption", default="", help="Optional caption")

    ss = sub.add_parser("set-state", help="Update agent state (persisted to JSON)")
    ss.add_argument("--current-task", default=None)
    ss.add_argument("--last-step", default=None)
    ss.add_argument("--next-step", default=None)

    dmn = sub.add_parser("daemon", help="Run heartbeat loop forever")
    dmn.add_argument("--interval", type=int, default=1800,
                     help="Seconds between heartbeats (default 1800)")

    return p


def main(argv: list[str] | None = None) -> None:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "check":
        token = _load_token()
        if not token:
            print("ERROR: bot_telegram.md not found.")
            sys.exit(1)
        ok = send_telegram_message("[check] Agent bot reachable.")
        print("OK" if ok else "FAILED")

    elif args.command == "startup":
        ts = datetime.now().strftime("%Y-%m-%d %H:%M")
        send_telegram_message(
            f"[Startup] Agent launched at {ts}\n"
            f"Repo: {REPO_ROOT.name}"
        )

    elif args.command == "heartbeat":
        send_heartbeat()

    elif args.command == "test":
        send_telegram_message(f"[Test] {datetime.now().strftime('%H:%M:%S')} — bot working.")

    elif args.command == "key":
        send_key_update(args.message)

    elif args.command == "urgent":
        send_urgent_update(args.message)

    elif args.command == "photo":
        ok = send_telegram_photo(args.path, args.caption)
        print("OK" if ok else "FAILED")

    elif args.command == "set-state":
        set_state(
            current_task=args.current_task,
            last_step=args.last_step,
            next_step=args.next_step,
        )
        print("State updated:", _load_state())

    elif args.command == "daemon":
        start_heartbeat_loop(interval_s=args.interval)


if __name__ == "__main__":
    main()
