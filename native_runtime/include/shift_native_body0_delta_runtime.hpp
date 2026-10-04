#pragma once

#include "shift_fun_007682c0_body0_delta_consumer_chain.hpp"

namespace shift::runtime {

struct NativeRuntimeState;

inline constexpr const char* kNativeBody0DeltaRuntimeFormat =
    "SHIFT.NativeBody0DeltaRuntime/1";

physics::Fun007682c0Body0DeltaConsumerChainResult
execute_explicit_outer_update_with_native_body0_delta_consumer(
    NativeRuntimeState& runtime,
    double outer_timestep,
    const physics::Fun0076d100MotionReadEffectNativeBodyProvider& physics_pass_provider,
    const physics::Fun00765470MachineScalarHalfStepProvider& half_step_provider,
    const physics::Fun007b8810PostHalfStepCallback& post_half_step,
    const physics::GlobalVehicleBodyOwnerIdentityHandoff& owner_handoff);

}  // namespace shift::runtime
