import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scaio_common import ai_hits  # noqa: E402
from scaio_monitor_sources import parse_bill_last_action, parse_meetings, score_item  # noqa: E402

MEETINGS = """<div>Week of September 14, 2026</div>
<p>Tuesday, September 15</p><p>No Meetings Scheduled.</p>
<p>Wednesday, September 16, 2026</p>
<p>10:00 am</p><p> -- Gressette Room 308 -- Special Senate Committee on Artificial Intelligence</p>
<a href="/agendas/126s16646.pdf">Agenda Available</a>
<p>1:00 pm</p><p> -- Blatt Room 433 -- EIA and Improvement Mechanisms Subcommittee</p>
<p>Thursday, September 17</p><p>2:00 pm</p><p> -- Room 105 -- Senate Finance</p>"""

BILL = """<title>2025-2026 Bill 788: Artificial Intelligence and Therapy - South Carolina Legislature Online</title>
<p>HISTORY OF LEGISLATIVE ACTIONS</p><table><tbody>
<tr><td>1/13/2026</td><td>Senate</td><td>Introduced and read first time (<a href="#">Senate Journal-page 53</a>)</td></tr>
<tr><td>4/30/2026</td><td>House</td><td>Referred to Committee on <span>Medical Affairs</span> (<a href="#">House Journal-page 155</a>)</td></tr>
</tbody></table>"""


def test_parse_meetings_finds_ai_committee_with_agenda():
    ms = parse_meetings(MEETINGS)
    ai = [m for m in ms if "Artificial Intelligence" in m["committee"]]
    assert len(ai) == 1
    assert ai[0]["date"] == "September 16, 2026" and ai[0]["time"] == "10:00 am"
    assert ai[0]["location"] == "Gressette Room 308"
    assert ai[0]["agenda_url"] == "https://www.scstatehouse.gov/agendas/126s16646.pdf"
    thursday = [m for m in ms if m["committee"] == "Senate Finance"][0]
    assert thursday["date"] == "September 17, 2026"     # year carried forward


def test_parse_bill_last_action():
    last = parse_bill_last_action(BILL)
    assert last == {"title": "Artificial Intelligence and Therapy", "date": "4/30/2026",
                    "body": "House", "action": "Referred to Committee on Medical Affairs"}


def test_ai_keyword_is_case_sensitive_for_AI():
    assert ai_hits("Lawmakers weigh AI rules") == 1
    assert ai_hits("The mayor said aid would arrive") == 0
    assert ai_hits("Deepfake ads and artificial intelligence") == 2


def _item(title, summary=""):
    return {"title": title, "summary": summary, "primary": False, "event": False}


def test_score_requires_ai_and_relevance():
    local = {"id": "x", "type": "rss", "sc_local": True}
    assert score_item(_item("High school football scores"), local) is None
    kept = score_item(_item("Senate panel studies AI rules"), local)
    assert kept and 1 in kept["pillars"] and kept["sc_relevant"]
    national = {"id": "y", "type": "rss"}
    assert score_item(_item("AI startup raises money in Ohio"), national) is None
    fed_item = {**_item("Executive order on AI preempts state laws"), "primary": True}
    fed = score_item(fed_item, {"id": "z", "type": "rss", "pillar": 3})
    assert fed and 3 in fed["pillars"]
