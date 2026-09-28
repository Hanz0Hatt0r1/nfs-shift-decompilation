from pathlib import Path

import pytest

import tools.run_specialized_provider_differential as tool


def test_build_parser_requires_pre():
    parser = tool.build_parser()

    with pytest.raises(SystemExit):
        parser.parse_args([])


def test_cli_rejects_source_without_provider(tmp_path: Path):
    parser = tool.build_parser()
    args = parser.parse_args(
        ["--pre", str(tmp_path / "pre.json"), "--source", str(tmp_path / "SHIFT.exe.c")]
    )

    assert args.provider is None


def test_load_json_rejects_non_object(tmp_path: Path):
    path = tmp_path / "value.json"
    path.write_text("[1, 2, 3]", encoding="utf-8")

    try:
        tool._load_json(path)
    except ValueError as exc:
        assert "expected JSON object" in str(exc)
    else:
        raise AssertionError("non-object JSON was accepted")
