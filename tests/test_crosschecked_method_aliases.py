import importlib.util
import json
from pathlib import Path


def _load_module():
    path = Path(__file__).resolve().parents[1] / "tools" / "ghidra" / "build_crosschecked_method_aliases.py"
    spec = importlib.util.spec_from_file_location("build_crosschecked_method_aliases", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _anchors(module, *, second_status="unique-method-name-anchor-candidate", second_alias=None):
    rows = []
    for spec in module.CROSSCHECKS:
        alias = spec["alias"]
        status = "unique-method-name-anchor-candidate"
        if spec["address"] == "0x00714560":
            status = second_status
            if second_alias is not None:
                alias = second_alias
        rows.append(
            {
                "address": spec["address"],
                "name": "FUN_" + spec["address"][2:],
                "calling_convention": "__fastcall",
                "size": 64,
                "mnemonic_sha256": "a" * 64,
                "method_anchors": [alias],
                "method_anchor_count": 1,
                "anchor_string_addresses": ["0x00b00000"],
                "unique_method_name_candidate": alias if status == "unique-method-name-anchor-candidate" else None,
                "status": status,
            }
        )
    return {
        "format": module.ANCHOR_FORMAT,
        "functions": rows,
    }


def _write_contracts(module, repo_root: Path, *, omit_marker: str | None = None):
    for spec in module.CROSSCHECKS:
        path = repo_root / spec["runtime_contract"]
        path.parent.mkdir(parents=True, exist_ok=True)
        markers = [
            marker
            for marker in spec["required_contract_markers"]
            if marker != omit_marker
        ]
        path.write_text("\n".join(markers) + "\n", encoding="utf-8")


def test_promotes_only_exact_unique_anchor_plus_runtime_contract(tmp_path):
    module = _load_module()
    anchors_path = tmp_path / "anchors.json"
    anchors_path.write_text(json.dumps(_anchors(module)), encoding="utf-8")
    repo_root = tmp_path / "repo"
    _write_contracts(module, repo_root)

    report = module.build_crosschecked_method_aliases(anchors_path, repo_root)
    assert report["format"] == "SHIFT.CrosscheckedMethodAliases/1"
    assert report["candidate_count"] == 2
    assert report["promoted_alias_count"] == 2
    assert report["failed_crosscheck_count"] == 0
    assert [row["address"] for row in report["promoted_aliases"]] == [
        "0x00710870",
        "0x00714560",
    ]
    assert all(row["promoted"] for row in report["aliases"])
    assert all(row["checks"]["unique_method_anchor_status"] for row in report["aliases"])
    assert all(row["checks"]["exact_method_name"] for row in report["aliases"])
    assert all(
        all(row["checks"]["runtime_contract_markers"].values())
        for row in report["aliases"]
    )
    assert all(item["sha256"] for item in report["runtime_contracts"])
    assert report["scope"]["parameter_semantics_proven"] is False
    assert report["scope"]["runtime_execution_proven"] is False


def test_ambiguous_method_anchor_is_not_promoted(tmp_path):
    module = _load_module()
    anchors_path = tmp_path / "anchors.json"
    anchors_path.write_text(
        json.dumps(_anchors(module, second_status="ambiguous-method-name-anchors")),
        encoding="utf-8",
    )
    repo_root = tmp_path / "repo"
    _write_contracts(module, repo_root)

    report = module.build_crosschecked_method_aliases(anchors_path, repo_root)
    row = next(item for item in report["aliases"] if item["address"] == "0x00714560")
    assert row["promoted"] is False
    assert row["checks"]["unique_method_anchor_status"] is False
    assert row["checks"]["exact_method_name"] is False
    assert report["promoted_alias_count"] == 1
    assert report["failed_crosscheck_count"] == 1


def test_wrong_exact_method_name_is_not_repaired(tmp_path):
    module = _load_module()
    anchors_path = tmp_path / "anchors.json"
    anchors_path.write_text(
        json.dumps(
            _anchors(
                module,
                second_alias="MWL::Core::PhysicsParticipantManager::DifferentMethod",
            )
        ),
        encoding="utf-8",
    )
    repo_root = tmp_path / "repo"
    _write_contracts(module, repo_root)

    report = module.build_crosschecked_method_aliases(anchors_path, repo_root)
    row = next(item for item in report["aliases"] if item["address"] == "0x00714560")
    assert row["checks"]["unique_method_anchor_status"] is True
    assert row["checks"]["exact_method_name"] is False
    assert row["promoted"] is False


def test_missing_runtime_marker_blocks_promotion(tmp_path):
    module = _load_module()
    anchors_path = tmp_path / "anchors.json"
    anchors_path.write_text(json.dumps(_anchors(module)), encoding="utf-8")
    repo_root = tmp_path / "repo"
    missing = module.CROSSCHECKS[0]["required_contract_markers"][0]
    _write_contracts(module, repo_root, omit_marker=missing)

    report = module.build_crosschecked_method_aliases(anchors_path, repo_root)
    row = next(item for item in report["aliases"] if item["address"] == "0x00710870")
    assert row["promoted"] is False
    assert row["checks"]["runtime_contract_markers"][missing] is False
    assert report["failed_crosscheck_count"] == 1


def test_rejects_wrong_anchor_format(tmp_path):
    module = _load_module()
    anchors_path = tmp_path / "anchors.json"
    anchors_path.write_text(json.dumps({"format": "wrong"}), encoding="utf-8")

    try:
        module.build_crosschecked_method_aliases(anchors_path, tmp_path)
    except ValueError as exc:
        assert module.ANCHOR_FORMAT in str(exc)
    else:
        raise AssertionError("wrong anchor format must fail")
