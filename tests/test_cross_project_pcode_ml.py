from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")


def test_shift_ml_exporter_keeps_portable_contract() -> None:
    text = (ROOT / "tools/ghidra/ShiftMlPcodeCorpusExporter.java").read_text(encoding="utf-8")
    assert 'FORMAT = "SHIFT.MlPcodeCorpus/1"' in text
    assert "MAX_MODEL_OPS = 256" in text
    assert 'text.append("ARCH=")' in text
    assert 'text.append("ENDIAN=")' in text
    assert 'text.append("PTR_SIZE=")' in text
    assert "appendGenericInputs(text, op, opIds, 1, \"arg\")" in text
    assert "if (opcode == PcodeOp.BRANCH) return;" in text
    assert "if (opcode == PcodeOp.INDIRECT)" in text
    assert "source_entry" in text
    assert "source_name" in text


def test_cross_project_runner_is_read_only_and_noanalysis() -> None:
    text = (ROOT / "tools/ml/run_shift_cross_project_pcode_probe.sh").read_text(encoding="utf-8")
    assert "-noanalysis" in text
    assert "-readOnly" in text
    assert "production-code-domain-v4" in text
    assert "ShiftMlPcodeCorpusExporter.java" in text
    assert "audit_shift_cross_project_pcode.py" in text


def test_cross_project_audit_summarizes_portable_and_transfer_rows(tmp_path: Path) -> None:
    corpus = tmp_path / "corpus.jsonl"
    classified = tmp_path / "classified.jsonl"
    output = tmp_path / "summary.json"
    _write_jsonl(
        corpus,
        [
            {
                "format": "SHIFT.MlPcodeCorpus/1",
                "program": "SHIFT.exe",
                "source_entry": "00401000",
                "source_name": "FUN_00401000",
                "external": False,
                "decompile_status": "ok",
                "metrics": {"emitted_ops": 3, "truncated": False},
                "model_text": (
                    "ARCH=X8632\nENDIAN=LE\nPTR_SIZE=4\nCALLCONV=__cdecl\n"
                    "PARAMS=1\nBODY_ADDRS_BUCKET=16-31\nOPS_BUCKET=2-3\n"
                    "CALLS_BUCKET=0\nINDIRECT_CALLS_BUCKET=0\nBRANCHES_BUCKET=0\n"
                    "LOADS_BUCKET=1\nSTORES_BUCKET=0\nTRUNCATED=0\n"
                    "o0 LOAD out=v0:4 addr=reg:4\n"
                    "o1 INT_ADD out=v1:4 in=v0:4 in=const:small:0x4:4\n"
                    "o2 RETURN ret=v1:4\n"
                ),
            }
        ],
    )
    _write_jsonl(
        classified,
        [
            {
                "id": "SHIFT.exe:00401000",
                "prediction": "game",
                "action": "review",
                "confidence": 0.82,
                "raw_confidence": 0.75,
                "family_similarity": 0.31,
                "contrast_margin": -0.07,
            }
        ],
    )

    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "tools/ml/audit_shift_cross_project_pcode.py"),
            str(corpus),
            "--classified",
            str(classified),
            "--output",
            str(output),
        ],
        check=True,
        text=True,
        capture_output=True,
    )
    assert "portable contract pass: True" in result.stdout
    summary = json.loads(output.read_text(encoding="utf-8"))
    assert summary["format"] == "SHIFT.CrossProjectPcodeAudit/1"
    assert summary["corpus"]["architecture"] == {"X8632": 1}
    assert summary["corpus"]["pointer_size"] == {"4": 1}
    assert summary["corpus"]["leakage_findings"] == []
    assert summary["transfer"]["predictions"] == {"game": 1}
    assert summary["transfer"]["actions"] == {"review": 1}
    assert summary["transfer"]["semantic_labels_available"] is False
