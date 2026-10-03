#pragma once

#include "shift_body_record_adapter.hpp"
#include "shift_body_state_feedback.hpp"

#include <cstddef>
#include <cstdint>
#include <vector>

namespace shift::runtime::physics {

inline constexpr const char* kNativeBodyFeedbackRecordBridgeFormat =
    "SHIFT.NativeBodyFeedbackRecordBridge/1";

struct BodyFeedbackRecordBridgeResult {
    std::vector<std::uint8_t> body_bytes;
    std::vector<double> generated_rhs;
    std::vector<double> solved_vector;
    std::size_t reset_call_count = 0;
    std::size_t reset_node_count = 0;
    double max_matrix_anchor_error = 0.0;
};

std::vector<BodyAccumulatorState> decode_body_accumulators_from_buffer(
    const std::vector<std::uint8_t>& body_bytes,
    std::size_t body_count);

std::vector<std::uint8_t> apply_body_accumulators_to_buffer(
    const std::vector<std::uint8_t>& body_bytes,
    const std::vector<BodyAccumulatorState>& bodies);

BodyFeedbackRecordBridgeResult execute_body_state_feedback_raw_step(
    const PreparedGeneratedBodyConstraintFrame& source,
    const PreparedConstraintSampleRelationFrame& relations,
    const PreparedConstraintRelationResetFrame& reset_state,
    const PreparedBuiltinSolverFrame& solver_topology,
    const PreparedPostSolveBodyProjection& projection,
    const std::vector<std::uint8_t>& body_bytes,
    double tolerance = 1e-10);

}  // namespace shift::runtime::physics
