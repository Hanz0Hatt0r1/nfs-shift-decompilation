import hashlib
import struct

import pytest

from imb_fxo_pair_provenance import (
    AMBIGUITY_FORMAT,
    FORMAT,
    TARGET_FORMAT,
    audit_target_set,
)
from shader_ir import parse_shader_blobs
from shader_permutation_identity import build_shader_permutation_identity


def _ctab(name: bytes, stage_version: int, register: int) -> bytes:
    header = 28
    info = 20
    typ = 20
    name_off = header + info + typ
    payload = bytearray(b"CTAB")
    payload += struct.pack("<7I", header, 0, stage_version, 1, header, 0, 0)
    payload += struct.pack(
        "<IHHHHII",
        name_off,
        3,
        register,
        1,
        0,
        header + info,
        0,
    )
    payload += struct.pack("<HHHHHHII", 4, 12, 1, 1, 1, 0, 0, 0)
    payload += name
    payload += b"\x00" * ((-len(payload)) % 4)
    return struct.pack("<I", stage_version) + struct.pack(
        "<I", ((len(payload) // 4) << 16) | 0xFFFE
    ) + payload


def _synthetic_pair(*, vertex_nop: bool = False) -> bytes:
    vs_version = 0xFFFE0300
    ps_version = 0xFFFF0300
    dcl = (2 << 24) | 31

    vs = bytearray(_ctab(b"diffuseMap\x00", vs_version, 0))
    vs += struct.pack(
        "<III",
        dcl,
        0,
        0x80000000 | 0 | (15 << 16) | (1 << 28),
    )
    vs += struct.pack(
        "<III",
        dcl,
        5 | (5 << 16),
        0x80000000 | 1 | (15 << 16) | (6 << 28),
    )
    if vertex_nop:
        vs += struct.pack("<I", 0)
    vs += struct.pack("<I", 0xFFFF)

    ps = bytearray(_ctab(b"diffuseMap\x00", ps_version, 0))
    ps += struct.pack(
        "<III",
        dcl,
        5 | (5 << 16),
        0x80000000 | 0 | (15 << 16) | (1 << 28),
    )
    ps += struct.pack("<I", 0xFFFF)
    return bytes(vs + ps)


def _variant(data: bytes, *, file: str) -> dict:
    blobs = parse_shader_blobs(data)
    vertex = next(blob for blob in blobs if blob.stage == "vertex")
    pixel = next(blob for blob in blobs if blob.stage == "pixel")
    vertex_bytes = data[vertex.offset:vertex.end]
    pixel_bytes = data[pixel.offset:pixel.end]
    identity = build_shader_permutation_identity(
        data,
        vertex_offset=vertex.offset,
        pixel_offset=pixel.offset,
    )
    return {
        "candidate_file": file,
        "candidate_program_offset": pixel.offset,
        "candidate_vertex_program_offset": vertex.offset,
        "vertex_byte_sha256": hashlib.sha256(vertex_bytes).hexdigest(),
        "pixel_byte_sha256": hashlib.sha256(pixel_bytes).hexdigest(),
        "pair_byte_sha256": hashlib.sha256(vertex_bytes + pixel_bytes).hexdigest(),
        "permutation_identity_sha256": identity["identity_sha256"],
        "exact": True,
    }


def _target_set(*variants: dict) -> dict:
    targets = []
    for variant in variants:
        targets.append({
            "identity_kind": "pair",
            "identity_value": variant["pair_byte_sha256"],
            "strength": "exact-pair",
            "candidate_variants": [variant],
        })
    return {
        "format": TARGET_FORMAT,
        "binding_targets": [
            {
                "binding_index": 0,
                "targets": targets,
            }
        ],
    }


def _occurrence(data: bytes, *, archive: str, entry: str) -> dict:
    return {
        "source_input": archive,
        "archive": archive,
        "entry_path": entry,
        "entry_index": 7,
        "payload": data,
        "payload_sha256": hashlib.sha256(data).hexdigest(),
        "load_status": "loaded",
    }


def _pair_tuple(variant: dict) -> tuple[str, str]:
    return variant["vertex_byte_sha256"], variant["pixel_byte_sha256"]


def test_exact_embedded_pair_is_recomputed_from_payload():
    data = _synthetic_pair()
    file = "render/shaders/body.fxo"
    variant = _variant(data, file=file)
    report = audit_target_set(
        _target_set(variant),
        {file: [_occurrence(data, archive="RENDER.bff", entry=file)]},
    )

    assert report["format"] == FORMAT
    assert report["ready"] is True
    assert report["status"] == "verified"
    assert report["summary"]["verified_pair_count"] == 1
    row = report["variants"][0]
    assert row["provenance_status"] == "exact-source-occurrence"
    check = row["occurrence_checks"][0]
    assert check["status"] == "verified-exact-fxo-pair"
    assert check["confidence"] == "exact-byte-equality"
    assert check["actual"]["pair_byte_sha256"] == variant["pair_byte_sha256"]


def test_byte_identical_archive_copies_remain_multiple_provenance_locations():
    data = _synthetic_pair()
    file = "render/shaders/body.fxo"
    variant = _variant(data, file=file)
    report = audit_target_set(
        _target_set(variant),
        {
            file: [
                _occurrence(data, archive="Silverstone_A.bff", entry=file),
                _occurrence(data, archive="Silverstone_B.bff", entry=file),
            ]
        },
    )

    row = report["variants"][0]
    assert row["verified_occurrence_count"] == 2
    assert row["provenance_status"] == "content-equivalent-multiple-source-occurrences"
    pair = report["verified_pairs"][0]
    assert pair["source_occurrence_count"] == 2
    assert {item["archive"] for item in pair["source_occurrences"]} == {
        "Silverstone_A.bff",
        "Silverstone_B.bff",
    }


def test_hash_mismatch_fails_closed_without_selecting_candidate():
    data = _synthetic_pair()
    file = "render/shaders/body.fxo"
    variant = _variant(data, file=file)
    variant["pixel_byte_sha256"] = "f" * 64
    report = audit_target_set(
        _target_set(variant),
        {file: [_occurrence(data, archive="RENDER.bff", entry=file)]},
    )

    assert report["ready"] is False
    assert report["status"] == "partial"
    row = report["variants"][0]
    assert row["verified_occurrence_count"] == 0
    assert row["provenance_status"] == "no-byte-exact-occurrence"
    assert "pixel_byte_sha256" in row["occurrence_checks"][0]["mismatches"]


def test_phase618_filter_audits_only_shader_provenance_distinct_pairs():
    data_a = _synthetic_pair(vertex_nop=False)
    data_b = _synthetic_pair(vertex_nop=True)
    file_a = "render/shaders/a.fxo"
    file_b = "render/shaders/b.fxo"
    variant_a = _variant(data_a, file=file_a)
    variant_b = _variant(data_b, file=file_b)
    vertex_b, pixel_b = _pair_tuple(variant_b)
    ambiguity = {
        "format": AMBIGUITY_FORMAT,
        "ambiguous_draws": [
            {
                "ambiguity_class": "material-distinct-candidates",
                "candidates": [
                    {
                        "matched_vertex_shader_sha256": variant_a["vertex_byte_sha256"],
                        "matched_pixel_shader_sha256": variant_a["pixel_byte_sha256"],
                    }
                ],
            },
            {
                "ambiguity_class": "shader-provenance-distinct-candidates",
                "candidates": [
                    {
                        "matched_vertex_shader_sha256": vertex_b,
                        "matched_pixel_shader_sha256": pixel_b,
                    }
                ],
            },
        ],
    }
    report = audit_target_set(
        _target_set(variant_a, variant_b),
        {
            file_a: [_occurrence(data_a, archive="A.bff", entry=file_a)],
            file_b: [_occurrence(data_b, archive="B.bff", entry=file_b)],
        },
        ambiguity=ambiguity,
    )

    assert report["ready"] is True
    assert report["status"] == "required-pairs-verified"
    assert report["summary"]["audited_variant_count"] == 1
    assert report["ambiguity_filter"]["required_pair_count"] == 1
    assert report["verified_pairs"][0]["vertex_shader_sha256"] == vertex_b


def test_empty_phase618_shader_provenance_class_needs_no_capture_or_selection():
    data = _synthetic_pair()
    file = "render/shaders/body.fxo"
    variant = _variant(data, file=file)
    ambiguity = {
        "format": AMBIGUITY_FORMAT,
        "ambiguous_draws": [
            {
                "ambiguity_class": "material-distinct-candidates",
                "candidates": [],
            }
        ],
    }
    report = audit_target_set(
        _target_set(variant),
        {},
        ambiguity=ambiguity,
    )
    assert report["ready"] is True
    assert report["status"] == "no-shader-provenance-distinct-candidates"
    assert report["summary"]["audited_variant_count"] == 0
    assert report["boundary"]["capture_requirement"] == "none"


def test_input_formats_fail_closed():
    with pytest.raises(ValueError, match="target set"):
        audit_target_set({"format": "wrong"}, {})

    data = _synthetic_pair()
    variant = _variant(data, file="body.fxo")
    with pytest.raises(ValueError, match="ambiguity audit"):
        audit_target_set(
            _target_set(variant),
            {},
            ambiguity={"format": "wrong"},
        )
