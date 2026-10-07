#pragma once

#include "runtime_explicit_outer_update_state.hpp"
#include "shift_fun_00770e80_motion_read_machine_input_provider_chain.hpp"

#include <cstdint>

namespace shift::runtime {

physics::Fun00770e80MotionReadMachineInputProviderChainResult
execute_explicit_motion_read_machine_input_update(
    ExplicitOuterUpdateRuntimeState& state,
    std::uint32_t runtime_body_count,
    bool workspace_ready,
    bool participant_ready,
    bool participant_identity_join_proven,
    double outer_timestep,
    const physics::Fun0076d100MotionReadMachineInputProvider& physics_pass_provider,
    const physics::Fun00765470MachineScalarHalfStepProvider& half_step_provider,
    const physics::Fun007b8810PostHalfStepCallback& post_half_step);

}  // namespace shift::runtime
