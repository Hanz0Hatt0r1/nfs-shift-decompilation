from pathlib import Path

from shift_importer import build_parser


def test_phase148_runtime_trace_cli_exposes_strict_same_instance_mode():
    parser = build_parser()
    args = parser.parse_args([
        "d3d9-runtime-trace",
        "trace.jsonl",
        "runtime.json",
        "--meb-resource",
        "meb.json",
        "--usage-map",
        "usage.json",
        "--require-same-instance",
    ])
    assert args.cmd == "d3d9-runtime-trace"
    assert args.trace == "trace.jsonl"
    assert args.output == "runtime.json"
    assert args.meb_resource == "meb.json"
    assert args.usage_map == "usage.json"
    assert args.require_same_instance is True
