from pathlib import Path

import tools.verify_specialized_provider_capture as tool


def _write_json(path: Path, value):
    import json

    path.write_text(
        json.dumps(value),
        encoding="utf-8",
    )


def test_cli_parser_requires_pre():
    parser = tool.build_parser()

    try:
        parser.parse_args([])
    except SystemExit:
        return
    raise AssertionError("parser accepted missing --pre")


def test_load_json_rejects_non_object(tmp_path: Path):
    path = tmp_path / "value.json"
    path.write_text("[1, 2, 3]", encoding="utf-8")

    try:
        tool._load_json(path)
    except ValueError as exc:
        assert "expected JSON object" in str(exc)
        return
    raise AssertionError("non-object JSON was accepted")


def test_cli_provider_argument_mismatch_is_blocking(tmp_path: Path, capsys):
    pre = tmp_path / "provider_pre_0_000001.json"
    _write_json(
        pre,
        {
            "provider_id": 0,
            "stage": "pre-solve-provider",
            "workspace": [0.0] * 1190,
            "output_vector": [0.0] * 40,
            "row_pointers": [],
            "frame_index": 1,
        },
    )

    result = tool.main(
        [
            "--pre",
            str(pre),
            "--provider",
            "1",
        ]
    )

    assert result == 2
    assert "provider-id-mismatch" in capsys.readouterr().out


def test_cli_pre_only_session_is_valid(tmp_path: Path, capsys):
    pre = tmp_path / "provider_pre_0_000001.json"
    _write_json(
        pre,
        {
            "provider_id": 0,
            "stage": "pre-solve-provider",
            "workspace": [0.0] * 1190,
            "output_vector": [0.0] * 40,
            "row_pointers": [],
            "frame_index": 1,
        },
    )

    result = tool.main(["--pre", str(pre)])

    assert result == 0
    assert '"ready": true' in capsys.readouterr().out
