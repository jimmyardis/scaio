"""Step 3 — Package. Open a PR from a staged build (.tmp/build/<date>-<slug>/).

    python execution/scaio_open_pr.py .tmp/build/2026-09-21-some-slug [--test]
    python execution/scaio_open_pr.py --close-stale

The branch is built in a throwaway git worktree off origin/main, so the
working tree you run this from is never touched. Merging the PR is the
approval: Pages publishes the post and scaio_publish.yml posts the social queue.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests
import yaml

from scaio_common import ROOT, SOURCES_YAML, TMP, load_env, load_seen, save_seen

API = "https://api.github.com"


def repo() -> str:
    return os.environ.get("SCAIO_REPO") or os.environ.get("GITHUB_REPOSITORY") or "jimmyardis/scaio"


def token() -> str:
    """Actions: the workflow's GITHUB_TOKEN. Local: the gh CLI login (the
    GITHUB_TOKEN in ~/.env belongs to other projects), then env as a fallback."""
    if os.environ.get("GITHUB_ACTIONS") == "true" and os.environ.get("GITHUB_TOKEN"):
        return os.environ["GITHUB_TOKEN"]
    for gh in ("gh", str(Path.home() / "bin" / "gh")):
        try:
            # gh returns $GITHUB_TOKEN when it's set, so hide it to get the gh login itself
            env = {k: v for k, v in os.environ.items() if k not in ("GITHUB_TOKEN", "GH_TOKEN")}
            out = subprocess.run([gh, "auth", "token"], capture_output=True, text=True,
                                 timeout=20, env=env)
            if out.returncode == 0 and out.stdout.strip():
                return out.stdout.strip()
        except FileNotFoundError:
            continue
    if os.environ.get("GITHUB_TOKEN"):
        return os.environ["GITHUB_TOKEN"]
    raise RuntimeError("no GitHub token (set GITHUB_TOKEN or log in with gh)")


def gh(method: str, path: str, **kw) -> requests.Response:
    r = requests.request(method, f"{API}{path}", timeout=30, headers={
        "Authorization": f"Bearer {token()}", "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28"}, **kw)
    return r


def git(*args: str, cwd: Path = ROOT) -> str:
    out = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)
    if out.returncode != 0:
        # never echo the push URL (it carries the token)
        raise RuntimeError(f"git {args[0]} failed: {out.stderr.replace(token(), '***')[:500]}")
    return out.stdout


def pr_body(m: dict, notes: str, test: bool) -> str:
    social = "\n\n".join(
        f"**{p.title() if p != 'linkedin' else 'LinkedIn'}**\n\n" + "\n".join(f"> {l}" if l else ">" for l in t.splitlines())
        for p, t in m["social"].items())
    prefix = ("> **Test PR** opened by a dry run of the content agent. Close it when you've "
              "looked it over — merging would publish it.\n\n") if test else ""
    return f"""{prefix}## What's new

**{m['title']}** — {m['dek']} New file `{m['article']}`, plus a card at the top of the homepage Journal section and social drafts in `{m['social_file']}`. Merging publishes the post; the social drafts go out automatically after it's live. Closing publishes nothing.

Preview after merge: {m['url']}

## Social drafts

Edit these in `{m['social_file']}` before merging if you want changes — the merged file is what gets posted.

{social}

{notes}

## Checklist

- [ ] Facts verified (every claim is footnoted; the agent dropped claims it couldn't match to source text — listed above)
- [ ] Tone check: nonpartisan, constructive, no hype or doom
- [ ] Names and titles correct
- [ ] Links work
- [ ] Social drafts OK for LinkedIn and Facebook

<sub>Drafted by the SCAIO content agent ({m['mode']} run, {m['usage']}). Stale PRs close automatically after 7 days.</sub>
"""


def open_pr(build: Path, test: bool = False) -> str:
    load_env()
    m = json.loads((build / "manifest.json").read_text())
    notes = (build / "draft_notes.md").read_text()
    reviewer = yaml.safe_load(SOURCES_YAML.read_text())["agent"]["reviewer"]
    branch = f"content/{'test-' if test else ''}{m['date']}-{m['slug']}"

    git("fetch", "-q", "origin", "main")
    wt = TMP / "wt" / branch.replace("/", "-")
    if wt.exists():
        subprocess.run(["git", "worktree", "remove", "--force", str(wt)], cwd=ROOT, capture_output=True)
        shutil.rmtree(wt, ignore_errors=True)
    wt.parent.mkdir(parents=True, exist_ok=True)
    git("worktree", "add", "-q", "-B", branch, str(wt), "origin/main")
    try:
        for rel in m["files"]:
            dest = wt / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(build / "files" / rel, dest)
        git("add", *m["files"], cwd=wt)
        if os.environ.get("GITHUB_ACTIONS") == "true":
            git("config", "user.name", "github-actions[bot]", cwd=wt)
            git("config", "user.email", "41898282+github-actions[bot]@users.noreply.github.com", cwd=wt)
        label = {"weekly": "Weekly brief", "event": "Update", "evergreen": "Explainer"}[m["mode"]]
        git("commit", "-q", "-m", f"{label}: {m['title']}\n\nDrafted by the SCAIO content agent.", cwd=wt)
        git("push", "-q", "--force", f"https://x-access-token:{token()}@github.com/{repo()}.git",
            f"{branch}:{branch}", cwd=wt)
    finally:
        subprocess.run(["git", "worktree", "remove", "--force", str(wt)], cwd=ROOT, capture_output=True)

    flags = ("[TEST] " if test else "") + ("[TIMELY] " if m["timely"] else "") \
        + ("[REVIEW] " if m["sensitive"] else "")
    r = gh("POST", f"/repos/{repo()}/pulls", json={
        "title": f"{flags}{label}: {m['title']}", "head": branch, "base": "main",
        "body": pr_body(m, notes, test), "draft": test})
    if r.status_code != 201:
        raise RuntimeError(f"PR create failed: {r.status_code} {r.text[:300]}")
    pr = r.json()
    rr = gh("POST", f"/repos/{repo()}/pulls/{pr['number']}/requested_reviewers",
            json={"reviewers": [reviewer]})
    if rr.status_code not in (201, 422):     # 422: can't request the PR's own author
        print(f"warning: reviewer request failed: {rr.status_code}")

    if not test:
        seen = load_seen()
        for iid in m["item_ids"]:
            if iid in seen:
                seen[iid]["used_in"] = pr["html_url"]
        save_seen(seen)
    m["pr_url"] = pr["html_url"]
    (build / "manifest.json").write_text(json.dumps(m, indent=2))
    return pr["html_url"]


def close_stale(days: int = 7) -> list[str]:
    """Close content/* PRs open longer than `days`, with a note."""
    load_env()
    r = gh("GET", f"/repos/{repo()}/pulls", params={"state": "open", "per_page": 100})
    r.raise_for_status()
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    closed = []
    for pr in r.json():
        if not pr["head"]["ref"].startswith("content/"):
            continue
        if datetime.fromisoformat(pr["created_at"].replace("Z", "+00:00")) > cutoff:
            continue
        gh("POST", f"/repos/{repo()}/issues/{pr['number']}/comments", json={
            "body": f"Closing: unmerged for {days} days, so this content is likely stale. "
                    "Reopen if you still want it."})
        gh("PATCH", f"/repos/{repo()}/pulls/{pr['number']}", json={"state": "closed"})
        closed.append(pr["html_url"])
    return closed


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("build", nargs="?", type=Path)
    ap.add_argument("--test", action="store_true", help="open as a draft [TEST] PR; don't mark items used")
    ap.add_argument("--close-stale", action="store_true")
    a = ap.parse_args()
    if a.close_stale:
        print("\n".join(close_stale()) or "no stale PRs")
    elif a.build:
        print(open_pr(a.build.resolve(), a.test))
    else:
        ap.error("give a build directory or --close-stale")
    sys.exit(0)
