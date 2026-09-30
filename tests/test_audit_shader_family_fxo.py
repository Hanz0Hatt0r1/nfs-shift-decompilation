import json

from tools.audit_shader_family_fxo import (
    FORMAT,
    _shader_refs_from_evidence,
    summarize_shader_families,
)


def _candidate(
    family,
    sha,
    *,
    archive="RENDER.bff",
    path="render/shaders/example.fxo",
    entry_index=1,
    vertex=1,
    pixel=1,
    program_count=None,
    parse_ready=True,
):
    if program_count is None:
        program_count = vertex + pixel
    return {
        "archive": archive,
        "entry_index": entry_index,
        "path": path,
        "type": 2,
        "family": family,
        "payload_sha256": sha,
        "decoded_size": 100,
        "program_count": program_count,
        "vertex_program_count": vertex,
        "pixel_program_count": pixel,
        "programs": [],
        "parse_ready": parse_ready,
    }


def test_content_identical_copies_collapse_to_one_payload():
    report = summarize_shader_families(
        ["render/shaders/basic_instanced.fx"],
        [
            _candidate(
                "basicinstanced",
                "a" * 64,
                archive="RENDER.bff",
                entry_index=10,
                path="render/shaders/basic_instanced_a.fxo",
            ),
            _candidate(
                "basicinstanced",
                "a" * 64,
                archive="RENDER_COPY.bff",
                entry_index=20,
                path="render/shaders/basic_instanced_b.fxo",
            ),
        ],
    )

    assert report["format"] == FORMAT
    assert report["status"] == "selection-ready"
    assert report["ready"] is True
    assert report["selection_ready"] is True
    assert report["candidate_copy_count"] == 2
    assert report["unique_payload_count"] == 1
    assert report["duplicate_copy_count"] == 1
    family = report["families"][0]
    assert family["status"] == "single-payload-single-pair"
    assert len(family["unique_payloads"][0]["copies"]) == 2


def test_single_payload_with_multiple_programs_remains_ambiguous():
    report = summarize_shader_families(
        ["render/shaders/foliage_instanced.fx"],
        [
            _candidate(
                "foliageinstanced",
                "b" * 64,
                vertex=3,
                pixel=4,
            )
        ],
    )

    assert report["status"] == "inventory-ready"
    assert report["ready"] is True
    assert report["selection_ready"] is False
    assert (
        report["families"][0]["status"]
        == "single-payload-multi-program"
    )


def test_multiple_distinct_payloads_remain_ambiguous():
    report = summarize_shader_families(
        ["render/shaders/crowd_geninstanced.fx"],
        [
            _candidate("crowdgeninstanced", "c" * 64),
            _candidate(
                "crowdgeninstanced",
                "d" * 64,
                entry_index=2,
                path="render/shaders/crowd_geninstanced_alt.fxo",
            ),
        ],
    )

    assert report["status"] == "inventory-ready"
    assert report["ready"] is True
    assert report["selection_ready"] is False
    assert report["families"][0]["status"] == "multi-payload"
    assert report["unique_payload_count"] == 2


def test_missing_and_parse_blocked_families_fail_closed():
    report = summarize_shader_families(
        [
            "render/shaders/basic_instanced.fx",
            "render/shaders/skintest_instanced.fx",
        ],
        [
            _candidate(
                "basicinstanced",
                "",
                parse_ready=False,
                program_count=0,
                vertex=0,
                pixel=0,
            )
        ],
    )

    assert report["status"] == "blocked"
    assert report["ready"] is False
    rows = {row["family"]: row for row in report["families"]}
    assert rows["basicinstanced"]["status"] == "parse-blocked"
    assert rows["skintestinstanced"]["status"] == "missing"


def test_dependency_evidence_shader_source_list_is_reusable(tmp_path):
    evidence = {
        "shader_sources": [
            {"path": "render/shaders/basic_instanced.fx"},
            {"path": "render/shaders/foliage_instanced.fx"},
        ]
    }
    path = tmp_path / "deps.json"
    path.write_text(json.dumps(evidence), encoding="utf-8")

    assert _shader_refs_from_evidence(path) == [
        "render/shaders/basic_instanced.fx",
        "render/shaders/foliage_instanced.fx",
    ]
