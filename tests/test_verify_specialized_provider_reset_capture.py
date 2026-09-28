from pathlib import Path

import tools.verify_specialized_provider_reset_capture as tool


def _write_json(path: Path, value):
    import json

    path.write_text(
        json.dumps(value),
        encoding="utf-8",
    )


def test_load_events_skips_blank_lines(tmp_path: Path):
    path = tmp_path / "events.jsonl"
    path.write_text(
        '{"call_index": 0, "frame_index": 1}\n\n'
        '{"call_index": 1, "frame_index": 1}\n',
        encoding="utf-8",
    )

    result = tool._load_events(path)

    assert result == [
        {"call_index": 0, "frame_index": 1},
        {"call_index": 1, "frame_index": 1},
    ]


def test_validate_capture_lists_requires_matching_pre_post_counts():
    try:
        tool._validate_capture_lists(
            [Path("a.json")],
            [Path("b.json"), Path("c.json")],
        )
    except ValueError as exc:
        assert "equal counts" in str(exc)
    else:
        raise AssertionError("mismatched provider capture lists were accepted")


def test_cli_pre_only_returns_success(tmp_path: Path, capsys):
    events = tmp_path / "scalar_reset_events.jsonl"
    events.write_text(
        "\n".join(
            [
                '{"call_index": 1, "frame_index": 1, "physics_system": 4096, "provider_pointer": 0, "scalar_count": 40, "selector": 2, "caller_return_address": 12288}',
                '{"call_index": 2, "frame_index": 1, "physics_system": 4096, "provider_pointer": 0, "scalar_count": 40, "selector": 3, "caller_return_address": 12307}',
                '{"call_index": 3, "frame_index": 1, "physics_system": 4096, "provider_pointer": 0, "scalar_count": 40, "selector": 4, "caller_return_address": 12322}',
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    result = tool.main(
        [
            "--events",
            str(events),
        ]
    )

    output = capsys.readouterr().out
    assert result == 0
    assert '"ready": true' in output
    assert '"frame_count": 1' in output


def test_load_json_rejects_non_object(tmp_path: Path):
    path = tmp_path / "value.json"
    path.write_text("[1, 2, 3]", encoding="utf-8")

    try:
        tool._load_json(path)
    except ValueError as exc:
        assert "expected JSON object" in str(exc)
    else:
        raise AssertionError("non-object JSON was accepted")
