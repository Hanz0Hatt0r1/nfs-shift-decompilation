from pathlib import Path

import tools.verify_specialized_provider_capture_bundle as tool


def test_parser_requires_directory():
    parser = tool.build_parser()
    try:
        parser.parse_args([])
    except SystemExit:
        return
    raise AssertionError("directory argument was not required")


def test_parser_accepts_reset_events_and_output():
    parser = tool.build_parser()
    args = parser.parse_args(
        [
            "capture",
            "--reset-events",
            "events.jsonl",
            "-o",
            "manifest.json",
        ]
    )

    assert args.directory == Path("capture")
    assert args.reset_events == Path("events.jsonl")
    assert args.output == Path("manifest.json")


def test_cli_pre_only_directory_returns_success(tmp_path: Path, capsys):
    pre = tmp_path / "provider_pre_0_000001.json"
    import json

    pre.write_text(
        json.dumps(
            {
                "provider_id": 0,
                "stage": "pre-solve-provider",
                "workspace": [0.0] * 1190,
                "output_vector": [0.0] * 40,
                "row_pointers": [],
                "frame_index": 1,
            }
        ),
        encoding="utf-8",
    )

    result = tool.main([str(tmp_path)])

    output = capsys.readouterr().out
    assert result == 0
    assert '"bundle_count": 1' in output
    assert '"ready": true' in output


def test_cli_writes_output_manifest(tmp_path: Path):
    pre = tmp_path / "provider_pre_1_000001.json"
    import json

    pre.write_text(
        json.dumps(
            {
                "provider_id": 1,
                "stage": "pre-solve-provider",
                "workspace": [0.0] * 746,
                "output_vector": [0.0] * 34,
                "row_pointers": [],
                "frame_index": 2,
            }
        ),
        encoding="utf-8",
    )
    output = tmp_path / "manifest.json"

    result = tool.main(
        [
            str(tmp_path),
            "-o",
            str(output),
        ]
    )

    assert result == 0
    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["bundle_count"] == 1
    assert report["bundles"][0]["provider_id"] == 1
