from pathlib import Path

import tools.prepare_apitrace_bmw_buffer_payload_trim as mod
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


def test_active_creation_lifecycle_is_filtered_by_release():
    plan = build_callset(_report(Path(".")))
    assert plan["callset"] == [10, 20, 30, 100, 101, 105, 110, 111, 115]
    assert plan["ready_for_payload_trim"] is False
    assert plan["resources"][0]["lock_calls"] == [101]
    assert plan["resources"][0]["unlock_calls"] == [105]
    assert plan["resources"][1]["lock_calls"] == [111]
    assert plan["resources"][1]["unlock_calls"] == [115]


def test_complete_lifetimes_are_ready_and_include_fake_memcpy(monkeypatch):
    report = {
        "format": "SHIFT.APITRACEUniqueBMWGeometry/1",
        "callset": [],
        "resources": {
            "vertex_buffers": [
                {
                    "pointer": "0x100",
                    "creation": {"call": 100},
                    "lifecycle": {
                        "lock_calls": [101],
                        "unlock_calls": [102],
                        "release_calls": [],
                    },
                }
            ],
            "index_buffers": [
                *[
                    {
                        "pointer": hex(0x200 + i),
                        "creation": {"call": 110 + i},
                        "lifecycle": {
                            "lock_calls": [120 + i],
                            "unlock_calls": [130 + i],
                            "release_calls": [],
                        },
                    }
                    for i in range(6)
                ]
            ],
        },
    }

    monkeypatch.setattr(
        mod,
        "_fake_memcpy_calls_near_unlock",
        lambda trace, apitrace, unlock_call, window=4: [unlock_call - 1],
    )
    plan = build_callset(report, trace=Path("/tmp/SHIFT.trace"))
    assert plan["ready_for_payload_trim"] is True
    assert plan["callset_count"] == 22
    assert plan["resources"][0]["fake_memcpy_calls_by_unlock"] == {"102": [101]}
    assert plan["resources"][6]["fake_memcpy_calls_by_unlock"] == {"130": [129]}


def test_missing_fake_memcpy_blocks_trim(monkeypatch):
    report = {
        "format": "SHIFT.APITRACEUniqueBMWGeometry/1",
        "callset": [],
        "resources": {
            "vertex_buffers": [
                {
                    "pointer": "0x100",
                    "creation": {"call": 100},
                    "lifecycle": {
                        "lock_calls": [101],
                        "unlock_calls": [102],
                        "release_calls": [],
                    },
                }
            ],
            "index_buffers": [
                {
                    "pointer": "0x200",
                    "creation": {"call": 110},
                    "lifecycle": {
                        "lock_calls": [120],
                        "unlock_calls": [130],
                        "release_calls": [],
                    },
                }
            ],
        },
    }

    monkeypatch.setattr(
        mod,
        "_fake_memcpy_calls_near_unlock",
        lambda trace, apitrace, unlock_call, window=4: (
            [] if unlock_call == 130 else [unlock_call + 1]
        ),
    )
    plan = build_callset(report, trace=Path("/tmp/SHIFT.trace"))
    assert plan["ready_for_payload_trim"] is False
    assert plan["missing_fake_memcpy"] == [
        {
            "kind": "index_buffer",
            "pointer": "0x200",
            "creation_call": 110,
            "unlock_call": 130,
        }
    ]


def test_fake_memcpy_calls_are_discovered_from_bounded_dump(monkeypatch):
    monkeypatch.setattr(
        mod,
        "_dump_calls",
        lambda trace, apitrace, first, last: (
            "117 memcpy(dest = 0x3, src = 0x4, n = 8) = 0\\n"
            "118 IDirect3DDevice9::Lock(...) = D3D_OK\\n"
            "119 memcpy(dest = 0x1, src = 0x2, n = 12) = 0\\n"
            "120 IDirect3DIndexBuffer9::Unlock(this = 0x200, pLength = 12) = D3D_OK\\n"
            "121 memcpy(dest = 0x5, src = 0x6, n = 8) = 0\\n"
        ),
    )
    assert mod._fake_memcpy_calls_near_unlock(
        Path("/tmp/SHIFT.trace"), "apitrace", 120, 4
    ) == [119]
