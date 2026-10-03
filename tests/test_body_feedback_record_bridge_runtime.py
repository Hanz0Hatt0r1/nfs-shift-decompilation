import math
import struct

import pytest

from body_feedback_record_bridge_runtime import (
    ACCUMULATOR_A,
    ACCUMULATOR_B,
    BODY_RECORD_SIZE,
    BodyAccumulatorRecordState,
    accumulator_writer_byte_indices,
    apply_body_accumulators_to_buffer,
    build_body_feedback_record_bridge_contract,
    decode_body_accumulators_from_buffer,
)


def _record(seed: int, angular, linear) -> bytes:
    record = bytearray([seed] * BODY_RECORD_SIZE)
    for offset, value in zip(ACCUMULATOR_A, angular):
        struct.pack_into("<d", record, offset, value)
    for offset, value in zip(ACCUMULATOR_B, linear):
        struct.pack_into("<d", record, offset, value)
    return bytes(record)


def test_contract_freezes_feedback_storage_boundary():
    contract = build_body_feedback_record_bridge_contract()
    assert contract["body_record_size"] == 0x170
    assert contract["accumulator_a_offsets"] == (0x48, 0x50, 0x58)
    assert contract["accumulator_b_offsets"] == (0x60, 0x68, 0x70)
    assert contract["accumulator_writer_bytes"] == 48
    assert contract["raw_feedback_seed_proven"] is True
    assert contract["post_solve_accumulator_write_proven"] is True
    assert contract["unrelated_bytes_preserved"] is True
    assert contract["body_integration_scheduled"] is False
    assert contract["runtime_scheduling_proven"] is False


def test_decodes_two_records_in_storage_order():
    first = _record(0x11, (1.0, 2.0, 3.0), (4.0, 5.0, 6.0))
    second = _record(0x22, (7.0, 8.0, 9.0), (10.0, 11.0, 12.0))
    decoded = decode_body_accumulators_from_buffer(first + second, 2)
    assert decoded == (
        BodyAccumulatorRecordState((1.0, 2.0, 3.0), (4.0, 5.0, 6.0)),
        BodyAccumulatorRecordState((7.0, 8.0, 9.0), (10.0, 11.0, 12.0)),
    )


def test_writer_changes_only_accumulator_bytes_per_record():
    first = _record(0x31, (1.0, 2.0, 3.0), (4.0, 5.0, 6.0))
    second = _record(0x42, (7.0, 8.0, 9.0), (10.0, 11.0, 12.0))
    original = first + second
    bodies = (
        BodyAccumulatorRecordState((101.0, 102.0, 103.0), (104.0, 105.0, 106.0)),
        BodyAccumulatorRecordState((201.0, 202.0, 203.0), (204.0, 205.0, 206.0)),
    )
    updated = apply_body_accumulators_to_buffer(original, bodies)
    writer = accumulator_writer_byte_indices()
    assert len(writer) == 48
    for record_index in range(2):
        base = record_index * BODY_RECORD_SIZE
        for local_index in range(BODY_RECORD_SIZE):
            if local_index not in writer:
                assert updated[base + local_index] == original[base + local_index]
    assert decode_body_accumulators_from_buffer(updated, 2) == bodies


def test_rejects_size_count_and_invalid_count():
    record = _record(0x11, (1.0, 2.0, 3.0), (4.0, 5.0, 6.0))
    with pytest.raises(ValueError, match="size/count mismatch"):
        decode_body_accumulators_from_buffer(record, 2)
    with pytest.raises(ValueError, match="non-negative integer"):
        decode_body_accumulators_from_buffer(record, -1)
    with pytest.raises(ValueError, match="non-negative integer"):
        decode_body_accumulators_from_buffer(record, True)


def test_rejects_non_finite_raw_and_writer_values():
    bad = bytearray(_record(0x11, (1.0, 2.0, 3.0), (4.0, 5.0, 6.0)))
    struct.pack_into("<d", bad, ACCUMULATOR_A[1], math.nan)
    with pytest.raises(ValueError, match="non-finite"):
        decode_body_accumulators_from_buffer(bad, 1)

    record = _record(0x11, (1.0, 2.0, 3.0), (4.0, 5.0, 6.0))
    with pytest.raises(ValueError, match="non-finite"):
        apply_body_accumulators_to_buffer(
            record,
            (BodyAccumulatorRecordState((1.0, math.inf, 3.0), (4.0, 5.0, 6.0)),),
        )
