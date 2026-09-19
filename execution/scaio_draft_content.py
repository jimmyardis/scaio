"""Step 2 — Draft. Turn monitored items into a staged post + social drafts.

    python execution/scaio_draft_content.py --mode weekly|event|evergreen

Pipeline:
  1. select unused items from .tmp/scaio_seen.json for the mode's window
  2. fetch each item's full text (unreachable/paywalled → skipped, noted)
  3. Claude: build a fact sheet — every fact carries a verbatim supporting quote
  4. verify each quote against our own fetch of the source; drop failures
  5. Claude: write the post and social drafts from verified facts only
  6. enforce citation/quote/link/social rules (one retry with the errors)
  7. stage files under .tmp/build/<date>-<slug>/ for scaio_open_pr.py

Nothing is written into the working tree; the PR step copies staged files into
a fresh worktree off origin/main.

Exit status: 0 drafted, 3 nothing substantive (quiet), 1 error.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import date, datetime
from pathlib import Path

import anthropic
import yaml

from scaio_common import (
    DIRECTIVE, REFERENCE_ARTICLE, ROOT, SITE_URL, SOURCES_YAML, TMP, days_ago, fetch_text,
    load_env, load_seen, now_utc, today,
)
from scaio_render import (
    add_homepage_card, build_page, check_social, render_body, render_sources, verify_facts,
)

QUIET = 3


def cfg() -> dict:
    return yaml.safe_load(SOURCES_YAML.read_text())["agent"]


def directive_sections(*names: str) -> str:
    """Pull named '## ' sections out of the directive so prompts always carry
    the current editorial rules."""
    text = DIRECTIVE.read_text()
    out = []
    for name in names:
        m = re.search(rf"^## {re.escape(name)}.*?(?=^## |\Z)", text, re.S | re.M)
        if m:
            out.append(m.group(0).strip())
    return "\n\n".join(out)


def git_show(path: str) -> str:
    """File content at origin/main (falls back to the working tree)."""
    try:
        subprocess.run(["git", "fetch", "-q", "origin", "main"], cwd=ROOT, check=False,
                       capture_output=True, timeout=60)
        return subprocess.run(["git", "show", f"origin/main:{path}"], cwd=ROOT, check=True,
                              capture_output=True, text=True).stdout
    except Exception:
        return (ROOT / path).read_text()


def date_label(d: date) -> str:
    return f"{d.strftime('%B')} {d.day}, {d.year}"


# ── Claude ─────────────────────────────────────────────────────────────

class Usage:
    def __init__(self):
        self.input = self.output = self.calls = 0

    def add(self, u) -> None:
        self.calls += 1
        self.input += (u.input_tokens or 0) + (getattr(u, "cache_read_input_tokens", 0) or 0)
        self.output += u.output_tokens or 0

    def __str__(self) -> str:
        return f"{self.calls} Claude calls, {self.input:,} input / {self.output:,} output tokens"


USAGE = Usage()


def claude(system: str, user: str, *, schema: dict | None = None, tools: list | None = None,
           effort: str = "high", max_tokens: int = 64000) -> str:
    """One Claude turn (continuing through pause_turn for server tools). Returns
    the concatenated text. Refusals raise."""
    client = anthropic.Anthropic()
    messages: list = [{"role": "user", "content": user}]
    output_config: dict = {"effort": effort}
    if schema:
        output_config["format"] = {"type": "json_schema", "schema": schema}
    for _ in range(6):
        kwargs = dict(
            model=cfg()["model"], max_tokens=max_tokens, system=system, messages=messages,
            thinking={"type": "adaptive"},
            extra_headers={"anthropic-beta": "server-side-fallback-2026-07-01"},
            extra_body={"fallbacks": "default", "output_config": output_config},
        )
        if tools:
            kwargs["tools"] = tools
        with client.messages.stream(**kwargs) as stream:
            msg = stream.get_final_message()
        USAGE.add(msg.usage)
        if msg.stop_reason == "refusal":
            raise RuntimeError(f"Claude declined the request: {getattr(msg, 'stop_details', None)}")
        if msg.stop_reason == "pause_turn":
            messages.append({"role": "assistant", "content": msg.content})
            continue
        if msg.stop_reason == "max_tokens":
            raise RuntimeError("Claude hit max_tokens — output truncated")
        return "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")
    raise RuntimeError("too many pause_turn continuations")


def claude_json(system: str, user: str, schema: dict, **kw) -> dict:
    return json.loads(claude(system, user, schema=schema, **kw))


def _obj(props: dict, required: list[str] | None = None) -> dict:
    return {"type": "object", "properties": props,
            "required": required if required is not None else list(props),
            "additionalProperties": False}


STR = {"type": "string"}
BOOL = {"type": "boolean"}

FACTS_SCHEMA = _obj({
    "substantive": BOOL,
    "skip_reason": STR,
    "angle": STR,
    "facts": {"type": "array", "items": _obj({
        "id": STR, "claim": STR, "source": {"type": "integer"}, "quote": STR})},
    "conflicts": {"type": "array", "items": STR},
    "sensitive": BOOL,
    "sensitive_reason": STR,
    "press_mentions": {"type": "array", "items": STR},
})

POST_SCHEMA = _obj({
    "slug": STR,
    "title": STR,
    "dek": STR,
    "description": STR,
    "tags": {"type": "array", "items": STR},
    "card_blurb": STR,
    "blocks": {"type": "array", "items": _obj({
        "kind": {"type": "string", "enum": ["p", "h2", "callout"]},
        "kicker": STR, "heading": STR, "text": STR})},
    "social": _obj({"linkedin": STR, "facebook": STR}),
    "notes": {"type": "array", "items": STR},
})

EVERGREEN_SCHEMA = _obj({
    "topic": STR,
    "question": STR,
    "why_now": STR,
    "urls": {"type": "array", "items": STR},
})

MODES = {
    "weekly": {
        "card_tag": "Weekly Brief",
        "read_link": "Read the brief",
        "shape": ("A weekly brief, 500–900 words. A 2–3 sentence opening on what mattered "
                  "this week and why. Then short sections with h2 headings, grouped by pillar "
                  "(only pillars with real news). Close with a short 'What we're watching' "
                  "section. Skip filler; a short brief is better than a padded one."),
        "tags": "first tag 'Weekly Brief', second the dominant pillar (e.g. 'SC Legislature')",
    },
    "event": {
        "card_tag": "Update",
        "read_link": "Read the update",
        "shape": ("A short update, 300–550 words, on one development: what happened, the "
                  "context a reader needs, and what comes next. At most two h2 sections."),
        "tags": "first tag 'Update', second the pillar (e.g. 'SC Legislature')",
    },
    "evergreen": {
        "card_tag": "Explainer",
        "read_link": "Read the explainer",
        "shape": ("A plain-language explainer, 800–1,300 words, answering one question "
                  "lawmakers or residents are actually asking. Lead with the short answer, "
                  "then build it out with h2 sections. Compare other states where the "
                  "sources support it."),
        "tags": "first tag 'Explainer', second the topic area",
    },
}


def system_prompt() -> str:
    return (
        "You are the drafting desk for SCAIO, the South Carolina Artificial Intelligence "
        "Observatory: a nonpartisan, public-interest source on AI policy and adoption in "
        "South Carolina. Everything you draft is reviewed by SCAIO's director before it is "
        "published, but it should be ready to publish as written.\n\n"
        + directive_sections("Context", "Content pillars", "Voice & editorial rules", "Edge cases")
    )


# ── Selection + sources ────────────────────────────────────────────────

def select_items(mode: str, seen: dict) -> list[dict]:
    c = cfg()
    window = c["windows"][mode]
    min_score = c["min_score"].get(mode, 0)
    out = []
    for it in seen.values():
        if it.get("alias") or it.get("used_in"):
            continue
        age = days_ago(it.get("published") or it["first_seen"])
        if age > window or it["score"] < min_score:
            continue
        if mode == "event" and not (it["event"] or (1 in it["pillars"] and it["score"] >= 9)):
            continue
        out.append(it)
    out.sort(key=lambda i: (-i["score"], i.get("published") or ""))
    return out


def gather_sources(items: list[dict], extra_urls: list[str] = ()) -> tuple[dict[int, dict], list[str], list[dict]]:
    """Fetch full text. Returns ({n: source}, notes, tips) where tips are
    discovery-only headlines that can't be cited."""
    sources: dict[int, dict] = {}
    notes, tips = [], []
    urls_done = set()
    cap = cfg()["max_sources"]

    def add(url, title, outlet, published, summary, item_ids):
        if url in urls_done or len(sources) >= cap:
            return
        urls_done.add(url)
        text, status = fetch_text(url)
        if text is None and summary and "scstatehouse.gov" in url:
            text = summary     # meeting notices: the schedule listing itself is the record
        if text is None:
            notes.append(f"Skipped {outlet or url} — {title[:80]} ({status}).")
            return
        d = None
        if published:
            try:
                d = datetime.fromisoformat(published).date()
            except ValueError:
                pass
        n = len(sources) + 1
        sources[n] = {"n": n, "url": url, "title": title, "outlet": outlet,
                      "date_label": date_label(d) if d else "", "text": text[:40000],
                      "item_ids": item_ids}

    titles = set()
    for it in items:
        key = re.sub(r"^(video|live|watch):\s*", "", it["title"].lower()).strip()
        if key in titles:          # syndicated copies of the same story
            continue
        titles.add(key)
        if not it.get("fetchable", True):
            tips.append(it)
            continue
        add(it["url"], it["title"], it["source_name"], it.get("published"), it.get("summary"), [it["id"]])
    for u in extra_urls:
        add(u, "", "", None, "", [])
    return sources, notes, tips


def sources_block(sources: dict[int, dict]) -> str:
    return "\n\n".join(
        f'<source n="{s["n"]}" outlet="{s["outlet"]}" url="{s["url"]}" date="{s["date_label"]}">\n'
        f'<title>{s["title"]}</title>\n{s["text"]}\n</source>'
        for s in sources.values())


# ── Steps ──────────────────────────────────────────────────────────────

def plan_evergreen(seen: dict) -> tuple[dict, list[str]]:
    """Pick an explainer topic and find sources for it with web search."""
    recent = sorted((i for i in seen.values() if not i.get("alias")), key=lambda i: -i["score"])[:25]
    existing = sorted(p.name for p in ROOT.glob("scaio-article-*.html"))
    prompt = (
        "Choose this month's SCAIO explainer: one plain-language question that South "
        "Carolina lawmakers, their aides, or residents are actually asking about AI right "
        "now. Favor questions tied to the Senate Special Committee on AI's study, the "
        "state's own use of AI, or what other states have already done.\n\n"
        f"Recent items we've tracked:\n" + "\n".join(f"- {i['title']} ({i['source_name']})" for i in recent)
        + "\n\nExisting SCAIO articles (don't repeat these):\n" + "\n".join(f"- {e}" for e in existing)
        + "\n\nUse web search to find 5–10 sources that can support the explainer. Put "
          "primary sources first (scstatehouse.gov, state agency sites, official "
          "documents, NCSL, other states' legislatures), then reputable reporting. Return "
          "only URLs you actually saw in search results, and prefer pages that are "
          "readable without a subscription."
    )
    tools = [{"type": "web_search_20260209", "name": "web_search", "max_uses": 8}]
    plan = claude_json(system_prompt(), prompt, EVERGREEN_SCHEMA, tools=tools)
    return plan, plan["urls"]


def build_fact_sheet(mode: str, sources: dict, tips: list[dict], topic: dict | None) -> dict:
    tip_lines = "\n".join(f"- {t['title']}" for t in tips[:20]) or "(none)"
    task = {
        "weekly": "Decide whether this week has enough substantive SC-relevant AI policy news for a weekly brief.",
        "event": "Decide whether the sources describe a timely development (a committee meeting, testimony, or bill action) worth a short update.",
        "evergreen": f"Gather facts for an explainer answering: {topic['question'] if topic else ''}",
    }[mode]
    prompt = (
        f"{task}\n\n"
        "Build a fact sheet from the numbered sources below. Rules:\n"
        "- Each fact is one checkable claim, stated plainly, with `source` set to the "
        "number of the source that supports it.\n"
        "- `quote` must be copied character-for-character from that source's text — a "
        "short span (one sentence or less) that directly supports the claim. It is used "
        "for automated verification, and a fact whose quote isn't found in the source is "
        "discarded.\n"
        "- Only use what the sources say. Background knowledge, however confident, "
        "doesn't go in the fact sheet.\n"
        "- Prefer primary sources when several support the same fact.\n"
        "- Give facts ids F1, F2, …\n"
        "- `substantive` is false when there isn't enough real news (or support) for a "
        "post worth a reader's time; say why in `skip_reason`. Never pad.\n"
        "- `conflicts`: where sources disagree, say so and which is primary.\n"
        "- `sensitive`: true for partisan flashpoints (e.g. a deepfake involving a named "
        "candidate); explain in `sensitive_reason`.\n"
        "- `press_mentions`: any source that quotes Jimmy Ardis or mentions SCAIO.\n"
        "- `angle`: one or two sentences on the story, consistent with SCAIO's editorial "
        "foundation.\n\n"
        f"Headlines we spotted but could not read (not citable; mention only as leads):\n{tip_lines}\n\n"
        f"{sources_block(sources)}"
    )
    return claude_json(system_prompt(), prompt, FACTS_SCHEMA)


def write_post(mode: str, facts: list[dict], sources: dict, sheet: dict, errors: list[str] | None,
               previous: dict | None) -> dict:
    m = MODES[mode]
    fact_lines = "\n".join(
        f'{f["id"]} [source {f["source"]}: {sources[f["source"]]["outlet"]}]: {f["claim"]}'
        for f in facts)
    source_lines = "\n".join(f'source {n}: {s["outlet"]} — {s["title"]} — {s["url"]}'
                              for n, s in sources.items() if any(f["source"] == n for f in facts))
    quotable = "\n".join(
        f'source {n}: quotable spans must be copied exactly from this text:\n{s["text"][:6000]}'
        for n, s in sources.items() if any(f["source"] == n for f in facts))
    prompt = (
        f"Write a SCAIO {mode} post. Shape: {m['shape']}\n\n"
        f"Angle: {sheet['angle']}\n"
        + (f"Conflicting reports to acknowledge: {sheet['conflicts']}\n" if sheet["conflicts"] else "")
        + "\nUse ONLY these verified facts. After every clause that relies on a fact, add "
          "its marker, e.g. `…met on September 16 [F2].` or `[F2,F5]`. Uncited analysis "
          "and framing is fine as long as it adds no new facts.\n\n"
        f"{fact_lines}\n\nSources (for links):\n{source_lines}\n\n"
        "Formatting inside `text`: plain sentences; **bold** and *italic* allowed; links "
        "as [text](url) only to the sources' URLs or scaio.org pages. Blocks: `p` "
        "paragraphs, `h2` headings (put the heading in `heading`, leave `text` empty), and "
        "at most one `callout` (kicker + heading + text) for a call to action such as a "
        "public-comment address — only if the facts support one.\n"
        "Quotes: paraphrase by default. A direct quote must be under 15 words, copied "
        "exactly from the text of a source cited in the same paragraph, and each source "
        "may be quoted at most once in the whole post.\n\n"
        f"Metadata: `slug` is lowercase-hyphenated, 3–6 words, no date. `tags`: two short "
        f"tags — {m['tags']}. `dek`: one sentence. `description`: one or two sentences for "
        "search/social previews. `card_blurb`: 1–2 sentences for the homepage card.\n\n"
        "Social: `linkedin` (120–220 words, professional, no hashtag spam — at most 3) and "
        "`facebook` (40–90 words, warm and plain). Both must be accurate summaries of the "
        "post, claim nothing the post doesn't, and include no URL (the link is attached "
        "separately) and no [F#] markers.\n\n"
        "`notes`: anything the reviewer should double-check — uncertain framing, titles "
        "or names you're less sure of, suggested edits.\n\n"
        f"For exact-quote checking, the source texts:\n{quotable}"
    )
    if errors and previous:
        prompt += ("\n\nYour previous draft broke these rules. Fix every one and return the "
                   "full corrected post:\n- " + "\n- ".join(errors)
                   + f"\n\nPrevious draft:\n{json.dumps(previous)[:30000]}")
    return claude_json(system_prompt(), prompt, POST_SCHEMA)


def unique_slug(slug: str) -> str:
    slug = re.sub(r"[^a-z0-9-]+", "-", slug.lower()).strip("-")[:60] or "update"
    base, n = slug, 2
    while (ROOT / f"scaio-article-{slug}.html").exists():
        slug, n = f"{base}-{n}", n + 1
    return slug


def stage(mode: str, post: dict, rendered, sheet: dict, dropped: list, fetch_notes: list,
          tips: list, verified: list, sources: dict, used_item_ids: list[str]) -> Path:
    c = cfg()
    d = now_utc().date()
    slug = unique_slug(post["slug"])
    filename = f"scaio-article-{slug}.html"
    url = f"{SITE_URL}/{filename}"
    build = TMP / "build" / f"{d.isoformat()}-{slug}"
    if build.exists():
        shutil.rmtree(build)
    files = build / "files"
    (files / "social" / "queue").mkdir(parents=True)

    reference = git_show(REFERENCE_ARTICLE)
    page = build_page(reference, title=post["title"], dek=post["dek"],
                      description=post["description"], tags=post["tags"][:3],
                      date_iso=d.isoformat(), date_label=date_label(d), byline=c["byline"],
                      body_html=rendered.body_html, sources_html=render_sources(rendered.sources),
                      url=url)
    (files / filename).write_text(page)

    m = MODES[mode]
    index = add_homepage_card(git_show("index.html"), href=filename,
                              tag=f"{m['card_tag']} · {d.strftime('%B %Y')}", title=post["title"],
                              blurb=post["card_blurb"], link_label=m["read_link"])
    (files / "index.html").write_text(index)

    social_name = f"{d.isoformat()}-{slug}.json"
    social = {
        "slug": slug, "title": post["title"], "link": url, "created": now_utc().isoformat(),
        "posts": [{"platform": p, "text": post["social"][p].strip(), "link": url, "image": None}
                  for p in c["platforms"]],
    }
    (files / "social" / "queue" / social_name).write_text(json.dumps(social, indent=2) + "\n")

    notes = ["## Draft notes", ""]
    notes += [f"- {n}" for n in post["notes"]] or ["- (none from the writer)"]
    if sheet["conflicts"]:
        notes += ["", "**Conflicting reports:**"] + [f"- {x}" for x in sheet["conflicts"]]
    if sheet["sensitive"]:
        notes += ["", f"**⚠️ Sensitive — extra review:** {sheet['sensitive_reason']}"]
    if sheet["press_mentions"]:
        notes += ["", "**SCAIO/Jimmy in the press** (the site has no press list — decide where this goes):"] \
            + [f"- {x}" for x in sheet["press_mentions"]]
    if rendered.warnings:
        notes += ["", "**Automated checks (warnings):**"] + [f"- {w}" for w in rendered.warnings]
    if dropped:
        notes += ["", f"**Dropped claims** ({len(dropped)} couldn't be verified against the source text):"] \
            + [f'- {f["claim"]} — {f["why"]}' for f in dropped]
    if fetch_notes:
        notes += ["", "**Sources skipped:**"] + [f"- {n}" for n in fetch_notes]
    if tips:
        notes += ["", "**Leads seen but not readable** (Google News redirects — not cited):"] \
            + [f"- {t['title']}" for t in tips[:15]]
    notes += ["", f"_Verified facts used: {len(verified)} from {len(rendered.sources)} sources. {USAGE}._"]
    notes_md = "\n".join(notes)
    (build / "draft_notes.md").write_text(notes_md)
    (TMP / "scaio_draft_notes.md").write_text(notes_md)

    manifest = {
        "mode": mode, "date": d.isoformat(), "slug": slug, "title": post["title"],
        "dek": post["dek"], "url": url, "article": filename, "social_file": f"social/queue/{social_name}",
        "files": [filename, "index.html", f"social/queue/{social_name}"],
        "timely": mode == "event", "sensitive": sheet["sensitive"],
        "social": {p: post["social"][p] for p in c["platforms"]},
        "item_ids": used_item_ids, "usage": str(USAGE),
    }
    (build / "manifest.json").write_text(json.dumps(manifest, indent=2))
    return build


def draft(mode: str) -> Path | None:
    load_env()
    seen = load_seen()
    topic, extra_urls = None, []
    if mode == "evergreen":
        topic, extra_urls = plan_evergreen(seen)
        items = select_items(mode, seen)[:4]
    else:
        items = select_items(mode, seen)
    if not items and not extra_urls:
        print(f"quiet: no unused items in the {mode} window")
        return None
    sources, fetch_notes, tips = gather_sources(items, extra_urls)
    if not sources:
        print("quiet: nothing readable to cite")
        return None
    print(f"drafting from {len(sources)} sources ({len(tips)} unreadable leads)")

    sheet = build_fact_sheet(mode, sources, tips, topic)
    verified, dropped = verify_facts(sheet["facts"], sources)
    print(f"fact sheet: {len(sheet['facts'])} facts, {len(verified)} verified, {len(dropped)} dropped")
    if not sheet["substantive"] or len(verified) < 3:
        print(f"quiet: {sheet['skip_reason'] or 'fewer than 3 verified facts'}")
        return None

    facts = {f["id"]: f for f in verified}
    post, errors = None, None
    for attempt in range(2):
        post = write_post(mode, verified, sources, sheet, errors, post)
        rendered = render_body(post["blocks"], facts, sources, SITE_URL)
        errors = rendered.errors + check_social(post["social"], cfg()["platforms"])
        if not errors:
            break
        print(f"attempt {attempt + 1}: {len(errors)} rule violations — {errors[:3]}")
    if errors:
        raise RuntimeError("draft still breaks editorial rules after a retry: " + "; ".join(errors))

    used = sorted({i for s in rendered.sources for i in s.get("item_ids", [])})
    build = stage(mode, post, rendered, sheet, dropped, fetch_notes, tips, verified, sources, used)
    print(f"staged: {build}")
    return build


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=list(MODES), required=True)
    args = ap.parse_args()
    try:
        result = draft(args.mode)
    except Exception as e:
        print(f"error: {e}", file=sys.stderr)
        sys.exit(1)
    sys.exit(0 if result else QUIET)
