#pragma once

#include "shift_contact_outer_kernel.hpp"
#include "shift_fun_00770e80_scalar_provider_anchor_chain.hpp"

#include <array>
#include <cstddef>
#include <functional>

namespace shift::runtime::physics {

inline constexpr const char* kNativeFun00770e80ContactOuterProviderChainFormat =
    "SHIFT.NativeFun00770e80ContactOuterProviderChain/1";

using Fun007675f0ContactOuterInputProvider =
    std::function<ContactOuterExternalInput()>;
using Fun007675f0DistanceStateCommit = std::function<void(double)>;

struct Fun0076d100ContactOuterProviderCallbacks {
    Fun0076d100AnchorCallback contact_factor{};
    Fun0076d100AnchorCallback wheel_update{};
    Fun0076d100AnchorCallback contact_response{};
    Fun007675f0ContactOuterInputProvider contact_outer_input_provider{};
    // Optional internal ownership hook. NativeVehicleProviderSession uses this
    // to commit FUN_007675f0's filtered distance result back to its persistent
    // HDVehicle+0x4080 state. Historical lower-chain fixtures may omit it.
    Fun007675f0DistanceStateCommit contact_outer_distance_state_commit{};
    Fun0076d100AnchorCallback motion_read_gate{};
    Fun0076d100PostPassBodyMutator post_pass_body_mutator{};
};

using Fun0076d100ContactOuterProvider =
    std::function<Fun0076d100ContactOuterProviderCallbacks(
        std::size_t pass_index)>;

struct Fun00770e80ContactOuterProviderChainResult {
    Fun00770e80ScalarProviderAnchorChainResult joined{};
    std::array<ContactOuterKernelResult, kFun00770e80PassCount>
        contact_outer_results{};
    std::array<Fun007675f0BodyMotion, kFun00770e80PassCount>
        body_motion_inputs{};
    std::array<bool, kFun00770e80PassCount> contact_outer_result_present{};
    std::array<bool, kFun00770e80PassCount> body_motion_input_present{};
    std::array<std::size_t, kFun00770e80PassCount>
        contact_outer_input_provider_call_counts{};
    std::array<std::size_t, kFun00770e80PassCount>
        contact_outer_native_call_counts{};
    std::array<std::size_t, kFun00770e80PassCount>
        contact_outer_distance_state_commit_counts{};
    std::size_t contact_outer_input_provider_call_count = 0u;
    std::size_t contact_outer_native_call_count = 0u;
    std::size_t contact_outer_distance_state_commit_count = 0u;
    std::size_t contact_outer_gate_open_count = 0u;
};

Fun00770e80ContactOuterProviderChainResult
execute_fun_00770e80_contact_outer_provider_chain(
    double outer_timestep,
    const std::vector<std::uint8_t>& initial_body_bytes,
    const Fun0076d100ContactOuterProvider& physics_pass_provider,
    const Fun00765470MachineScalarHalfStepProvider& half_step_provider,
    const Fun007b8810PostHalfStepCallback& post_half_step);

}  // namespace shift::runtime::physics
