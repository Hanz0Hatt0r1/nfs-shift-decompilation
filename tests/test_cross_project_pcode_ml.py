from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REVENGINSTR_ROOT = Path(
    os.environ.get("REVENGINSTR_REPO", str(ROOT.parent / "revenginstr"))
)


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")


def test_shift_ml_exporter_keeps_portable_contract() -> None:
    text = (REVENGINSTR_ROOT / "ghidra/PortablePcodeCorpusExporter.java").read_text(encoding="utf-8")
    assert 'FORMAT = "REVENGINSTR.PcodeCorpus/1"' in text
    assert "PortablePcodeCorpusExporter" in text
    assert "SHIFT" not in text
    assert "Nevergone" not in text
    assert "MAX_MODEL_OPS = 256" in text
    assert 'text.append("ARCH=")' in text
    assert 'text.append("ENDIAN=")' in text
    assert 'text.append("PTR_SIZE=")' in text
    assert "appendInputs(text, op, opIds, 1, \"arg\")" in text
    assert "if (opcode == PcodeOp.BRANCH) return;" in text
    assert "if (opcode == PcodeOp.INDIRECT)" in text
    assert "source_entry" in text
    assert "source_name" in text


def test_cross_project_runner_is_read_only_isolated_and_guarded() -> None:
    text = (ROOT / "tools/ml/run_shift_cross_project_pcode_probe.sh").read_text(encoding="utf-8")
    exporter = (REVENGINSTR_ROOT / "scripts/run_ghidra_pcode_export.sh").read_text(encoding="utf-8")
    assert "-noanalysis" in text
    assert "-readOnly" in text
    assert "production-code-domain-v4" in text
    assert "REVENGINSTR_REPO" in text
    assert "scripts/run_ghidra_pcode_export.sh" in text
    assert "revenginstr.pcode.audit" in text
    assert "revenginstr.ood.foreign_guard" in text
    assert "ShiftMlPcodeCorpusExporter.java" not in text
    assert "ML_SCRIPT_DIR" not in text
    assert "-readOnly" in exporter and "-noanalysis" in exporter
    assert "mktemp -d" in exporter
    assert '-scriptPath "$TMP_SCRIPT_DIR"' in exporter


def test_foreign_guard_only_demotes_weak_accepts(tmp_path: Path) -> None:
    classified = tmp_path / "classified.jsonl"
    guarded = tmp_path / "guarded.jsonl"
    _write_jsonl(
        classified,
        [
            {
                "id": "strong",
                "prediction": "engine",
                "action": "accept",
                "family_similarity": 0.82,
                "contrast_margin": 0.11,
                "ood_accept_threshold": 0.55,
                "contrast_accept_threshold": 0.03,
            },
            {
                "id": "weak-contrast",
                "prediction": "game",
                "action": "accept",
                "family_similarity": 0.85,
                "contrast_margin": 0.0,
                "ood_accept_threshold": 0.50,
                "contrast_accept_threshold": 0.01,
            },
            {
                "id": "weak-similarity",
                "prediction": "media_library",
                "action": "accept",
                "family_similarity": 0.61,
                "contrast_margin": 0.20,
                "ood_accept_threshold": 0.45,
                "contrast_accept_threshold": 0.02,
            },
            {
                "id": "existing-review",
                "prediction": "runtime_library",
                "action": "review",
                "family_similarity": 0.95,
                "contrast_margin": 0.25,
            },
            {
                "id": "class-policy-stronger",
                "prediction": "engine",
                "action": "accept",
                "family_similarity": 0.75,
                "contrast_margin": 0.10,
                "ood_accept_threshold": 0.80,
                "contrast_accept_threshold": 0.08,
            },
        ],
    )

    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "tools/ml/guard_shift_foreign_pcode_predictions.py"),
            str(classified),
            "--output",
            str(guarded),
        ],
        check=True,
        text=True,
        capture_output=True,
    )
    assert "promotions: 0" in result.stdout
    rows = [json.loads(line) for line in guarded.read_text(encoding="utf-8").splitlines()]
    by_id = {row["id"]: row for row in rows}
    assert by_id["strong"]["action"] == "accept"
    assert by_id["strong"]["foreign_guard_changed"] is False
    assert by_id["weak-contrast"]["action"] == "review"
    assert by_id["weak-similarity"]["action"] == "review"
    assert by_id["existing-review"]["action"] == "review"
    assert by_id["existing-review"]["base_action"] == "review"
    assert by_id["class-policy-stronger"]["action"] == "review"
    assert by_id["class-policy-stronger"]["foreign_similarity_floor"] == 0.8


def test_cross_project_audit_summarizes_portable_guarded_transfer_rows(tmp_path: Path) -> None:
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
                "base_action": "accept",
                "action": "review",
                "confidence": 0.82,
                "raw_confidence": 0.75,
                "family_similarity": 0.31,
                "contrast_margin": -0.07,
                "foreign_guard_format": "SHIFT.ForeignProjectGuard/1",
                "foreign_guard_changed": True,
                "foreign_guard_reasons": ["family_similarity_below_foreign_floor"],
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
    assert summary["format"] == "SHIFT.CrossProjectPcodeAudit/2"
    assert summary["corpus"]["architecture"] == {"X8632": 1}
    assert summary["corpus"]["pointer_size"] == {"4": 1}
    assert summary["corpus"]["leakage_findings"] == []
    assert summary["transfer"]["predictions"] == {"game": 1}
    assert summary["transfer"]["base_actions"] == {"accept": 1}
    assert summary["transfer"]["actions"] == {"review": 1}
    assert summary["transfer"]["foreign_guard"]["changed_accepts"] == 1
    assert summary["transfer"]["foreign_guard"]["promotions"] == 0
    assert summary["transfer"]["semantic_labels_available"] is False
