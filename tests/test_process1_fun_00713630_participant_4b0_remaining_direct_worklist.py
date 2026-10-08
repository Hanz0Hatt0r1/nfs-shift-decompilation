import json
from pathlib import Path

EVIDENCE = Path(__file__).parents[1] / "evidence" / "fun_00713630_participant_4b0_remaining_direct_worklist.json"


def _payload():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_remaining_direct_site_inventory_is_exactly_seven():
    p = _payload()
    assert p["format"] == "SHIFT.Fun00713630Participant4b0RemainingDirectWorklist/1"
    rows = p["remaining_direct_displacement_sites"]
    assert len(rows) == 7
    assert [row["site"] for row in rows] == [
        "0x00487d2d",
        "0x005b0b1b",
        "0x005b0ea6",
        "0x00607f22",
        "0x0076019f",
        "0x00832f46",
        "0x0098e583",
    ]


def test_previous_rejections_do_not_reenter_worklist():
    sites = {row["site"] for row in _payload()["remaining_direct_displacement_sites"]}
    rejected = {
        "0x00748956",
        "0x007c48ae",
        "0x007c0fe2",
        "0x0051f81c",
        "0x0051f8d2",
        "0x004dbf73",
        "0x00482a5a",
        "0x00991650",
        "0x007a2006",
    }
    assert sites.isdisjoint(rejected)


def test_fail_closed_gate_and_provider_count_are_unchanged():
    a = _payload()["adjudication"]
    assert a["remaining_unjoined_direct_site_count"] == 7
    assert a["all_previously_rejected_direct_sites_excluded"] is True
    assert a["selected_participant_runtime_plus_0x4b0_writer_closed"] is False
    assert a["p1_1a_complete"] is False
    assert a["p1_1_complete"] is False
    assert a["contact_response_provider_removal_authorized"] is False
    assert a["external_provider_count"] == 7


def test_widening_is_forbidden_until_direct_surface_closes():
    rules = "\n".join(_payload()["rules"])
    assert "exact receiver provenance" in rules
    assert "numeric +0x4b0 equality is never sufficient" in rules
    assert "Only after this seven-site direct surface is exhausted" in rules
