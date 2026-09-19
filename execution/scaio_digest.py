"""Step 5 — Digest. A short note to Jimmy after each run.

Delivery is Telegram for now (TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID, the same bot
the museum project uses). Everything goes through notify(), so pointing the
digest somewhere else later (email, Muse Agent) is a change to that one function.

    python execution/scaio_digest.py "test message"
"""
from __future__ import annotations

import os
import sys

import requests

from scaio_common import load_env


def notify(text: str) -> bool:
    load_env()
    tok, chat = os.environ.get("TELEGRAM_BOT_TOKEN"), os.environ.get("TELEGRAM_CHAT_ID")
    if not tok or not chat:
        print(f"[digest — no Telegram credentials, printing instead]\n{text}")
        return False
    r = requests.post(f"https://api.telegram.org/bot{tok}/sendMessage", timeout=20, json={
        "chat_id": chat, "text": text, "disable_web_page_preview": True})
    if not r.ok:
        print(f"digest send failed: {r.status_code} {r.text[:200]}")
    return r.ok


def pr_opened(manifest: dict, pr_url: str, flagged: list[str]) -> bool:
    kind = {"weekly": "Weekly brief", "event": "Timely update", "evergreen": "Explainer"}[manifest["mode"]]
    lines = [f"SCAIO — {kind} ready for review", manifest["title"], manifest["dek"], pr_url]
    if flagged:
        lines += ["", "Flagged:"] + [f"• {f}" for f in flagged]
    return notify("\n".join(lines))


def quiet(mode: str, reason: str) -> bool:
    what = {"weekly": "Quiet week", "evergreen": "No explainer this month"}.get(mode, "Nothing to publish")
    return notify(f"SCAIO — {what}: {reason}. No PR opened.")


def failed(mode: str, error: str) -> bool:
    return notify(f"SCAIO — {mode} run failed: {error[:500]}")


if __name__ == "__main__":
    notify(" ".join(sys.argv[1:]) or "SCAIO digest test")
