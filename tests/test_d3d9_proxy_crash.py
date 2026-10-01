from native_capture.analyze_proxy_crash import analyze


def test_near_null_read_is_classified():
    report = analyze([{
        "format": "SHIFT.D3D9ProxyCrash/1",
        "exception_code": "0xc0000005",
        "exception_address": "0x0083a006",
        "exception_rva": "0x0043a006",
        "access_type": 0,
        "access_address": "0x00000018",
        "registers": {
            "eip": "0x0083a006",
            "ecx": "0x00000000",
            "edx": "0x00000000",
        },
        "main_image": {"base": "0x00400000", "size": 0x800000},
        "stack_words": ["0x0082a6a1", "0x12345678"],
    }])
    assert report["diagnosis"] == "game-code-near-null-access-violation"
    assert report["access_type"] == "read"
    assert report["main_image_stack_candidates"] == [{
        "address": "0x0082a6a1",
        "rva": "0x0042a6a1",
    }]


def test_non_access_violation_is_generic():
    report = analyze([{
        "format": "SHIFT.D3D9ProxyCrash/1",
        "exception_code": "0xc000001d",
        "exception_address": "0x00401000",
        "access_type": 8,
        "access_address": "0x00401000",
    }])
    assert report["diagnosis"] == "game-code-exception"
    assert report["access_type"] == "execute"


def test_empty_log_is_reported():
    report = analyze([])
    assert report["diagnosis"] == "malformed-or-empty-crash-log"
