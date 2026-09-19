"""Step 4 — Post the social queue after a content PR merges.

Run only by .github/workflows/scaio_publish.yml on a push to main. It refuses to
post from anywhere else (hard rule: never post from a local run); --dry-run
prints what would go out.

For each social/queue/*.json: wait until the article is live, post each entry
to its platform, record the result in the file, and move the file to
social/posted/ once every configured platform has posted. A platform whose
credentials aren't set is skipped and left queued, so adding credentials later
posts the backlog on the next merge — or run the workflow manually.

Credentials (GitHub repository secrets):
  LinkedIn:  LINKEDIN_ACCESS_TOKEN, LINKEDIN_AUTHOR_URN (urn:li:organization:… for
             the SCAIO page, urn:li:person:… for a personal profile),
             optional LINKEDIN_API_VERSION (YYYYMM)
  Facebook:  FACEBOOK_PAGE_ID, FACEBOOK_PAGE_TOKEN, optional FACEBOOK_GRAPH_VERSION
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
QUEUE = ROOT / "social" / "queue"
POSTED = ROOT / "social" / "posted"


def now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def configured(platform: str) -> bool:
    need = {"linkedin": ["LINKEDIN_ACCESS_TOKEN", "LINKEDIN_AUTHOR_URN"],
            "facebook": ["FACEBOOK_PAGE_ID", "FACEBOOK_PAGE_TOKEN"]}[platform]
    return all(os.environ.get(k) for k in need)


def post_linkedin(entry: dict, title: str) -> dict:
    r = requests.post("https://api.linkedin.com/rest/posts", timeout=30, headers={
        "Authorization": f"Bearer {os.environ['LINKEDIN_ACCESS_TOKEN']}",
        "LinkedIn-Version": os.environ.get("LINKEDIN_API_VERSION") or "202608",
        "X-Restli-Protocol-Version": "2.0.0",
        "Content-Type": "application/json",
    }, json={
        "author": os.environ["LINKEDIN_AUTHOR_URN"],
        "commentary": entry["text"],
        "visibility": "PUBLIC",
        "distribution": {"feedDistribution": "MAIN_FEED", "targetEntities": [],
                         "thirdPartyDistributionChannels": []},
        "content": {"article": {"source": entry["link"], "title": title}},
        "lifecycleState": "PUBLISHED",
        "isReshareDisabledByAuthor": False,
    })
    if r.status_code != 201:
        raise RuntimeError(f"LinkedIn {r.status_code}: {r.text[:300]}")
    urn = r.headers.get("x-restli-id", "")
    return {"id": urn, "url": f"https://www.linkedin.com/feed/update/{urn}/" if urn else None}


def post_facebook(entry: dict, title: str) -> dict:
    version = os.environ.get("FACEBOOK_GRAPH_VERSION") or "v23.0"
    r = requests.post(f"https://graph.facebook.com/{version}/{os.environ['FACEBOOK_PAGE_ID']}/feed",
                      timeout=30, data={"message": entry["text"], "link": entry["link"],
                                        "access_token": os.environ["FACEBOOK_PAGE_TOKEN"]})
    if not r.ok:
        raise RuntimeError(f"Facebook {r.status_code}: {r.text[:300]}")
    pid = r.json().get("id", "")
    return {"id": pid, "url": f"https://www.facebook.com/{pid}" if pid else None}


POSTERS = {"linkedin": post_linkedin, "facebook": post_facebook}


def wait_until_live(url: str, timeout_s: int = 900) -> bool:
    """GitHub Pages deploys a minute or two after the merge; don't share a 404."""
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        try:
            if requests.get(url, params={"v": int(time.time())}, timeout=20).status_code == 200:
                return True
        except requests.RequestException:
            pass
        time.sleep(20)
    return False


def process(path: Path, dry_run: bool) -> str:
    data = json.loads(path.read_text())
    pending = [e for e in data["posts"] if not e.get("posted")]
    if dry_run:
        for e in pending:
            state = "ready" if configured(e["platform"]) else "no credentials"
            print(f"--- {path.name} → {e['platform']} ({state})\n{e['text']}\n{e['link']}\n")
        return "dry-run"
    todo = [e for e in pending if configured(e["platform"])]
    if todo and not wait_until_live(data["link"]):
        return f"{path.name}: article not live yet ({data['link']}); left queued"
    errors = []
    for e in todo:
        try:
            e["posted"] = {**POSTERS[e["platform"]](e, data["title"]), "at": now()}
        except Exception as ex:
            errors.append(f"{e['platform']}: {ex}")
            e["last_error"] = {"message": str(ex)[:300], "at": now()}
    if all(e.get("posted") for e in data["posts"]):
        data["posted_at"] = now()
        POSTED.mkdir(exist_ok=True)
        (POSTED / path.name).write_text(json.dumps(data, indent=2) + "\n")
        path.unlink()
        return f"{path.name}: posted to all platforms → social/posted/"
    path.write_text(json.dumps(data, indent=2) + "\n")
    waiting = [e["platform"] for e in data["posts"] if not e.get("posted")]
    return f"{path.name}: still queued for {', '.join(waiting)}" + (f" — errors: {errors}" if errors else "")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    dry = ap.parse_args().dry_run
    in_publish_action = (os.environ.get("GITHUB_ACTIONS") == "true"
                         and os.environ.get("GITHUB_REF") == "refs/heads/main"
                         and os.environ.get("GITHUB_WORKFLOW") == "SCAIO publish")
    if not dry and not in_publish_action:
        print("Refusing to post: social posts only go out from the SCAIO publish workflow on main. "
              "Use --dry-run to preview.")
        return 2
    files = sorted(QUEUE.glob("*.json"))
    if not files:
        print("social queue empty")
        return 0
    if not dry and not any(configured(p) for p in POSTERS):
        print("No platform credentials set — queue left as is.")
        return 0
    for f in files:
        print(process(f, dry))
    return 0


if __name__ == "__main__":
    sys.exit(main())
