import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scaio_render import (  # noqa: E402
    CARD_ANCHOR, add_homepage_card, build_page, check_social, quote_in_text,
    render_body, render_sources, verify_facts,
)

SRC_TEXT = ("The nine-member panel is chaired by Sen. Tom Young. Senators spent the morning on "
            "foundational questions, starting with what counts as AI. South Carolina currently "
            "has no legal definition of artificial intelligence, lawmakers said.")
SOURCES = {
    1: {"n": 1, "url": "https://example.com/a", "title": "Panel starts work", "outlet": "Live 5",
        "date_label": "September 16, 2026", "text": SRC_TEXT, "item_ids": ["i1"]},
    2: {"n": 2, "url": "https://example.com/b", "title": "Other", "outlet": "WIS",
        "date_label": "", "text": "Thirty-three states have adopted a definition of AI.", "item_ids": ["i2"]},
}
FACTS = {
    "F1": {"id": "F1", "claim": "Young chairs it", "source": 1, "quote": "chaired by Sen. Tom Young"},
    "F2": {"id": "F2", "claim": "33 states define AI", "source": 2, "quote": "Thirty-three states have adopted"},
}


def test_quote_in_text_tolerates_typography():
    assert quote_in_text("South Carolina currently has no legal definition", SRC_TEXT)
    assert quote_in_text("chaired by Sen. Tom Young", SRC_TEXT.replace("  ", " "))
    assert quote_in_text("what counts as AI—South", "what counts as AI - South")
    assert not quote_in_text("chaired by Sen. Shane Massey", SRC_TEXT)


def test_verify_facts_drops_unsupported_and_unfetched():
    facts = list(FACTS.values()) + [
        {"id": "F3", "claim": "made up", "source": 1, "quote": "the committee voted 9-0"},
        {"id": "F4", "claim": "no source", "source": 9, "quote": "anything"},
    ]
    ok, dropped = verify_facts(facts, SOURCES)
    assert [f["id"] for f in ok] == ["F1", "F2"]
    assert {d["id"] for d in dropped} == {"F3", "F4"}


def test_citations_number_by_first_use_and_backlink():
    blocks = [{"kind": "p", "text": "Thirty-three states act [F2]. Young chairs [F1]. Again [F2]."}]
    r = render_body(blocks, FACTS, SOURCES, "https://www.scaio.org")
    assert not r.errors
    assert '<sup><a href="#src-1" id="ref-1-a">1</a></sup>' in r.body_html
    assert '<sup><a href="#src-1" id="ref-1-b">1</a></sup>' in r.body_html
    assert [s["url"] for s in r.sources] == ["https://example.com/b", "https://example.com/a"]
    html = render_sources(r.sources)
    assert 'id="src-1"' in html and 'href="#ref-1-a"' in html


def test_unknown_citation_is_an_error():
    r = render_body([{"kind": "p", "text": "Claim [F9]."}], FACTS, SOURCES, "https://www.scaio.org")
    assert any("F9" in e for e in r.errors)


def test_quote_rules():
    ok = [{"kind": "p", "text": 'Lawmakers noted the state has "no legal definition of artificial intelligence" [F1].'}]
    assert not render_body(ok, FACTS, SOURCES, "https://www.scaio.org").errors
    fabricated = [{"kind": "p", "text": 'Young said "we will regulate AI next year" [F1].'}]
    assert render_body(fabricated, FACTS, SOURCES, "https://www.scaio.org").errors
    long = [{"kind": "p", "text": '"Senators spent the morning on foundational questions, starting with what counts as AI, lawmakers said on Wednesday" [F1].'}]
    assert any("over" in e for e in render_body(long, FACTS, SOURCES, "https://www.scaio.org").errors)
    twice = [{"kind": "p", "text": '"no legal definition of artificial intelligence" [F1]. '
                                   '"chaired by Sen. Tom Young" [F1].'}]
    assert any("second quote" in e for e in render_body(twice, FACTS, SOURCES, "https://www.scaio.org").errors)


def test_links_must_be_sources_or_site():
    good = [{"kind": "p", "text": "See [coverage](https://example.com/a) and [our primer](/learn/) [F1]."}]
    assert not render_body(good, FACTS, SOURCES, "https://www.scaio.org").errors
    bad = [{"kind": "p", "text": "See [this](https://evil.example/x) [F1]."}]
    assert render_body(bad, FACTS, SOURCES, "https://www.scaio.org").errors


def test_html_is_escaped():
    r = render_body([{"kind": "p", "text": "<script>x</script> **bold** [F1]"}], FACTS, SOURCES, "https://www.scaio.org")
    assert "<script>" not in r.body_html and "<strong>bold</strong>" in r.body_html


def test_social_limits():
    assert check_social({"linkedin": "x" * 100, "facebook": "y"}, ["linkedin", "facebook"]) == []
    errs = check_social({"linkedin": "x" * 3001, "facebook": "claim [F1]"}, ["linkedin", "facebook"])
    assert len(errs) == 2


REF = (Path(__file__).resolve().parents[2] / "scaio-article-everywhere-at-once.html").read_text()


def test_build_page_reuses_reference_template():
    page = build_page(REF, title="T & U", dek="Dek", description="Desc", tags=["Update", "SC Legislature"],
                      date_iso="2026-09-21", date_label="September 21, 2026", byline="SCAIO Staff",
                      body_html="<p>x</p>", sources_html="<li>s</li>", url="https://www.scaio.org/x.html")
    assert "<title>T &amp; U — SCAIO</title>" in page
    assert '<div class="site-bar">' in page and "navigator.js" in page and "plausible.io" in page
    assert page.count("<style>") == 1 and "fonts.googleapis.com/css2" in page
    assert 'rel="canonical" href="https://www.scaio.org/x.html"' in page


def test_homepage_card_inserted_first_and_idempotent():
    index = "<div>\n" + CARD_ANCHOR + '        <a class="card published" href="old.html">\n</div>'
    once = add_homepage_card(index, href="new.html", tag="Update · September 2026", title="New",
                             blurb="B", link_label="Read the update")
    assert once.index("new.html") < once.index("old.html")
    assert add_homepage_card(once, href="new.html", tag="t", title="New", blurb="B", link_label="l") == once
