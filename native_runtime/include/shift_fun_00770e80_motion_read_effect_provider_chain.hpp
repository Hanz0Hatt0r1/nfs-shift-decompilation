#pragma once

#include "shift_fun_00770e80_contact_outer_provider_chain.hpp"

#include <array>
#include <cstddef>
#include <cstdint>
#include <functional>
#include <vector>

namespace shift::runtime::physics {

inline constexpr const char* kNativeFun00770e80MotionReadEffectProviderChainFormat =
    "SHIFT.NativeFun00770e80MotionReadEffectProviderChain/1";

struct Fun007682c0AccumulatorEffect {
    bool gate_open = false;
    double accumulator_y_delta = 0.0;
};

using Fun007682c0EffectProvider =
    std::function<Fun007682c0AccumulatorEffect()>;
// Compatibility/observability hook only. The source-backed BODY0 +0x50 write is
// internal to this chain and does not depend on this callback being present.
using Fun007682c0AccumulatorDeltaConsumer =
    std::function<void(double accumulator_y_delta)>;

struct Fun0076d100MotionReadEffectProviderCallbacks {
    Fun0076d100AnchorCallback contact_factor{};
    Fun0076d100AnchorCallback wheel_update{};
    Fun0076d100AnchorCallback contact_response{};
    Fun007675f0ContactOuterInputProvider contact_outer_input_provider{};
    Fun007682c0EffectProvider motion_read_effect_provider{};
    Fun007682c0AccumulatorDeltaConsumer motion_read_delta_consumer{};
};

using Fun0076d100MotionReadEffectProvider =
    std::function<Fun0076d100MotionReadEffectProviderCallbacks(
        std::size_t pass_index)>;

struct Fun00770e80MotionReadEffectProviderChainResult {
    Fun00770e80ContactOuterProviderChainResult joined{};
    std::array<Fun007682c0AccumulatorEffect, kFun00770e80PassCount>
        motion_read_effects{};
    std::array<bool, kFun00770e80PassCount>
        motion_read_effect_present{};
    std::array<std::size_t, kFun00770e80PassCount>
        motion_read_effect_provider_call_counts{};
    std::array<std::size_t, kFun00770e80PassCount>
        motion_read_delta_application_call_counts{};
    std::array<std::size_t, kFun00770e80PassCount>
        motion_read_delta_consumer_call_counts{};
    std::size_t motion_read_effect_provider_call_count = 0u;
    std::size_t motion_read_delta_application_call_count = 0u;
    std::size_t motion_read_delta_consumer_call_count = 0u;
    std::size_t motion_read_gate_open_count = 0u;
};

Fun00770e80MotionReadEffectProviderChainResult
execute_fun_00770e80_motion_read_effect_provider_chain(
    double outer_timestep,
    const std::vector<std::uint8_t>& initial_body_bytes,
    const Fun0076d100MotionReadEffectProvider& physics_pass_provider,
    const Fun00765470MachineScalarHalfStepProvider& half_step_provider,
    const Fun007b8810PostHalfStepCallback& post_half_step);

}  // namespace shift::runtime::physics
