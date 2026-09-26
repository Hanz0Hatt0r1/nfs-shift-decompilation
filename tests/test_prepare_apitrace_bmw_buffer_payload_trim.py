import json
from pathlib import Path

from tools.prepare_apitrace_bmw_buffer_payload_trim import build_callset


def _report(tmp_path: Path) -> dict:
    return {
        "format": "SHIFT.APITRACEUniqueBMWGeometry/1",
        "callset": [10, 20, 30],
        "resources": {
            "vertex_buffers": [
                {
                    "pointer": "0x100",
                    "creation": {"call": 100},
                    "lifecycle": {
                        "lock_calls": [101, 201],
                        "unlock_calls": [105, 205],
                        "release_calls": [200],
                    },
                }
            ],
            "index_buffers": [
                {
                    "pointer": "0x200",
                    "creation": {"call": 110},
                    "lifecycle": {
                        "lock_calls": [111, 211],
                        "unlock_calls": [115, 215],
                        "release_calls": [210],
                    },
                }
            ],
        },
    }


def test_active_creation_lifecycle_is_filtered_by_release(tmp_path: Path):
    plan = build_callset(_report(tmp_path))
    assert plan["callset"] == [10, 20, 30, 100, 105, 110, 115]
    assert plan["ready_for_payload_trim"] is False
    # Only the first lock/unlock belongs to the active creation lifetime.
    assert plan["resources"][0]["lock_calls"] == [101]
    assert plan["resources"][0]["unlock_calls"] == [105]
    assert plan["resources"][1]["lock_calls"] == [111]
    assert plan["resources"][1]["unlock_calls"] == [115]


def test_geometry_reports_with_complete_lifetimes_are_ready():
    report = {
        "format": "SHIFT.APITRACEUniqueBMWGeometry/1",
        "callset": [],
        "resources": {
            "vertex_buffers": [
                {
                    "pointer": "0x100",
                    "creation": {"call": 100},
                    "lifecycle": {"lock_calls": [101], "unlock_calls": [102], "release_calls": []},
                }
            ],
            "index_buffers": [
                *[
                    {
                        "pointer": hex(0x200 + i),
                        "creation": {"call": 110 + i},
                        "lifecycle": {"lock_calls": [120 + i], "unlock_calls": [130 + i], "release_calls": []},
                    }
                    for i in range(6)
                ]
            ],
        },
    }
    plan = build_callset(report)
    assert plan["ready_for_payload_trim"] is True
    assert plan["callset_count"] == 21
