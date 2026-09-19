"""Shared helpers for the SCAIO content agent: paths, env, HTTP, text extraction,
keyword matching, and the seen-item state file."""
from __future__ import annotations

import hashlib
import json
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
TMP = ROOT / ".tmp"
DIRECTIVE = ROOT / "directives" / "scaio_content_agent.md"
SOURCES_YAML = ROOT / "directives" / "scaio_sources.yaml"
SEEN_PATH = TMP / "scaio_seen.json"
REFERENCE_ARTICLE = "scaio-article-everywhere-at-once.html"
SITE_URL = "https://www.scaio.org"

USER_AGENT = "Mozilla/5.0 (compatible; SCAIO-monitor/1.0; +https://www.scaio.org)"

# ── Env ────────────────────────────────────────────────────────────────

def load_env() -> None:
    """Fill os.environ from repo .env then ~/.env (local runs). Never overrides
    variables already set, so Actions secrets win."""
    for path in (ROOT / ".env", Path.home() / ".env"):
        if not path.exists():
            continue
        for line in path.read_text(errors="ignore").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            key = key.strip().removeprefix("export ").strip()
            if not re.fullmatch(r"[A-Z_][A-Z0-9_]*", key):
                continue
            val = val.strip().strip('"').strip("'")
            os.environ.setdefault(key, val)


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def today() -> str:
    return now_utc().date().isoformat()


def item_id(key: str) -> str:
    return hashlib.sha1(key.encode()).hexdigest()[:16]


# ── HTTP + text ────────────────────────────────────────────────────────

def http_get(url: str, timeout: int = 25, retries: int = 2) -> requests.Response:
    last: Exception | None = None
    for attempt in range(retries + 1):
        try:
            r = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=timeout)
            if r.status_code >= 500 and attempt < retries:
                time.sleep(2 * (attempt + 1))
                continue
            return r
        except requests.RequestException as e:
            last = e
            time.sleep(2 * (attempt + 1))
    raise last  # type: ignore[misc]


def html_to_text(html: str, url: str = "") -> str:
    """Main-content text of an HTML page. trafilatura first, crude fallback."""
    try:
        import trafilatura
        text = trafilatura.extract(html, url=url or None, include_comments=False,
                                   include_tables=True, favor_recall=True)
        if text and len(text) > 300:
            return text
    except Exception:
        pass
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "nav", "header", "footer", "noscript"]):
        tag.decompose()
    return re.sub(r"\n\s*\n+", "\n\n", soup.get_text("\n")).strip()


def fetch_text(url: str) -> tuple[str | None, str]:
    """(text, status). text is None when unreachable, paywalled or too thin to cite."""
    try:
        r = http_get(url)
    except Exception as e:
        return None, f"unreachable ({type(e).__name__})"
    if r.status_code != 200:
        return None, f"HTTP {r.status_code}"
    ctype = r.headers.get("content-type", "")
    if "pdf" in ctype or url.lower().endswith(".pdf"):
        try:
            import io
            from pypdf import PdfReader
            reader = PdfReader(io.BytesIO(r.content))
            text = "\n".join((p.extract_text() or "") for p in reader.pages)
        except Exception as e:
            return None, f"pdf unreadable ({type(e).__name__})"
    else:
        text = html_to_text(r.text, url)
    if len(text) < 400:
        return None, "too little readable text (paywall or script-rendered)"
    return text, "ok"


# ── Keywords ───────────────────────────────────────────────────────────

# "AI" is matched case-sensitively so "said"/"aid" don't count.
AI_PATTERNS = [
    re.compile(r"(?i)\bartificial intelligence\b"),
    re.compile(r"\bA\.?I\.?(?=[\s,.;:'’)-]|$)"),
    re.compile(r"(?i)\bmachine learning\b"),
    re.compile(r"(?i)\bdeep ?fakes?\b"),
    re.compile(r"(?i)\bsynthetic media\b"),
    re.compile(r"(?i)\balgorithm(ic|s)?\b"),
    re.compile(r"(?i)\bgenerative\b"),
    re.compile(r"(?i)\bchatbots?\b|\bChatGPT\b|\blarge language model"),
    re.compile(r"(?i)\bdata cent(er|re)s?\b"),
]

SC_PATTERN = re.compile(
    r"South Carolina|\bS\.C\.|\bSC\b|Palmetto State|Charleston|Greenville|"
    r"Spartanburg|Myrtle Beach|Rock Hill|Florence|Orangeburg|Aiken|Beaufort|"
    r"Clemson|scstatehouse|McMaster|Statehouse"
)

PILLAR_PATTERNS = {
    1: re.compile(r"(?i)\b(senate|house|bill|committee|lawmakers?|legislat\w*|"
                  r"general assembly|statehouse|senator|representative|sen\.|rep\.)"),
    2: re.compile(r"(?i)\b(agenc(y|ies)|department|procure\w*|school district|schools?|"
                  r"county|city of|municipal|governor|state government|pilot program|"
                  r"public (sector|services))\b"),
    3: re.compile(r"(?i)\b(other states|federal|congress|white house|executive order|"
                  r"preempt\w*|FTC|FCC|NIST|federal register|trump|washington|"
                  r"colorado|california|texas|utah|georgia|north carolina)\b"),
}

PRESS_PATTERN = re.compile(r"\bSCAIO\b|South Carolina Artificial Intelligence Observatory|Jimmy Ardis")


def ai_hits(text: str) -> int:
    return sum(1 for p in AI_PATTERNS if p.search(text))


def classify_pillars(text: str, default: int | None) -> list[int]:
    pillars = {default} if default else set()
    for n, pat in PILLAR_PATTERNS.items():
        if pat.search(text):
            pillars.add(n)
    return sorted(pillars) or [4]


# ── Seen state ─────────────────────────────────────────────────────────

def load_seen() -> dict:
    if SEEN_PATH.exists():
        return json.loads(SEEN_PATH.read_text())
    return {}


def save_seen(seen: dict, keep_days: int = 90) -> None:
    TMP.mkdir(exist_ok=True)
    cutoff = now_utc().timestamp() - keep_days * 86400
    pruned = {
        k: v for k, v in seen.items()
        if datetime.fromisoformat(v["first_seen"]).timestamp() >= cutoff
    }
    SEEN_PATH.write_text(json.dumps(pruned, indent=1, sort_keys=True))


def days_ago(iso: str) -> float:
    return (now_utc() - datetime.fromisoformat(iso)).total_seconds() / 86400
