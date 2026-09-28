from pathlib import Path

import tools.compare_specialized_provider_mutations as tool


def test_parser_requires_pre_post_source_and_provider():
    parser = tool.build_parser()
    try:
        parser.parse_args([])
    except SystemExit:
        return
    raise AssertionError("required arguments were not enforced")


def test_cli_writes_correlation_manifest(monkeypatch, tmp_path: Path, capsys):
    pre = tmp_path / "pre.json"
    post = tmp_path / "post.json"
    source = tmp_path / "SHIFT.exe.c"
    output = tmp_path / "correlation.json"

    pre.write_text("{}", encoding="utf-8")
    post.write_text("{}", encoding="utf-8")
    source.write_text("source", encoding="utf-8")

    monkeypatch.setattr(
        tool,
        "extract_factor_pattern",
        lambda source_text, provider_id: {
            "format": "SHIFT.SpecializedProviderFactorPatternRuntime/1",
            "provider_id": provider_id,
            "ready": True,
            "edges": [{"pivot_index": 0, "column": 1}],
            "errors": [],
        },
    )
    monkeypatch.setattr(
        tool,
        "build_source_mutation_correlation_contract",
        lambda pre_capture, post_capture, source_pattern, **kwargs: {
            "format": "SHIFT.SpecializedProviderCaptureSourceMutationCorrelation/1",
            "status": "partial",
            "ready": True,
            "provider_id": 0,
            "summary": {
                "source_edge_count": 1,
                "source_address_count": 1,
                "observed_workspace_address_count": 2,
                "observed_addresses_covered": 1,
                "observed_addresses_uncovered": 1,
                "alias_address_count": 0,
            },
            "errors": [],
        },
    )

    result = tool.main(
        [
            "--pre",
            str(pre),
            "--post",
            str(post),
            "--source",
            str(source),
            "--provider",
            "0",
            "-o",
            str(output),
        ]
    )

    assert result == 0
    report = output.read_text(encoding="utf-8")
    assert '"status": "partial"' in report
    assert '"observed_addresses_uncovered": 1' in capsys.readouterr().out
