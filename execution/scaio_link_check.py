"""Link check for the education-series data files (learn/map-data.json,
learn/whos-who.json). Internal SCAIO paths must exist in the repo; external URLs
must answer. Prints a markdown report suitable for a PR body.

    python execution/scaio_link_check.py            # report only
    python execution/scaio_link_check.py --stamp    # also write last_verified on links that pass
"""
from __future__ import annotations

import argparse
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from urllib.parse import urlparse

import requests

from scaio_common import ROOT

DATA_FILES = [ROOT / "learn" / "map-data.json", ROOT / "learn" / "whos-who.json"]
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"
TIMEOUT = 25


def iter_links(node):
    """Yield every dict that carries a 'url' key, wherever it sits in the tree."""
    if isinstance(node, dict):
        if "url" in node:
            yield node
        for v in node.values():
            yield from iter_links(v)
    elif isinstance(node, list):
        for v in node:
            yield from iter_links(v)


def check_internal(path: str) -> tuple[str, str]:
    target = ROOT / path.split("#")[0]
    if target.is_dir():
        target = target / "index.html"
    return ("ok", "") if target.exists() else ("dead", "file not in repo")


def check_external(url: str) -> tuple[str, str]:
    try:
        r = requests.get(url, headers={"User-Agent": UA}, timeout=TIMEOUT, allow_redirects=True)
    except requests.RequestException as e:
        return "error", type(e).__name__
    final = r.url
    if r.status_code in (401, 403, 429):
        return "blocked", f"HTTP {r.status_code} to scripts; check by hand"
    if r.status_code >= 400:
        return "dead", f"HTTP {r.status_code}"
    a, b = urlparse(url), urlparse(final)
    if (a.netloc.removeprefix("www."), a.path.rstrip("/")) != (b.netloc.removeprefix("www."), b.path.rstrip("/")):
        return "redirect", final
    return "ok", ""


def check(url: str | None) -> tuple[str, str]:
    if not url:
        return "no-link", ""
    if url.startswith(("http://", "https://")):
        return check_external(url)
    return check_internal(url)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stamp", action="store_true", help="write last_verified on links that pass")
    args = ap.parse_args()

    today = date.today().isoformat()
    problems = 0
    for path in DATA_FILES:
        if not path.exists():
            continue
        data = json.loads(path.read_text())
        items = list(iter_links(data))
        urls = sorted({i["url"] for i in items if i.get("url")})
        with ThreadPoolExecutor(max_workers=8) as pool:
            results = dict(zip(urls, pool.map(check, urls)))
        results[None] = ("no-link", "")

        print(f"## {path.relative_to(ROOT)}\n")
        counts: dict[str, int] = {}
        for status, _ in results.values():
            counts[status] = counts.get(status, 0) + 1
        print(", ".join(f"{k}: {v}" for k, v in sorted(counts.items())) + "\n")
        rows = [(results[u][0], u, results[u][1]) for u in urls if results[u][0] != "ok"]
        if rows:
            print("| Status | URL | Detail |\n|---|---|---|")
            for status, u, detail in sorted(rows):
                print(f"| {status} | {u} | {detail} |")
            print()
        problems += sum(1 for s, _, _ in rows if s in ("dead", "error"))

        if args.stamp:
            for i in items:
                if i.get("url") and results[i["url"]][0] == "ok":
                    i["last_verified"] = today
            path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
