#pragma once

#include "shift_constraint_sample_relation_frame.hpp"

#include <cstddef>
#include <cstdint>
#include <string>
#include <vector>

namespace shift::runtime::physics {

inline constexpr const char* kNativeConstraintRelationResetFrameFormat =
    "SHIFT.NativeConstraintRelationResetFrame/1";
inline constexpr const char*
    kNativeConstraintRelationResetFramePacketFormat =
        "SHIFT.NativeConstraintRelationResetFramePacket/1";

struct PreparedConstraintRelationResetFrame {
    std::vector<std::uint8_t> joint_state_bit0;
    std::vector<std::uint8_t> hinge_state_bit0;
    std::vector<std::uint8_t> bar_state_bit0;
};

struct ConstraintRelationResetSelectionResult {
    std::vector<std::size_t> reset_nodes;
    std::size_t scalar_count = 0;
    std::size_t joint_relation_count = 0;
    std::size_t hinge_relation_count = 0;
    std::size_t bar_relation_count = 0;
    std::size_t selected_joint_relation_count = 0;
    std::size_t selected_hinge_relation_count = 0;
    std::size_t selected_bar_relation_count = 0;
};

PreparedConstraintRelationResetFrame
load_prepared_constraint_relation_reset_frame(
    const std::string& path);

ConstraintRelationResetSelectionResult
select_fun_007b3f40_reset_nodes(
    const PreparedGeneratedBodyConstraintFrame& frame,
    const PreparedConstraintSampleRelationFrame& relations,
    const PreparedConstraintRelationResetFrame& reset_state);

std::vector<std::size_t>
normalize_fun_007b3f40_reset_nodes(
    const std::vector<std::size_t>& reset_call_nodes);

void verify_fun_007b3f40_reset_nodes_match(
    const ConstraintRelationResetSelectionResult& selection,
    const std::vector<std::size_t>& solver_frame_reset_nodes);

}  // namespace shift::runtime::physics
