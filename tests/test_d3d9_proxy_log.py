from native_capture.analyze_proxy_log import analyze_events


def test_passthrough_success():
    report = analyze_events([
        {"event": "proxy_direct3dcreate9", "mode": "passthrough"},
        {"event": "proxy_system_d3d9_ready"},
        {"event": "direct3dcreate9_result", "success": True},
    ])
    assert report["diagnosis"] == "passthrough-forwarding-ok"
    assert report["issues"] == []


def test_create_device_failure_is_named():
    report = analyze_events([
        {"event": "proxy_direct3dcreate9", "mode": "diagnostic"},
        {"event": "proxy_system_d3d9_ready"},
        {"event": "direct3dcreate9_result", "success": True},
        {"event": "create_device_result", "success": False, "hresult": "0x8876086c"},
    ])
    assert report["diagnosis"] == "device-creation-failure"
    issue = next(item for item in report["issues"] if item["kind"] == "create-device-failed")
    assert issue["hresult_name"] == "D3DERR_INVALIDCALL"


def test_successful_present_marks_path_alive():
    report = analyze_events([
        {"event": "proxy_direct3dcreate9", "mode": "capture"},
        {"event": "direct3dcreate9_result", "success": True},
        {"event": "create_device_result", "success": True},
        {"event": "present_result", "success": True, "hresult": "0x00000000"},
    ])
    assert report["diagnosis"] == "d3d9-presentation-path-alive"


def test_device_lost_present_is_reported():
    report = analyze_events([
        {"event": "proxy_direct3dcreate9", "mode": "diagnostic"},
        {"event": "direct3dcreate9_result", "success": True},
        {"event": "create_device_result", "success": True},
        {"event": "present_result", "success": False, "hresult": "0x88760868"},
    ])
    assert report["diagnosis"] == "device-present-failure"
    issue = next(item for item in report["issues"] if item["kind"] == "present-always-failing")
    assert issue["hresult_name"] == "D3DERR_DEVICELOST"


def test_parse_error_blocks_clean_report():
    report = analyze_events([], parse_errors=2)
    assert report["parse_error_count"] == 2
    assert any(item["kind"] == "malformed-jsonl" for item in report["issues"])
