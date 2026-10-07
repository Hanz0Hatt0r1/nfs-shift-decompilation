#pragma once

#include "shift_fun_007682c0_machine_effect.hpp"
#include "shift_fun_00770e80_contact_outer_provider_chain.hpp"

#include <array>
#include <cstddef>
#include <functional>
#include <vector>

namespace shift::runtime::physics {

inline constexpr const char*
    kNativeFun00770e80MotionReadMachineInputProviderChainFormat =
        "SHIFT.NativeFun00770e80MotionReadMachineInputProviderChain/1";

using Fun007682c0MachineInputProvider =
    std::function<Fun007682c0MachineInput()>;

struct Fun0076d100MotionReadMachineInputProviderCallbacks {
    Fun0076d100AnchorCallback contact_factor{};
    Fun0076d100AnchorCallback wheel_update{};
    Fun0076d100AnchorCallback contact_response{};
    Fun007675f0ContactOuterInputProvider contact_outer_input_provider{};
    Fun007675f0DistanceStateCommit contact_outer_distance_state_commit{};
    Fun007682c0MachineInputProvider motion_read_input_provider{};
};

using Fun0076d100MotionReadMachineInputProvider =
    std::function<Fun0076d100MotionReadMachineInputProviderCallbacks(
        std::size_t pass_index)>;

struct Fun00770e80MotionReadMachineInputProviderChainResult {
    Fun00770e80ContactOuterProviderChainResult joined{};
    std::array<Fun007682c0MachineInput, kFun00770e80PassCount>
        motion_read_inputs{};
    std::array<Fun007682c0MachineEffectResult, kFun00770e80PassCount>
        motion_read_results{};
    std::array<bool, kFun00770e80PassCount> motion_read_input_present{};
    std::array<bool, kFun00770e80PassCount> motion_read_result_present{};
    std::array<std::size_t, kFun00770e80PassCount>
        motion_read_input_provider_call_counts{};
    std::array<std::size_t, kFun00770e80PassCount>
        motion_read_native_effect_call_counts{};
    std::array<std::size_t, kFun00770e80PassCount>
        motion_read_delta_application_call_counts{};
    std::size_t motion_read_input_provider_call_count = 0u;
    std::size_t motion_read_native_effect_call_count = 0u;
    std::size_t motion_read_delta_application_call_count = 0u;
    std::size_t motion_read_gate_open_count = 0u;
};

Fun00770e80MotionReadMachineInputProviderChainResult
execute_fun_00770e80_motion_read_machine_input_provider_chain(
    double outer_timestep,
    const std::vector<std::uint8_t>& initial_body_bytes,
    const Fun0076d100MotionReadMachineInputProvider& physics_pass_provider,
    const Fun00765470MachineScalarHalfStepProvider& half_step_provider,
    const Fun007b8810PostHalfStepCallback& post_half_step);

}  // namespace shift::runtime::physics
