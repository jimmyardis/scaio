import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scaio_link_check import check, check_internal, iter_links  # noqa: E402
from scaio_common import ROOT  # noqa: E402


def test_iter_links_finds_nested_resources():
    data = {"branches": [{"resources": {"curious": [{"title": "a", "url": "x"}, {"title": "b", "url": None}]}}]}
    assert [d["title"] for d in iter_links(data)] == ["a", "b"]


def test_internal_paths_resolve_against_repo():
    assert check_internal("learn/primer-01-llm.html") == ("ok", "")
    assert check_internal("policy/") == ("ok", "")
    assert check_internal("index.html#journal") == ("ok", "")
    assert check_internal("learn/no-such-primer.html")[0] == "dead"


def test_missing_url_is_not_a_failure():
    assert check(None) == ("no-link", "")


def test_map_data_internal_links_all_exist():
    data = json.loads((ROOT / "learn" / "map-data.json").read_text())
    internal = [d["url"] for d in iter_links(data) if d["url"] and not d["url"].startswith("http")]
    assert internal
    assert all(check_internal(u)[0] == "ok" for u in internal)
