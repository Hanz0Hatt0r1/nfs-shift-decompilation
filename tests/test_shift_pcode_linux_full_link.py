from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

TOOL = Path(__file__).resolve().parents[1] / "tools/ghidra/link_shift_pcode_linux_full.py"
SPEC = importlib.util.spec_from_file_location("shift_pcode_linux_full_link", TOOL)
assert SPEC is not None and SPEC.loader is not None
LINKER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(LINKER)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _fixture(tmp_path: Path) -> tuple[Path, Path, Path, Path]:
    build = tmp_path / "build"
    build.mkdir()
    obj = build / "shard-00000.o"
    obj.write_bytes(b"test object")
    manifest = tmp_path / "corpus-manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "format": "REVENGINSTR.GhidraFunctionInstructionCorpus/1",
                "program": "SHIFT.exe",
                "language_id": "x86:LE:32:default",
                "complete": True,
                "exported_function_count": 1,
                "output_sha256": "a" * 64,
            }
        ),
        encoding="utf-8",
    )
    spaces = tmp_path / "address-spaces.json"
    spaces.write_text(
        '{"format":"REVENGINSTR.GhidraLanguageAddressSpaces/1",'
        '"language_id":"x86:LE:32:default"}\n',
        encoding="utf-8",
    )
    report = {
        "format": "REVENGINSTR.PcodeCFunctionShardBuild/1",
        "source": {
            "program": "SHIFT.exe",
            "language_id": "x86:LE:32:default",
            "corpus_sha256": "a" * 64,
            "manifest_sha256": _sha256(manifest),
            "address_spaces_sha256": _sha256(spaces),
        },
        "functions": {"lowerable": 1, "rejected": 0},
        "compiler": {"arguments": ["-std=c11", "-fPIC"]},
        "shards": [
            {
                "index": 0,
                "functions": 1,
                "object_file": obj.name,
                "object_sha256": _sha256(obj),
            }
        ],
    }
    (build / "build-report.json").write_text(json.dumps(report), encoding="utf-8")
    return build, manifest, spaces, obj


def test_full_link_inputs_require_hash_pinned_complete_shards(tmp_path: Path) -> None:
    build, manifest, spaces, obj = _fixture(tmp_path)

    report, objects = LINKER.verify_inputs(build, manifest, spaces, expected_functions=1)

    assert report["functions"]["lowerable"] == 1
    assert objects == [obj]


def test_full_link_inputs_reject_modified_object_shard(tmp_path: Path) -> None:
    build, manifest, spaces, obj = _fixture(tmp_path)
    obj.write_bytes(b"modified object")

    with pytest.raises(ValueError, match="wrong hash"):
        LINKER.verify_inputs(build, manifest, spaces, expected_functions=1)


def test_full_link_inputs_reject_non_position_independent_objects(tmp_path: Path) -> None:
    build, manifest, spaces, _ = _fixture(tmp_path)
    report_path = build / "build-report.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    report["compiler"]["arguments"] = ["-std=c11"]
    report_path.write_text(json.dumps(report), encoding="utf-8")

    with pytest.raises(ValueError, match="-fPIC"):
        LINKER.verify_inputs(build, manifest, spaces, expected_functions=1)
