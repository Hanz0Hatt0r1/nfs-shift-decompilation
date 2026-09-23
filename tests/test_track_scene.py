from resource_formats import parse_sgb
from track_scene import build_track_scene_manifest


def _chunk(tag, payload):
    return tag[::-1].encode("ascii") + len(payload).to_bytes(4, "little") + payload


def test_sgb_resource_refs_keep_chunk_provenance():
    data = b" \x42\x47\x53" + (0x10).to_bytes(4, "little") + (3).to_bytes(4, "little") + (0).to_bytes(4, "little")
    payload = b"tracks/Alpental/grid1_02.meb\x00TRACKS/GRID2.BMT\x00surface.dds\x00"
    data += _chunk("NODE", payload)
    data += _chunk("END ", b"\x00\x00\x00\x00")
    parsed = parse_sgb(data)
    assert len(parsed["resource_refs"]) == 3
    meb = next(x for x in parsed["resource_refs"] if x["extension"] == ".meb")
    assert meb["kind"] == "geometry"
    assert meb["encoding"] == "ascii"
    assert meb["offset"] >= 24


def test_track_scene_manifest_resolves_exact_and_basename_refs():
    data = b" \x42\x47\x53" + (0x10).to_bytes(4, "little") + (3).to_bytes(4, "little") + (0).to_bytes(4, "little")
    data += _chunk("NODE", b"tracks/a/body.meb\x00shared.dds\x00")
    data += _chunk("END ", b"\x00\x00\x00\x00")
    parsed = parse_sgb(data)
    resources = [
        {"path": "tracks/a/body.meb", "analysis": {"format": "MEB"}},
        {"path": "textures/shared.dds", "analysis": {"format": "DDS"}},
    ]
    scene = build_track_scene_manifest(parsed, resources)
    assert scene["stats"]["geometry_refs"] == 1
    assert scene["stats"]["texture_refs"] == 1
    assert scene["stats"]["unresolved_refs"] == 0
    assert scene["placement"]["status"] == "unknown"


def test_track_scene_manifest_marks_missing_resources():
    data = b" \x42\x47\x53" + (0x10).to_bytes(4, "little") + (3).to_bytes(4, "little") + (0).to_bytes(4, "little")
    data += _chunk("NODE", b"tracks/a/missing.csm\x00")
    data += _chunk("END ", b"\x00\x00\x00\x00")
    scene = build_track_scene_manifest(parse_sgb(data), [])
    assert scene["stats"]["unresolved_refs"] == 1
    assert scene["unresolved"][0]["kind"] == "collision"
