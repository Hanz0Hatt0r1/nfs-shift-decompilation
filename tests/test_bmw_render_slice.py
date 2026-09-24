from bmw_render_slice import select_bmw_packets


def _golden():
    return {
        "format": "SHIFT.BMWGoldenAssetManifest/1",
        "golden": {
            "resource": "vehicles/bmw/body.meb",
            "resource_sha256": "abc",
        },
    }


def _packet(sha="abc", path="vehicles/bmw/body.meb"):
    return {
        "mesh": {
            "ref": path,
            "resolved": {"path": path, "resource_sha256": sha},
        },
        "submeshes": [],
    }


def test_bmw_render_slice_selects_exact_resource_and_parallel_outputs():
    binding = {
        "format": "SHIFT.RenderBinding/1",
        "packets": [_packet(sha="other", path="vehicles/other.meb"), _packet()],
        "static_draws": [{"id": 1}, {"id": 2}],
        "render_commands": [{"id": 3}, {"id": 4}],
    }
    report = select_bmw_packets(binding, _golden())
    assert report["ready"] is True
    assert report["packet_index"] == 1
    assert report["static_draw"] == {"id": 2}
    assert report["render_command"] == {"id": 4}


def test_bmw_render_slice_blocks_identity_conflict():
    binding = {
        "format": "SHIFT.RenderBinding/1",
        "packets": [_packet(sha="wrong"), _packet()],
        "static_draws": [{}, {}],
        "render_commands": [{}, {}],
    }
    report = select_bmw_packets(binding, _golden())
    assert report["ready"] is True


def test_bmw_render_slice_blocks_path_sha_disagreement():
    binding = {
        "format": "SHIFT.RenderBinding/1",
        "packets": [_packet(sha="wrong"), _packet(sha="abc", path="vehicles/other.meb")],
    }
    report = select_bmw_packets(binding, _golden())
    assert report["ready"] is False
    assert "golden:identity-conflict" in report["blocking_reasons"]