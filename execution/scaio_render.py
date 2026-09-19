"""Deterministic half of drafting: fact verification, citation/quote rules, and
rendering a post in the site's article template. No network, no LLM — tested
in execution/tests/.

Citation markup used by the writer: a clause ends with [F3] or [F3,F7], where
F-ids are verified facts. Each fact points at one source; the renderer numbers
sources in order of first citation and emits the same footnote markup as the
reference article (<sup><a href="#src-N" id="ref-N-x">N</a></sup>).
"""
from __future__ import annotations

import html
import re
import unicodedata
from dataclasses import dataclass, field
from difflib import SequenceMatcher

QUOTE_MAX_WORDS = 14            # directive: quotes under 15 words
SOCIAL_LIMITS = {"linkedin": 3000, "facebook": 2000}   # facebook's real cap is ~63k; we self-limit


# ── Verification ───────────────────────────────────────────────────────

def normalize(s: str) -> str:
    s = unicodedata.normalize("NFKC", s)
    s = s.replace("\u2019", "'").replace("\u2018", "'").replace("\u201c", '"').replace("\u201d", '"')
    s = re.sub("[\u2014\u2013-]", " - ", s).replace("\u00a0", " ")
    return re.sub(r"\s+", " ", s).strip().lower()


def quote_in_text(quote: str, text: str, threshold: float = 0.92) -> bool:
    """True if quote appears in text verbatim (after normalization) or nearly so
    (tolerates whitespace/punctuation differences from HTML extraction)."""
    q, t = normalize(quote), normalize(text)
    if not q:
        return False
    if q in t:
        return True
    if len(q) < 25:
        return False
    # anchor on the quote's first 20 chars, then score the window
    anchor = q[:20]
    start = 0
    while (i := t.find(anchor, start)) != -1:
        window = t[i:i + len(q) + 20]
        m = SequenceMatcher(None, q, window, autojunk=False)
        if sum(b.size for b in m.get_matching_blocks()) / len(q) >= threshold:
            return True
        start = i + 1
    return False


def verify_facts(facts: list[dict], sources: dict[int, dict]) -> tuple[list[dict], list[dict]]:
    """Split facts into (verified, dropped). A fact survives only if its source
    was fetched and its supporting quote is found in that source's text."""
    ok, dropped = [], []
    for f in facts:
        src = sources.get(f.get("source"))
        if not src or not src.get("text"):
            dropped.append({**f, "why": "source not fetched"})
        elif not quote_in_text(f.get("quote", ""), src["text"]):
            dropped.append({**f, "why": "supporting quote not found in source"})
        else:
            ok.append(f)
    return ok, dropped


# ── Citations, quotes, links ───────────────────────────────────────────

CITE_RE = re.compile(r"\s*\[(F\d+(?:\s*,\s*F\d+)*)\]")
QUOTE_RE = re.compile("[\"\u201c]([^\"\u201c\u201d]{2,}?)[\"\u201d]")
LINK_RE = re.compile(r"\[([^\]]+)\]\((https?://[^)\s]+|mailto:[^)\s]+|/[^)\s]*|scaio-article-[^)\s]+)\)")


@dataclass
class Rendered:
    body_html: str = ""
    sources: list[dict] = field(default_factory=list)   # in citation order, with "n"
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def _inline(text: str) -> str:
    """Escape, then allow **bold**, *italic*, and [text](url)."""
    out = html.escape(text, quote=False)
    out = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", out)
    out = re.sub(r"(?<![*\w])\*(?!\s)(.+?)(?<!\s)\*(?!\*)", r"<em>\1</em>", out)
    out = LINK_RE.sub(lambda m: f'<a href="{html.escape(m.group(2))}">{m.group(1)}</a>', out)
    return out


def render_body(blocks: list[dict], facts: dict[str, dict], sources: dict[int, dict],
                site_url: str) -> Rendered:
    """Blocks → prose HTML with footnotes; enforces citation, quote and link rules."""
    res = Rendered()
    order: dict[int, int] = {}          # source key -> display number
    ref_counts: dict[int, int] = {}
    quoted_sources: dict[int, str] = {}
    allowed_links = {s["url"] for s in sources.values()}
    parts: list[str] = []

    def cite(match: re.Match) -> str:
        ids = [x.strip() for x in match.group(1).split(",")]
        nums = []
        for fid in ids:
            f = facts.get(fid)
            if not f:
                res.errors.append(f"citation {fid} is not a verified fact")
                continue
            key = f["source"]
            if key not in order:
                order[key] = len(order) + 1
            n = order[key]
            if n not in nums:
                nums.append(n)
        sups = []
        for n in nums:
            ref_counts[n] = ref_counts.get(n, 0) + 1
            letter = chr(ord("a") + ref_counts[n] - 1) if ref_counts[n] <= 26 else str(ref_counts[n])
            sups.append(f'<sup><a href="#src-{n}" id="ref-{n}-{letter}">{n}</a></sup>')
        return "".join(sups)

    def check_block(text: str) -> None:
        cited = [facts[x.strip()]["source"]
                 for m in CITE_RE.finditer(text) for x in m.group(1).split(",")
                 if x.strip() in facts]
        plain = CITE_RE.sub("", text)
        for q in QUOTE_RE.findall(plain):
            words = len(q.split())
            if words < 3:
                continue    # scare quotes / terms, not quotations
            if words > QUOTE_MAX_WORDS:
                res.errors.append(f'quote over {QUOTE_MAX_WORDS} words: "{q[:80]}"')
                continue
            home = next((s for s in cited if quote_in_text(q, sources[s].get("text", ""), 0.97)), None)
            if home is None:
                res.errors.append(f'quote not found verbatim in a source cited in the same paragraph: "{q}"')
            elif home in quoted_sources:
                res.errors.append(f'second quote from the same source ({sources[home]["url"]}): "{q}"')
            else:
                quoted_sources[home] = q
        for _, url in LINK_RE.findall(plain):
            if url.startswith(("mailto:", "/", "scaio-article-")) or url.startswith(site_url):
                continue
            if url not in allowed_links:
                res.errors.append(f"link to a URL that isn't a fetched source: {url}")
        if re.search(r"\d", re.sub(r"\[(F\d+(?:\s*,\s*F\d+)*)\]", "", text)) and not CITE_RE.search(text):
            res.warnings.append(f'paragraph with numbers but no citation: "{plain[:90]}…"')

    for b in blocks:
        kind, text = b.get("kind"), b.get("text", "")
        check_block(text)
        if kind == "h2":
            parts.append(f"      <h2>{_inline(CITE_RE.sub('', b.get('heading') or text))}</h2>")
        elif kind == "callout":
            body = CITE_RE.sub(cite, _inline_keep_cites(text))
            parts.append(
                '      <div class="sc-callout">\n'
                + (f'        <div class="kicker">{_inline(b["kicker"])}</div>\n' if b.get("kicker") else "")
                + (f'        <h2>{_inline(b["heading"])}</h2>\n' if b.get("heading") else "")
                + f"        <p>{body}</p>\n      </div>")
        else:
            parts.append(f"      <p>{CITE_RE.sub(cite, _inline_keep_cites(text))}</p>")

    for key, n in sorted(order.items(), key=lambda kv: kv[1]):
        res.sources.append({**sources[key], "n": n})
    res.body_html = "\n\n".join(parts)
    return res


def _inline_keep_cites(text: str) -> str:
    """_inline() but leave [F#] markers intact for the citation pass."""
    marks: list[str] = []

    def stash(m: re.Match) -> str:
        marks.append(m.group(0))
        return f"\ue000{len(marks) - 1}\ue001"

    out = _inline(CITE_RE.sub(stash, text))
    return re.sub("\ue000(\\d+)\ue001", lambda m: marks[int(m.group(1))], out)


def render_sources(sources: list[dict]) -> str:
    items = []
    for s in sources:
        n = s["n"]
        outlet = html.escape(s.get("outlet") or "")
        title = html.escape(s.get("title") or s["url"])
        date = html.escape(s.get("date_label") or "")
        host = html.escape(re.sub(r"^www\.", "", re.sub(r"^https?://([^/]+).*", r"\1", s["url"])))
        lead = f"{outlet}, " if outlet else ""
        items.append(
            f'          <li id="src-{n}">{lead}"{title}"{", " + date if date else ""}. '
            f'<a href="{html.escape(s["url"])}">{host}</a> '
            f'<a class="back-ref" href="#ref-{n}-a" aria-label="Back to reference {n}">&#8617;</a></li>')
    return "\n".join(items)


def check_social(social: dict[str, str], platforms: list[str]) -> list[str]:
    errs = []
    for p in platforms:
        text = social.get(p, "")
        if not text.strip():
            errs.append(f"missing {p} post")
        elif len(text) > SOCIAL_LIMITS[p]:
            errs.append(f"{p} post is {len(text)} chars (limit {SOCIAL_LIMITS[p]})")
        if CITE_RE.search(text):
            errs.append(f"{p} post contains citation markers")
    return errs


# ── Page assembly ──────────────────────────────────────────────────────

def _attr(s: str) -> str:
    return html.escape(s, quote=True)


def build_page(reference_html: str, *, title: str, dek: str, description: str, tags: list[str],
               date_iso: str, date_label: str, byline: str, body_html: str, sources_html: str,
               url: str) -> str:
    """Article page in the same template as the reference article: its <style>
    block, fonts, analytics and navigator widget are carried over verbatim."""
    style = re.search(r"<style>.*?</style>", reference_html, re.S).group(0)
    head_links = "\n".join(
        l for l in re.findall(r"^\s*<link [^>]+>\s*$", reference_html.split("</head>")[0], re.M)
        if "canonical" not in l)
    site_bar = re.search(r'<div class="site-bar">.*?</div>', reference_html, re.S).group(0)
    tag_spans = "\n".join(f'      <span class="meta-tag">{html.escape(t)}</span>' for t in tags)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{html.escape(title)} — SCAIO</title>
  <meta name="description" content="{_attr(description)}" />
  <meta name="author" content="{_attr(byline)}" />
  <meta property="og:title" content="{_attr(title)}" />
  <meta property="og:description" content="{_attr(dek)}" />
  <meta property="og:type" content="article" />
  <meta property="og:url" content="{_attr(url)}" />
  <meta property="article:published_time" content="{date_iso}" />
  <link rel="canonical" href="{_attr(url)}" />
{head_links}
  {style}
  <!-- Plausible analytics -->
  <script defer data-domain="scaio.org" src="https://plausible.io/js/script.js"></script>
</head>
<body>

  {site_bar}

  <article class="article-wrap">

    <div class="meta">
{tag_spans}
      <span class="meta-date"><time datetime="{date_iso}">{html.escape(date_label)}</time> · SCAIO Journal</span>
      <span class="meta-byline">By {html.escape(byline)}</span>
    </div>

    <h1>{html.escape(title)}</h1>

    <p class="dek">
      {html.escape(dek)}
    </p>

    <div class="prose">

{body_html}

      <section class="source-note" aria-labelledby="sources-heading">
        <strong id="sources-heading">Sources</strong>
        <ol>
{sources_html}
        </ol>
      </section>

    </div>

  </article>

  <script src="/assets/navigator.js" defer></script>
</body>
</html>
"""


CARD_ANCHOR = "        <!-- ── Published article ── -->\n"


def add_homepage_card(index_html: str, *, href: str, tag: str, title: str, blurb: str,
                      link_label: str) -> str:
    """Insert a Journal card at the top of the homepage grid (newest first)."""
    if CARD_ANCHOR not in index_html:
        raise ValueError("homepage Journal anchor comment not found — template changed?")
    if f'href="{href}"' in index_html:
        return index_html
    card = (f'{CARD_ANCHOR}'
            f'        <a class="card published" href="{_attr(href)}">\n'
            f'          <div class="article-tag live">{html.escape(tag)}</div>\n'
            f'          <h3>{html.escape(title)}</h3>\n'
            f'          <p>{html.escape(blurb)}</p>\n'
            f'          <span class="read-link">{html.escape(link_label)} →</span>\n'
            f'        </a>\n\n')
    return index_html.replace(CARD_ANCHOR, card, 1)
