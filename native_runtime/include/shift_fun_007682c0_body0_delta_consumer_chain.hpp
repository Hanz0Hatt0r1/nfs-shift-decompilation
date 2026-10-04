#pragma once

#include "shift_body_record_adapter.hpp"
#include "shift_fun_00770e80_contact_outer_provider_chain.hpp"
#include "shift_fun_00770e80_motion_read_effect_provider_chain.hpp"
#include "shift_global_vehicle_body_owner_selection.hpp"

#include <array>
#include <cstddef>
#include <cstdint>
#include <functional>
#include <vector>

namespace shift::runtime::physics {

inline constexpr const char* kNativeFun007682c0Body0DeltaConsumerChainFormat =
    "SHIFT.NativeFun007682c0Body0DeltaConsumerChain/1";
inline constexpr std::size_t kFun007682c0AccumulatorYOffset = 0x50u;

struct Fun0076d100MotionReadEffectNativeBodyCallbacks {
    Fun0076d100AnchorCallback contact_factor{};
    Fun0076d100AnchorCallback wheel_update{};
    Fun0076d100AnchorCallback contact_response{};
    Fun007675f0ContactOuterInputProvider contact_outer_input_provider{};
    Fun007682c0EffectProvider motion_read_effect_provider{};
};

using Fun0076d100MotionReadEffectNativeBodyProvider =
    std::function<Fun0076d100MotionReadEffectNativeBodyCallbacks(
        std::size_t pass_index)>;

struct Fun007682c0Body0DeltaConsumerChainResult {
    Fun00770e80ContactOuterProviderChainResult joined{};
    std::array<Fun007682c0AccumulatorEffect, kFun00770e80PassCount>
        motion_read_effects{};
    std::array<bool, kFun00770e80PassCount>
        motion_read_effect_present{};
    std::array<std::size_t, kFun00770e80PassCount>
        motion_read_effect_provider_call_counts{};
    std::array<std::size_t, kFun00770e80PassCount>
        native_delta_application_counts{};
    std::array<double, kFun00770e80PassCount>
        accumulator_y_after_application{};
    std::uint32_t selected_body_index = 0u;
    std::size_t motion_read_effect_provider_call_count = 0u;
    std::size_t native_delta_application_count = 0u;
    std::size_t motion_read_gate_open_count = 0u;
};

double apply_fun_007682c0_body_accumulator_y_delta(
    std::vector<std::uint8_t>& body_bytes,
    std::uint32_t body_index,
    double accumulator_y_delta);

Fun007682c0Body0DeltaConsumerChainResult
execute_fun_00770e80_motion_read_effect_native_body0_consumer_chain(
    double outer_timestep,
    const std::vector<std::uint8_t>& initial_body_bytes,
    const Fun0076d100MotionReadEffectNativeBodyProvider& physics_pass_provider,
    const Fun00765470MachineScalarHalfStepProvider& half_step_provider,
    const Fun007b8810PostHalfStepCallback& post_half_step,
    const GlobalVehicleBodyOwnerIdentityHandoff& owner_handoff);

}  // namespace shift::runtime::physics
