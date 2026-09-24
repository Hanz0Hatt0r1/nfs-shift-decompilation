import json
import struct
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.collect_meb_evidence import build_parser, collect


def synthetic_color_meb() -> bytes:
    data = bytearray()
    data += struct.pack(">I", 1)
    data += struct.pack(">I", 0)
    data += b"x\x00"
    while len(data) % 4:
        data += b"\x00"
    data += struct.pack("<III", 1, 2, 0)
    data += b"\x00" * 40
    data += struct.pack("<III", 4, 6, 0)
    data += bytes((10, 20, 30, 255))
    data += struct.pack("<III", 4, 6, 1)
    data += bytes((40, 50, 60, 255))
    return bytes(data)


def test_collector_creates_small_self_describing_color_bundle(tmp_path):
    game = tmp_path / "game"
    game.mkdir()
    (game / "cars").mkdir()
    meb_path = game / "cars" / "body.meb"
    meb_path.write_bytes(synthetic_color_meb())

    output = tmp_path / "shift_meb_evidence.zip"
    args = build_parser().parse_args([
        str(game),
        "--output",
        str(output),
    ])

    assert collect(args) == 0
    assert output.exists()

    with zipfile.ZipFile(output) as zf:
        names = set(zf.namelist())
        assert "README.txt" in names
        assert "summary.json" in names
        assert "archives.json" in names
        assert "resources.jsonl" in names
        assert "errors.json" in names
        assert "descriptor_triple_proofs.json" in names
        assert "resources/" in "\n".join(names)

        summary = json.loads(zf.read("summary.json"))
        assert summary["scan"]["direct_meb_files"] == 1
        assert summary["scan"]["bff_files"] == 0
        assert summary["scan"]["meb_resources"] == 1
        assert summary["scan"]["meb_resources_with_color"] == 1
        assert summary["scan"]["errors"] == 0

        rows = [
            json.loads(line)
            for line in zf.read("resources.jsonl").decode("utf-8").splitlines()
            if line
        ]
        assert len(rows) == 1
        resource = rows[0]
        assert resource["source"]["kind"] == "direct-meb"
        assert resource["color_properties_found"] == ["460", "461"]

        rid = resource["id"]
        assert zf.read(f"resources/{rid}/460/descriptor.bin") == bytes.fromhex(
            "040000000600000000000000"
        )
        assert zf.read(f"resources/{rid}/461/descriptor.bin") == bytes.fromhex(
            "040000000600000001000000"
        )
        assert zf.read(f"resources/{rid}/460/payload.bin") == bytes((10, 20, 30, 255))
        assert zf.read(f"resources/{rid}/461/payload.bin") == bytes((40, 50, 60, 255))

        color460 = json.loads(zf.read(f"resources/{rid}/460/color_abi.json"))
        color461 = json.loads(zf.read(f"resources/{rid}/461/color_abi.json"))
        assert color460["property_id"] == "460"
        assert color461["property_id"] == "461"
        assert color460["source"]["decoded_stream_matches_payload_status"] == "observed"
        assert color461["source"]["decoded_stream_matches_payload_status"] == "observed"


def test_collector_can_continue_after_bad_meb_and_report_error(tmp_path):
    game = tmp_path / "game"
    game.mkdir()
    (game / "broken.meb").write_bytes(b"not-a-meb")

    output = tmp_path / "errors.zip"
    args = build_parser().parse_args([
        str(game),
        "--output",
        str(output),
    ])

    assert collect(args) == 0
    with zipfile.ZipFile(output) as zf:
        summary = json.loads(zf.read("summary.json"))
        errors = json.loads(zf.read("errors.json"))
        assert summary["scan"]["meb_resources"] == 0
        assert summary["scan"]["errors"] == 1
        assert errors[0]["source_kind"] == "direct-meb"


def test_collector_fail_on_error_returns_nonzero(tmp_path):
    game = tmp_path / "game"
    game.mkdir()
    (game / "broken.meb").write_bytes(b"not-a-meb")

    output = tmp_path / "errors.zip"
    args = build_parser().parse_args([
        str(game),
        "--output",
        str(output),
        "--fail-on-error",
    ])

    assert collect(args) == 1
