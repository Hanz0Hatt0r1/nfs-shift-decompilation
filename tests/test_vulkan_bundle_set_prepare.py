import json
from pathlib import Path

import vulkan_bundle_set_prepare as prepare


def _write_set(root: Path, paths=("draws/submesh_000", "draws/submesh_001")):
    root.mkdir(parents=True, exist_ok=True)
    draws = []
    for index, relative in enumerate(paths):
        child = root / relative
        child.mkdir(parents=True, exist_ok=True)
        draws.append({
            "draw_order": index,
            "source_submesh_index": index,
            "bundle_path": relative,
            "ready": True,
        })
    manifest = {
        "format": "SHIFT.BMWVulkanBundleSet/1",
        "ready": True,
        "blocking_reasons": [],
        "draw_count": len(draws),
        "draws": draws,
    }
    (root / "bundle_set_manifest.json").write_text(
        json.dumps(manifest), encoding="utf-8"
    )
    (root / "bundle_set.paths").write_text(
        "".join(f"{path}\n" for path in paths), encoding="utf-8"
    )


def _ready_runner(calls):
    def run(child, **kwargs):
        calls.append((Path(child), kwargs))
        Path(child, "spirv_report.json").write_text(
            json.dumps({"format": "SHIFT.VulkanBundleSPIRV/1", "ready": True}),
            encoding="utf-8",
        )
        Path(child, "vulkan_interface.json").write_text(
            json.dumps({"format": "SHIFT.BMWVulkanInterfaceGate/1", "ready": True}),
            encoding="utf-8",
        )
        return {
            "format": "SHIFT.BMWVulkanRunner/1",
            "status": "ready",
            "ready": True,
            "blocking_reasons": [],
        }
    return run


def test_prepare_bundle_set_runs_every_draw_in_order(tmp_path, monkeypatch):
    _write_set(tmp_path)
    calls = []
    monkeypatch.setattr(prepare, "run_bmw_vulkan_bundle", _ready_runner(calls))

    result = prepare.prepare_bmw_vulkan_bundle_set(
        tmp_path, validator="fake-validator"
    )

    assert result["ready"] is True
    assert result["draw_count"] == 2
    assert [row["bundle_path"] for row in result["draws"]] == [
        "draws/submesh_000",
        "draws/submesh_001",
    ]
    assert [call[0].relative_to(tmp_path).as_posix() for call in calls] == [
        "draws/submesh_000",
        "draws/submesh_001",
    ]
    assert all(call[1]["prepare_only"] is True for call in calls)
    assert all(call[1]["validator"] == "fake-validator" for call in calls)
    persisted = json.loads(
        (tmp_path / "bundle_set_prepare.json").read_text(encoding="utf-8")
    )
    assert persisted["format"] == prepare.FORMAT
    assert persisted["ready"] is True


def test_prepare_bundle_set_fails_closed_on_child_gate(tmp_path, monkeypatch):
    _write_set(tmp_path)
    calls = []

    def runner(child, **kwargs):
        index = len(calls)
        calls.append(Path(child))
        if index == 1:
            return {
                "format": "SHIFT.BMWVulkanRunner/1",
                "status": "blocked",
                "ready": False,
                "blocking_reasons": ["vulkan-interface:missing-2d-resource:s2"],
            }
        Path(child, "spirv_report.json").write_text("{}", encoding="utf-8")
        Path(child, "vulkan_interface.json").write_text("{}", encoding="utf-8")
        return {
            "format": "SHIFT.BMWVulkanRunner/1",
            "status": "ready",
            "ready": True,
            "blocking_reasons": [],
        }

    monkeypatch.setattr(prepare, "run_bmw_vulkan_bundle", runner)
    result = prepare.prepare_bmw_vulkan_bundle_set(tmp_path)

    assert result["ready"] is False
    assert result["draws"][0]["ready"] is True
    assert result["draws"][1]["ready"] is False
    assert (
        "bundle-set-prepare:draw-1:"
        "vulkan-interface:missing-2d-resource:s2"
    ) in result["blocking_reasons"]


def test_prepare_bundle_set_blocks_draw_order_mismatch_before_running(tmp_path, monkeypatch):
    _write_set(tmp_path)
    (tmp_path / "bundle_set.paths").write_text(
        "draws/submesh_001\ndraws/submesh_000\n", encoding="utf-8"
    )
    called = False

    def runner(*args, **kwargs):
        nonlocal called
        called = True
        raise AssertionError("runner must not execute invalid draw order")

    monkeypatch.setattr(prepare, "run_bmw_vulkan_bundle", runner)
    result = prepare.prepare_bmw_vulkan_bundle_set(tmp_path)

    assert result["ready"] is False
    assert "bundle-set-prepare:draw-order-path-mismatch:0" in result["blocking_reasons"]
    assert called is False


def test_prepare_bundle_set_rejects_path_traversal(tmp_path, monkeypatch):
    _write_set(tmp_path, paths=("../escape",))
    monkeypatch.setattr(
        prepare,
        "run_bmw_vulkan_bundle",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("unsafe path must be blocked")
        ),
    )
    result = prepare.prepare_bmw_vulkan_bundle_set(tmp_path)
    assert result["ready"] is False
    assert "bundle-set-prepare:unsafe-bundle-path:0" in result["blocking_reasons"]
