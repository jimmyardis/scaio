"""Entry point: one content-agent run, end to end.

    python execution/scaio_run.py --mode weekly            # monitor → draft → PR → digest
    python execution/scaio_run.py --mode event
    python execution/scaio_run.py --mode evergreen         # acts only on the first Wednesday
    python execution/scaio_run.py --mode weekly --test     # draft [TEST] PR, items not marked used
    python execution/scaio_run.py --mode weekly --no-pr    # stop after staging (.tmp/build/)

The GitHub Actions workflow (.github/workflows/scaio_content.yml) calls this.
"""
from __future__ import annotations

import argparse
import json
import sys
import traceback

from scaio_common import load_env, now_utc
import scaio_digest as digest
import scaio_draft_content as drafter
import scaio_monitor_sources as monitor
import scaio_open_pr as packager


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["weekly", "event", "evergreen"], required=True)
    ap.add_argument("--test", action="store_true")
    ap.add_argument("--no-pr", action="store_true")
    ap.add_argument("--no-digest", action="store_true")
    ap.add_argument("--skip-monitor", action="store_true")
    ap.add_argument("--force", action="store_true", help="evergreen: run even if not the first Wednesday")
    a = ap.parse_args()
    load_env()
    send = (lambda *_: None) if a.no_digest else None

    if a.mode == "evergreen" and not a.force:
        d = now_utc().date()
        if not (d.weekday() == 2 and d.day <= 7):
            print("evergreen runs on the first Wednesday of the month; nothing to do")
            return 0

    try:
        if not a.no_pr:
            for url in packager.close_stale():
                print(f"closed stale PR {url}")
        if not a.skip_monitor:
            result = monitor.run()
            print(f"monitor: {len(result['items'])} new items")
        build = drafter.draft(a.mode)
        if build is None:
            if a.mode != "event":            # daily event checks stay silent when quiet
                (send or digest.quiet)(a.mode, "nothing substantive in the sources this cycle")
            return 0
        if a.no_pr:
            print(f"staged only: {build}")
            return 0
        pr_url = packager.open_pr(build, test=a.test)
        print(f"PR: {pr_url}")
        manifest = json.loads((build / "manifest.json").read_text())
        flagged = []
        if manifest["sensitive"]:
            flagged.append("sensitive topic — extra review")
        notes = (build / "draft_notes.md").read_text()
        if "**Dropped claims**" in notes:
            flagged.append("some claims were dropped as unverifiable (see PR)")
        if "SCAIO/Jimmy in the press" in notes:
            flagged.append("SCAIO mentioned in the press")
        (send or digest.pr_opened)(manifest, pr_url, flagged)
        return 0
    except Exception as e:
        traceback.print_exc()
        (send or digest.failed)(a.mode, f"{type(e).__name__}: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
