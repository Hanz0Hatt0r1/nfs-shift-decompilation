#pragma once

#include "shift_fun_00763570_machine_feedback_join.hpp"
#include "shift_fun_0076d100_anchor_sequence.hpp"
#include "shift_fun_00770e80_two_half_step_schedule.hpp"

#include <array>
#include <cstddef>
#include <cstdint>
#include <functional>
#include <vector>

namespace shift::runtime::physics {

inline constexpr const char* kNativeFun00770e80ComposedAnchorChainFormat =
    "SHIFT.NativeFun00770e80ComposedAnchorChain/1";

struct Fun0076d100AnchorCallbacks {
    Fun0076d100AnchorCallback contact_factor;
    Fun0076d100AnchorCallback wheel_update;
    Fun0076d100AnchorCallback contact_response;
    Fun0076d100AnchorCallback contact_outer;
    Fun0076d100AnchorCallback motion_read_gate;
};

using Fun0076d100AnchorProvider =
    std::function<Fun0076d100AnchorCallbacks(std::size_t pass_index)>;

// Executes after the complete FUN_0076d100 required anchor sequence for one
// pass, and before the corresponding FUN_00765470 half-step consumes BODY
// bytes. Existing callers omit it and preserve the pre-Phase-707 behavior.
using Fun0076d100PostAnchorBodyStateMutator =
    std::function<void(
        std::size_t pass_index,
        std::vector<std::uint8_t>& current_body_bytes)>;

struct Fun00765470MachineHalfStepInput {
    Fun00763570MachineInput machine{};
    PreparedGeneratedBodyConstraintFrame source{};
    PreparedConstraintSampleRelationFrame relations{};
    PreparedConstraintRelationResetFrame reset_state{};
    PreparedBuiltinSolverFrame solver_topology{};
    PreparedPostSolveBodyProjection projection{};
    BodyBasisRotationCallback basis_rotation{};
    double tolerance = 1e-10;
};

using Fun00765470MachineHalfStepProvider =
    std::function<Fun00765470MachineHalfStepInput(
        std::size_t pass_index,
        double half_timestep,
        const std::vector<std::uint8_t>& current_body_bytes)>;

struct Fun00770e80ComposedAnchorChainResult {
    Fun00770e80TwoHalfStepScheduleResult schedule{};
    std::array<Fun0076d100AnchorSequenceResult, kFun00770e80PassCount>
        physics_passes{};
    std::array<Fun00763570MachineFeedbackJoinResult, kFun00770e80PassCount>
        half_steps{};
    std::vector<std::uint8_t> final_body_bytes;
    std::size_t physics_pass_provider_call_count = 0u;
    std::size_t half_step_provider_call_count = 0u;
};

Fun00770e80ComposedAnchorChainResult execute_fun_00770e80_composed_anchor_chain(
    double outer_timestep,
    const std::vector<std::uint8_t>& initial_body_bytes,
    const Fun0076d100AnchorProvider& physics_pass_provider,
    const Fun00765470MachineHalfStepProvider& half_step_provider,
    const Fun007b8810PostHalfStepCallback& post_half_step,
    const Fun0076d100PostAnchorBodyStateMutator& post_anchor_body_mutator = {});

}  // namespace shift::runtime::physics
