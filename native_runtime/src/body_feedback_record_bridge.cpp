#include "shift_body_feedback_record_bridge.hpp"

#include <cmath>
#include <cstring>
#include <limits>
#include <stdexcept>

namespace shift::runtime::physics {
namespace {

void require_buffer_shape(
    const std::vector<std::uint8_t>& body_bytes,
    std::size_t body_count) {
    if (body_count > std::numeric_limits<std::size_t>::max() / kBodyRecordSize) {
        throw std::invalid_argument(
            "BODY feedback record count overflows byte domain");
    }
    const std::size_t expected = body_count * kBodyRecordSize;
    if (body_bytes.size() != expected) {
        throw std::invalid_argument(
            "BODY feedback record buffer size/count mismatch");
    }
}

std::uint64_t read_u64_le(
    const std::vector<std::uint8_t>& bytes,
    std::size_t offset) {
    std::uint64_t value = 0u;
    for (std::size_t byte = 0; byte < 8u; ++byte) {
        value |= static_cast<std::uint64_t>(bytes[offset + byte]) << (byte * 8u);
    }
    return value;
}

double read_f64_le(
    const std::vector<std::uint8_t>& bytes,
    std::size_t offset) {
    const std::uint64_t bits = read_u64_le(bytes, offset);
    double value = 0.0;
    std::memcpy(&value, &bits, sizeof(value));
    return value;
}

void write_u64_le(
    std::vector<std::uint8_t>& bytes,
    std::size_t offset,
    std::uint64_t value) {
    for (std::size_t byte = 0; byte < 8u; ++byte) {
        bytes[offset + byte] = static_cast<std::uint8_t>(
            (value >> (byte * 8u)) & 0xffu);
    }
}

void write_f64_le(
    std::vector<std::uint8_t>& bytes,
    std::size_t offset,
    double value) {
    std::uint64_t bits = 0u;
    std::memcpy(&bits, &value, sizeof(bits));
    write_u64_le(bytes, offset, bits);
}

void require_finite_accumulator(
    const BodyAccumulatorState& body,
    const char* label) {
    for (double value : body.angular) {
        if (!std::isfinite(value)) {
            throw std::invalid_argument(label);
        }
    }
    for (double value : body.linear) {
        if (!std::isfinite(value)) {
            throw std::invalid_argument(label);
        }
    }
}

BodyAccumulatorState decode_one(
    const std::vector<std::uint8_t>& bytes,
    std::size_t base) {
    BodyAccumulatorState body{};
    for (std::size_t component = 0; component < 3u; ++component) {
        body.angular[component] = read_f64_le(
            bytes,
            base + body_record_offset::kAccumulatorA[component]);
        body.linear[component] = read_f64_le(
            bytes,
            base + body_record_offset::kAccumulatorB[component]);
    }
    require_finite_accumulator(
        body,
        "BODY feedback record contains non-finite accumulator value");
    return body;
}

void write_one(
    std::vector<std::uint8_t>& bytes,
    std::size_t base,
    const BodyAccumulatorState& body) {
    require_finite_accumulator(
        body,
        "BODY feedback result contains non-finite accumulator value");
    for (std::size_t component = 0; component < 3u; ++component) {
        write_f64_le(
            bytes,
            base + body_record_offset::kAccumulatorA[component],
            body.angular[component]);
        write_f64_le(
            bytes,
            base + body_record_offset::kAccumulatorB[component],
            body.linear[component]);
    }
}

}  // namespace

std::vector<BodyAccumulatorState> decode_body_accumulators_from_buffer(
    const std::vector<std::uint8_t>& body_bytes,
    std::size_t body_count) {
    require_buffer_shape(body_bytes, body_count);

    std::vector<BodyAccumulatorState> result;
    result.reserve(body_count);
    for (std::size_t index = 0; index < body_count; ++index) {
        result.push_back(decode_one(body_bytes, index * kBodyRecordSize));
    }
    return result;
}

std::vector<std::uint8_t> apply_body_accumulators_to_buffer(
    const std::vector<std::uint8_t>& body_bytes,
    const std::vector<BodyAccumulatorState>& bodies) {
    require_buffer_shape(body_bytes, bodies.size());

    std::vector<std::uint8_t> result = body_bytes;
    for (std::size_t index = 0; index < bodies.size(); ++index) {
        write_one(result, index * kBodyRecordSize, bodies[index]);
    }
    return result;
}

BodyFeedbackRecordBridgeResult execute_body_state_feedback_raw_step(
    const PreparedGeneratedBodyConstraintFrame& source,
    const PreparedConstraintSampleRelationFrame& relations,
    const PreparedConstraintRelationResetFrame& reset_state,
    const PreparedBuiltinSolverFrame& solver_topology,
    const PreparedPostSolveBodyProjection& projection,
    const std::vector<std::uint8_t>& body_bytes,
    double tolerance) {

    const std::size_t body_count = source.bodies.size();
    const auto current_bodies =
        decode_body_accumulators_from_buffer(body_bytes, body_count);
    const auto feedback = execute_body_state_feedback_step(
        source,
        relations,
        reset_state,
        solver_topology,
        projection,
        current_bodies,
        tolerance);
    if (feedback.bodies.size() != body_count) {
        throw std::runtime_error(
            "BODY feedback record bridge output cardinality mismatch");
    }

    return {
        apply_body_accumulators_to_buffer(body_bytes, feedback.bodies),
        feedback.generated_rhs,
        feedback.solved_vector,
        feedback.reset_call_count,
        feedback.reset_node_count,
        feedback.max_matrix_anchor_error,
    };
}

}  // namespace shift::runtime::physics
