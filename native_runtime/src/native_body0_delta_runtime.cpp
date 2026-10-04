#include "shift_native_body0_delta_runtime.hpp"

#include "runtime_state.hpp"

#include <stdexcept>
#include <utility>
#include <vector>

namespace shift::runtime {

physics::Fun007682c0Body0DeltaConsumerChainResult
execute_explicit_outer_update_with_native_body0_delta_consumer(
    NativeRuntimeState& runtime,
    double outer_timestep,
    const physics::Fun0076d100MotionReadEffectNativeBodyProvider& physics_pass_provider,
    const physics::Fun00765470MachineScalarHalfStepProvider& half_step_provider,
    const physics::Fun007b8810PostHalfStepCallback& post_half_step,
    const physics::GlobalVehicleBodyOwnerIdentityHandoff& owner_handoff) {
    runtime.outer_update.validate_runtime_boundary(
        runtime.physics.workspace.body_count,
        runtime.physics.workspace.ready,
        runtime.physics.participant_ready,
        runtime.physics.participant_identity_join_proven);

    auto result =
        physics::execute_fun_00770e80_motion_read_effect_native_body0_consumer_chain(
            outer_timestep,
            runtime.outer_update.body_bytes,
            physics_pass_provider,
            half_step_provider,
            post_half_step,
            owner_handoff);

    const auto& final_body_bytes =
        result.joined.joined.joined.final_body_bytes;
    const std::size_t expected_bytes =
        static_cast<std::size_t>(runtime.physics.workspace.body_count) *
        physics::kBodyRecordSize;
    if (final_body_bytes.size() != expected_bytes) {
        throw std::runtime_error(
            "Phase 707 native BODY0 delta chain returned malformed persistent BODY state");
    }

    // Decode every derived snapshot before mutating runtime state. A failure in
    // the native delta application, solver path, or pose decode leaves the
    // previously committed persistent state untouched.
    std::vector<std::uint8_t> committed_body_bytes = final_body_bytes;
    auto committed_pose_snapshots =
        physics::decode_persistent_body_pose_snapshots(
            committed_body_bytes,
            runtime.physics.workspace.body_count);

    auto& state = runtime.outer_update;
    state.body_bytes = std::move(committed_body_bytes);
    state.body_pose_snapshots = std::move(committed_pose_snapshots);
    state.body_byte_count = state.body_bytes.size();
    state.last_outer_timestep = outer_timestep;
    state.last_physics_pass_provider_call_count =
        result.joined.joined.joined.physics_pass_provider_call_count;
    state.last_half_step_provider_call_count =
        result.joined.joined.joined.half_step_provider_call_count;
    state.last_scalar_provider_call_count =
        result.joined.joined.scalar_provider_call_count;
    state.last_applied_rotation_count =
        result.joined.joined.applied_rotation_count;
    state.last_zero_noop_count =
        result.joined.joined.zero_noop_count;
    state.last_contact_outer_input_provider_call_count =
        result.joined.contact_outer_input_provider_call_count;
    state.last_contact_outer_native_call_count =
        result.joined.contact_outer_native_call_count;
    state.last_contact_outer_gate_open_count =
        result.joined.contact_outer_gate_open_count;
    state.last_motion_read_effect_provider_call_count =
        result.motion_read_effect_provider_call_count;
    // This legacy telemetry field now counts the concrete native consumer
    // application rather than an injected external callback.
    state.last_motion_read_delta_consumer_call_count =
        result.native_delta_application_count;
    state.last_motion_read_gate_open_count =
        result.motion_read_gate_open_count;
    ++state.explicit_update_count;
    state.body_pose_snapshot_generation = state.explicit_update_count;
    return result;
}

}  // namespace shift::runtime
