import math
import struct

import pytest

from body_record_adapter_runtime import (
    ACCUMULATOR_A,
    ACCUMULATOR_B,
    BASIS,
    BODY_RECORD_SIZE,
    CROSS_VECTOR,
    MOTION_TRIPLET,
    ORIGIN,
    PREPARED_VECTOR,
    RECIPROCAL_COEFFICIENTS,
    SCALAR_0X90,
    BodyRecordWriterPayload,
    apply_fun_007b2270_body_buffer_payloads,
    apply_fun_007bab70_writer_payload,
    build_body_record_adapter_contract,
    decode_fun_007bab70_body_record,
    writer_byte_indices,
)


def _record(seed=0xA5):
    record = bytearray([seed] * BODY_RECORD_SIZE)
    values = {
        ORIGIN: (1.0, 2.0, 3.0),
        CROSS_VECTOR: (0.1, -0.2, 0.3),
        PREPARED_VECTOR: (10.0, 20.0, 30.0),
        ACCUMULATOR_A: (2.0, 4.0, 6.0),
        ACCUMULATOR_B: (1.0, 2.0, 3.0),
        MOTION_TRIPLET: (4.0, 5.0, 6.0),
        RECIPROCAL_COEFFICIENTS: (2.0, 3.0, 5.0),
    }
    for offsets, lane in values.items():
        for offset, value in zip(offsets, lane):
            struct.pack_into("<d", record, offset, value)
    struct.pack_into("<d", record, SCALAR_0X90, 0.5)
    identity = (1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0)
    for offset, value in zip(BASIS, identity):
        struct.pack_into("<f", record, offset, value)
    return bytes(record)


def _payload(base=0.0):
    return BodyRecordWriterPayload(
        origin=(base + 1.0, base + 2.0, base + 3.0),
        cross_vector=(base + 4.0, base + 5.0, base + 6.0),
        prepared_vector=(base + 7.0, base + 8.0, base + 9.0),
        motion_triplet=(base + 10.0, base + 11.0, base + 12.0),
        symmetric_tensor=(
            2.0, 0.0, 0.0,
            0.0, 3.0, 0.0,
            0.0, 0.0, 5.0,
        ),
        basis=(
            1.0, 0.0, 0.0,
            0.0, 1.0, 0.0,
            0.0, 0.0, 1.0,
        ),
    )


def test_contract_freezes_source_backed_record_layout():
    contract = build_body_record_adapter_contract()
    assert contract["body_record_size"] == 0x170
    assert contract["f64_input_offsets"]["reciprocal_coefficients"] == (0x138, 0x140, 0x148)
    assert contract["f32_writer_offsets"]["basis"][-1] == 0xF4
    assert contract["unrelated_bytes_preserved"] is True
    assert contract["basis_rotation_arithmetic_external"] is True
    assert contract["render_frame_scheduler_proven"] is False


def test_decodes_exact_little_endian_input_lanes():
    decoded = decode_fun_007bab70_body_record(_record())
    assert decoded.origin == (1.0, 2.0, 3.0)
    assert decoded.cross_vector == pytest.approx((0.1, -0.2, 0.3))
    assert decoded.accumulator_a == (2.0, 4.0, 6.0)
    assert decoded.accumulator_b == (1.0, 2.0, 3.0)
    assert decoded.motion_triplet == (4.0, 5.0, 6.0)
    assert decoded.scalar_0x90 == 0.5
    assert decoded.reciprocal_coefficients == (2.0, 3.0, 5.0)
    assert decoded.basis == (1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0)


def test_writer_payload_changes_only_proven_writer_bytes():
    original = _record()
    updated = apply_fun_007bab70_writer_payload(original, _payload(100.0))
    writer = writer_byte_indices()
    assert len(writer) == 168
    for index, (before, after) in enumerate(zip(original, updated)):
        if index not in writer:
            assert after == before, f"unrelated byte changed at 0x{index:x}"

    decoded = decode_fun_007bab70_body_record(updated)
    assert decoded.origin == (101.0, 102.0, 103.0)
    assert decoded.cross_vector == (104.0, 105.0, 106.0)
    assert decoded.prepared_vector == (107.0, 108.0, 109.0)
    assert decoded.motion_triplet == (110.0, 111.0, 112.0)
    # Read-only/producer lanes remain byte-identical through the writer adapter.
    assert decoded.accumulator_a == (2.0, 4.0, 6.0)
    assert decoded.accumulator_b == (1.0, 2.0, 3.0)
    assert decoded.scalar_0x90 == 0.5
    assert decoded.reciprocal_coefficients == (2.0, 3.0, 5.0)


def test_buffer_adapter_preserves_record_boundaries():
    first = _record(0x11)
    second = _record(0x22)
    updated = apply_fun_007b2270_body_buffer_payloads(
        first + second,
        (_payload(10.0), _payload(20.0)),
    )
    assert len(updated) == BODY_RECORD_SIZE * 2
    assert decode_fun_007bab70_body_record(updated[:BODY_RECORD_SIZE]).origin == (
        11.0,
        12.0,
        13.0,
    )
    assert decode_fun_007bab70_body_record(updated[BODY_RECORD_SIZE:]).origin == (
        21.0,
        22.0,
        23.0,
    )


def test_rejects_invalid_sizes_and_non_finite_consumed_fields():
    with pytest.raises(ValueError, match="exactly 368 bytes"):
        decode_fun_007bab70_body_record(bytes(BODY_RECORD_SIZE - 1))
    with pytest.raises(ValueError, match="size/count mismatch"):
        apply_fun_007b2270_body_buffer_payloads(_record(), (_payload(), _payload()))

    bad = bytearray(_record())
    struct.pack_into("<d", bad, CROSS_VECTOR[0], math.nan)
    with pytest.raises(ValueError, match="non-finite"):
        decode_fun_007bab70_body_record(bad)


def test_rejects_non_finite_writer_payload():
    bad = BodyRecordWriterPayload(
        origin=(math.inf, 0.0, 0.0),
        cross_vector=(0.0, 0.0, 0.0),
        prepared_vector=(0.0, 0.0, 0.0),
        motion_triplet=(0.0, 0.0, 0.0),
        symmetric_tensor=(0.0,) * 9,
        basis=(0.0,) * 9,
    )
    with pytest.raises(ValueError, match="non-finite"):
        apply_fun_007bab70_writer_payload(_record(), bad)
