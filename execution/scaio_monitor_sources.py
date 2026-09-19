"""Step 1 — Monitor. Fetch every source in directives/scaio_sources.yaml, keep
AI-relevant items, classify by pillar, score, dedupe against .tmp/scaio_seen.json.

Writes .tmp/scaio_items_YYYY-MM-DD.json (items new this run) and updates the
seen file. Seen entries keep the item so later runs (weekly roundup) can pick
up items first spotted by daily event checks.

    python execution/scaio_monitor_sources.py
"""
from __future__ import annotations

import calendar
import html
import json
import re
import sys
from datetime import datetime, timezone
from urllib.parse import urljoin

import feedparser
import yaml

from scaio_common import (
    PRESS_PATTERN, ROOT, SC_PATTERN, SOURCES_YAML, TMP, ai_hits, classify_pillars,
    http_get, item_id, load_seen, now_utc, save_seen, today,
)


def _clean(s: str) -> str:
    s = re.sub(r"<[^>]+>", " ", s or "")
    return re.sub(r"\s+", " ", html.unescape(s)).strip()


def _item(src: dict, title: str, url: str, summary: str = "", published: str | None = None,
          key: str | None = None, event: bool = False, **extra) -> dict:
    return {
        "id": item_id(key or url),
        "source_id": src["id"],
        "source_name": src["name"],
        "title": _clean(title),
        "url": url,
        "summary": _clean(summary)[:600],
        "published": published,
        "primary": bool(src.get("primary")),
        "event": event,
        "fetchable": not src.get("discovery_only"),
        **extra,
    }


# ── Fetchers ───────────────────────────────────────────────────────────

def fetch_rss(src: dict) -> list[dict]:
    r = http_get(src["url"])
    r.raise_for_status()
    feed = feedparser.parse(r.content)
    out = []
    for e in feed.entries:
        published = None
        t = e.get("published_parsed") or e.get("updated_parsed")
        if t:
            published = datetime.fromtimestamp(calendar.timegm(t), timezone.utc).isoformat()
        out.append(_item(src, e.get("title", ""), e.get("link", ""),
                         e.get("summary", ""), published))
    return out


def fetch_html_links(src: dict) -> list[dict]:
    r = http_get(src["url"])
    r.raise_for_status()
    pat = re.compile(src["link_pattern"])
    out, seen = [], set()
    for href, text in re.findall(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', r.text, re.S):
        if not pat.search(href):
            continue
        url = urljoin(src.get("base_url", src["url"]), href)
        title = _clean(text)
        if url in seen or len(title) < 12:
            continue
        seen.add(url)
        out.append(_item(src, title, url))
    return out


def fetch_federal_register(src: dict) -> list[dict]:
    r = http_get(src["url"])
    r.raise_for_status()
    out = []
    for d in r.json().get("results", []):
        pub = d.get("publication_date")
        out.append(_item(src, d.get("title", ""), d.get("html_url", ""),
                         d.get("abstract") or "",
                         f"{pub}T00:00:00+00:00" if pub else None,
                         doc_type=d.get("type")))
    return out


_DAY_RE = re.compile(r"^(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),\s+"
                     r"([A-Z][a-z]+ \d{1,2}(?:, \d{4})?)")


def parse_meetings(page_html: str) -> list[dict]:
    """Split a scstatehouse.gov meetings page into meetings:
    {date, time, location, committee, agenda_url}."""
    body = re.sub(r"<script.*?</script>|<style.*?</style>", "", page_html, flags=re.S)
    # keep agenda hrefs visible as tokens in the text stream
    body = re.sub(r'<a[^>]+href="(/agendas/[^"]+)"[^>]*>', r"\n[[AGENDA \1]]\n", body)
    lines = [html.unescape(l).strip() for l in re.sub(r"<[^>]+>", "\n", body).split("\n")]
    lines = [l for l in lines if l]
    meetings, day, year, cur = [], None, None, None
    for line in lines:
        m = _DAY_RE.match(line)
        if m:
            day = m.group(2)
            y = re.search(r"\d{4}", day)
            if y:
                year = y.group(0)
            elif year:
                day = f"{day}, {year}"
            continue
        if re.fullmatch(r"\d{1,2}:\d{2}\s*[ap]m.*", line, re.I) and day:
            cur = {"date": day, "time": line, "location": "", "committee": "", "agenda_url": None}
            meetings.append(cur)
            continue
        if cur and line.startswith("--") and not cur["committee"]:
            parts = [p.strip() for p in line.split("--") if p.strip()]
            if len(parts) >= 2:
                cur["location"], cur["committee"] = parts[0], " -- ".join(parts[1:])
            elif parts:
                cur["committee"] = parts[0]
            continue
        if cur and line.startswith("[[AGENDA "):
            cur["agenda_url"] = "https://www.scstatehouse.gov" + line[9:-2]
    return meetings


def fetch_sc_meetings(src: dict) -> list[dict]:
    r = http_get(src["url"])
    r.raise_for_status()
    out = []
    for m in parse_meetings(r.text):
        if not ai_hits(m["committee"]):
            continue
        title = f'{m["committee"]} meets {m["date"]}, {m["time"]}'
        url = m["agenda_url"] or src["url"]
        out.append(_item(src, title, url,
                         f'{m["committee"]} — {m["date"]} {m["time"]}, {m["location"]}',
                         key=f'meeting|{m["committee"]}|{m["date"]}|{m["time"]}',
                         event=True, meeting=m))
    return out


def parse_bill_last_action(page_html: str) -> dict | None:
    """Last row of the HISTORY OF LEGISLATIVE ACTIONS table on a bill page."""
    title = re.search(r"<title>[^<]*Bill \d+: (.*?)(?: - South Carolina Legislature Online)?</title>",
                      page_html, re.S)
    hist = page_html.split("HISTORY OF LEGISLATIVE ACTIONS", 1)
    if len(hist) < 2:
        return None
    rows = []
    for tr in re.findall(r"<tr>(.*?)</tr>", hist[1], re.S):
        cells = [_clean(c) for c in re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S)]
        if len(cells) == 3 and re.fullmatch(r"\d{1,2}/\d{1,2}/\d{4}", cells[0]):
            rows.append(cells)
    if not rows:
        return None
    date, body, desc = rows[-1]
    desc = re.sub(r"\s*\(\s*(Senate|House) Journal-page \d+\s*\)", "", desc)
    return {"title": _clean(title.group(1)) if title else "", "date": date,
            "body": body, "action": desc[:300]}


def fetch_sc_bills(src: dict) -> list[dict]:
    urls = []
    bills_json = ROOT / src.get("bills_json", "bills.json")
    if bills_json.exists():
        for b in json.loads(bills_json.read_text())["bills"]:
            if b.get("url"):
                urls.append((b["bill_number"], b["url"]))
    urls += [(u.rsplit("/", 1)[-1], u) for u in src.get("extra_bills", [])]
    out = []
    for number, url in urls:
        try:
            r = http_get(url)
            if r.status_code != 200:
                continue
            last = parse_bill_last_action(r.text)
        except Exception:
            continue
        if not last:
            continue
        try:
            acted = datetime.strptime(last["date"], "%m/%d/%Y").replace(tzinfo=timezone.utc)
        except ValueError:
            continue
        if (now_utc() - acted).days > 14:
            continue   # old actions aren't news; a new action makes a new key
        out.append(_item(src, f'{number} ({last["title"]}): {last["action"]}', url,
                         f'{last["body"]} action on {last["date"]}: {last["action"]}',
                         acted.isoformat(), key=f'bill|{url}|{last["date"]}|{last["action"]}',
                         event=True, bill_number=number))
    return out


FETCHERS = {
    "rss": fetch_rss,
    "html_links": fetch_html_links,
    "federal_register": fetch_federal_register,
    "sc_meetings": fetch_sc_meetings,
    "sc_bills": fetch_sc_bills,
}

def resolve_google_news(url: str) -> str | None:
    """Google News RSS links are encrypted redirects. Decode one to the
    publisher's URL via the same batchexecute call the news.google.com page
    makes. Returns None if Google changes the format (the item then stays a lead)."""
    import requests
    m = re.search(r"/articles/([^?]+)", url)
    if not m:
        return None
    gid = m.group(1)
    ua = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                        "(KHTML, like Gecko) Chrome/126 Safari/537.36"}
    try:
        page = requests.get(f"https://news.google.com/articles/{gid}", headers=ua, timeout=20).text
        sig = re.search(r'data-n-a-sg="([^"]+)"', page)
        ts = re.search(r'data-n-a-ts="([^"]+)"', page)
        if not (sig and ts):
            return None
        inner = json.dumps(["garturlreq", [["X", "X", ["X", "X"], None, None, 1, 1, "US:en", None, 1,
                                            None, None, None, None, None, 0, 1], "X", "X", 1, [1, 1, 1],
                                           1, 1, None, 0, 0, None, 0], gid, int(ts.group(1)), sig.group(1)])
        r = requests.post("https://news.google.com/_/DotsSplashUi/data/batchexecute", timeout=20,
                          headers={**ua, "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8"},
                          data={"f.req": json.dumps([[["Fbv4je", inner, None, "generic"]]])})
        rows = json.loads(r.text.split("\n\n", 1)[1])[:-2]
        real = json.loads(rows[0][2])[1]
        return real if isinstance(real, str) and real.startswith("http") else None
    except Exception:
        return None


def resolve_lead(item: dict) -> dict:
    """Turn a Google News lead into a normal, citable item when possible."""
    real = resolve_google_news(item["url"])
    if not real:
        return item
    title, _, outlet = item["title"].rpartition(" - ")
    return {**item, "url": real, "id": item_id(real), "fetchable": True,
            "title": title or item["title"],
            "source_name": outlet or item["source_name"], "via": "Google News"}


# ── Relevance ──────────────────────────────────────────────────────────

AI_SPECIFIC_TYPES = {"sc_meetings", "sc_bills"}   # already AI-filtered at the source


def score_item(item: dict, src: dict) -> dict | None:
    """Attach pillars/score; None when the item isn't relevant enough to keep."""
    text = f'{item["title"]} {item["summary"]}'
    hits = ai_hits(item["title"]) * 2 + ai_hits(item["summary"])
    if src["type"] not in AI_SPECIFIC_TYPES and hits == 0:
        return None
    if src.get("require") and not re.search(src["require"], text):
        return None
    sc = bool(src.get("sc_local")) or src["type"] in AI_SPECIFIC_TYPES \
        or bool(SC_PATTERN.search(text))
    pillars = classify_pillars(text, src.get("pillar"))
    if not sc and 3 not in pillars:
        return None
    score = min(hits, 4) + (3 if sc else 0) + (2 if item["primary"] else 0) \
        + (2 if item["event"] else 0) + (1 if 1 in pillars else 0)
    if src["type"] in AI_SPECIFIC_TYPES:
        score += 3
    if score < 3:
        return None
    item["pillars"] = pillars
    item["score"] = min(score, 10)
    item["sc_relevant"] = sc
    item["press"] = bool(PRESS_PATTERN.search(text))
    return item


def run() -> dict:
    sources = yaml.safe_load(SOURCES_YAML.read_text())["sources"]
    seen = load_seen()
    stamp = now_utc().isoformat()
    new_items, status = [], {}
    for src in sources:
        try:
            raw = FETCHERS[src["type"]](src)
        except Exception as e:
            status[src["id"]] = f"error: {type(e).__name__}: {str(e)[:120]}"
            continue
        kept = [i for i in (score_item(r, src) for r in raw) if i]
        fresh = [i for i in kept if i["id"] not in seen]
        if src.get("resolve") == "google_news":
            resolved = []
            for lead in fresh:
                seen[lead["id"]] = {"alias": True, "first_seen": stamp}   # don't re-resolve
                r = resolve_lead(lead)
                if r["id"] not in seen:
                    resolved.append(r)
            fresh = resolved
        for i in fresh:
            i["first_seen"] = stamp
            i["used_in"] = None
            seen[i["id"]] = i
        new_items += fresh
        status[src["id"]] = f"ok: {len(raw)} fetched, {len(kept)} relevant, {len(fresh)} new"
    save_seen(seen)
    new_items.sort(key=lambda i: -i["score"])
    TMP.mkdir(exist_ok=True)
    out = {"run_at": stamp, "source_status": status, "items": new_items}
    (TMP / f"scaio_items_{today()}.json").write_text(json.dumps(out, indent=1))
    return out


if __name__ == "__main__":
    result = run()
    for sid, st in result["source_status"].items():
        print(f"  {sid:24s} {st}")
    print(f"\n{len(result['items'])} new items")
    for i in result["items"][:25]:
        print(f'  [{i["score"]:>2}] p{",".join(map(str, i["pillars"]))} {i["source_id"]}: {i["title"][:100]}')
    sys.exit(0)
