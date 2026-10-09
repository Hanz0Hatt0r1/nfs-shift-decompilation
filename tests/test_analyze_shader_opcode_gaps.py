from tools import analyze_shader_opcode_gaps as runtime


def test_analyze_opcode_gaps_reports_only_observed_unsupported_ops(monkeypatch):
    monkeypatch.setattr(runtime, "_SUPPORTED", {"MOV", "TEX"})

    report = {
        "format": "SHIFT.FXOShaderCorpusAudit/1",
        "ready": True,
        "summary": {
            "opcode_counts": {
                "MOV": 100,
                "TEX": 80,
                "POW": 10,
                "TEXKILL": 2,
            },
            "unsupported_opcode_counts": {
                "POW": 10,
                "TEXKILL": 2,
            },
        },
    }

    result = runtime.analyze_opcode_gaps(report)

    assert result["gap_count"] == 2
    assert result["gaps"] == [
        {
            "opcode": "POW",
            "observed_instruction_count": 10,
            "parser_unsupported_count": 10,
        },
        {
            "opcode": "TEXKILL",
            "observed_instruction_count": 2,
            "parser_unsupported_count": 2,
        },
    ]
    assert result["observed_supported_count"] == 2
    assert result["ready"] is False


def test_analyze_opcode_gaps_is_ready_only_when_corpus_is_ready_and_gap_free(monkeypatch):
    monkeypatch.setattr(runtime, "_SUPPORTED", {"MOV", "TEX"})
    result = runtime.analyze_opcode_gaps(
        {
            "format": "SHIFT.FXOShaderCorpusAudit/1",
            "ready": True,
            "summary": {
                "opcode_counts": {"MOV": 3, "TEX": 2},
                "unsupported_opcode_counts": {},
            },
        }
    )
    assert result["gap_count"] == 0
    assert result["ready"] is True


def test_analyze_opcode_gaps_preserves_blocked_corpus_state():
    result = runtime.analyze_opcode_gaps(
        {
            "format": "SHIFT.FXOShaderCorpusAudit/1",
            "ready": False,
            "summary": {
                "opcode_counts": {"MOV": 1},
                "unsupported_opcode_counts": {},
            },
        }
    )
    assert result["gap_count"] == 0
    assert result["ready"] is False
