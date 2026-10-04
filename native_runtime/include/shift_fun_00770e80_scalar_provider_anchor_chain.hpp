#pragma once

#include "shift_fun_00770e80_composed_anchor_chain.hpp"
#include "shift_fun_007afdd0_scalar_provider_join.hpp"

#include <array>
#include <cstddef>
#include <cstdint>
#include <functional>
#include <vector>

namespace shift::runtime::physics {

inline constexpr const char* kNativeFun00770e80ScalarProviderAnchorChainFormat =
    "SHIFT.NativeFun00770e80ScalarProviderAnchorChain/1";

struct Fun00765470MachineScalarHalfStepInput {
    Fun00763570MachineInput machine{};
    PreparedGeneratedBodyConstraintFrame source{};
    PreparedConstraintSampleRelationFrame relations{};
    PreparedConstraintRelationResetFrame reset_state{};
    PreparedBuiltinSolverFrame solver_topology{};
    PreparedPostSolveBodyProjection projection{};
    Fun007afdd0ScalarProvider scalar_provider{};
    double tolerance = 1e-10;
};

using Fun00765470MachineScalarHalfStepProvider =
    std::function<Fun00765470MachineScalarHalfStepInput(
        std::size_t pass_index,
        double half_timestep,
        const std::vector<std::uint8_t>& current_body_bytes)>;

struct Fun00770e80ScalarProviderAnchorChainResult {
    Fun00770e80ComposedAnchorChainResult joined{};
    std::array<std::size_t, kFun00770e80PassCount> scalar_provider_call_counts{};
    std::array<std::size_t, kFun00770e80PassCount> applied_rotation_counts{};
    std::array<std::size_t, kFun00770e80PassCount> zero_noop_counts{};
    std::size_t scalar_provider_call_count = 0u;
    std::size_t applied_rotation_count = 0u;
    std::size_t zero_noop_count = 0u;
};

Fun00770e80ScalarProviderAnchorChainResult
execute_fun_00770e80_scalar_provider_anchor_chain(
    double outer_timestep,
    const std::vector<std::uint8_t>& initial_body_bytes,
    const Fun0076d100AnchorProvider& physics_pass_provider,
    const Fun00765470MachineScalarHalfStepProvider& half_step_provider,
    const Fun007b8810PostHalfStepCallback& post_half_step,
    const Fun0076d100PostAnchorBodyStateMutator& post_anchor_body_mutator = {});

}  // namespace shift::runtime::physics
