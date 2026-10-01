#pragma once

#include "shift_constraint_sample_relation_frame.hpp"
#include "shift_generated_body_constraint_frame.hpp"

#include <cstddef>
#include <cstdint>
#include <string>
#include <vector>

namespace shift::runtime::physics {

inline constexpr const char* kNativeConstraintResetStateFrameFormat =
    "SHIFT.NativeConstraintResetStateFrame/1";
inline constexpr const char* kNativeConstraintResetStateFramePacketFormat =
    "SHIFT.NativeConstraintResetStateFramePacket/1";

struct PreparedConstraintResetStateFrame {
    std::size_t body_count = 0;
    std::vector<std::uint32_t> joint_runtime_flags;
    std::vector<std::uint32_t> hinge_runtime_flags;
    std::vector<std::uint32_t> bar_runtime_flags;
};

struct ConstraintResetSelectionResult {
    std::vector<std::size_t> ordered_reset_nodes;
    std::vector<std::size_t> reset_nodes;
    std::size_t joint_relation_count = 0;
    std::size_t hinge_relation_count = 0;
    std::size_t bar_relation_count = 0;
    std::size_t selected_joint_relation_count = 0;
    std::size_t selected_hinge_relation_count = 0;
    std::size_t selected_bar_relation_count = 0;
};

PreparedConstraintResetStateFrame
load_prepared_constraint_reset_state_frame(
    const std::string& path);

ConstraintResetSelectionResult
derive_fun_007b2210_reset_nodes(
    const PreparedGeneratedBodyConstraintFrame& frame,
    const PreparedConstraintSampleRelationFrame& relations,
    const PreparedConstraintResetStateFrame& reset_state);

}  // namespace shift::runtime::physics
