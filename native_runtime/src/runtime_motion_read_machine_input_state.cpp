#include "runtime_motion_read_machine_input_state.hpp"

#include "shift_persistent_body_pose_snapshot.hpp"

#include <stdexcept>
#include <utility>
#include <vector>

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
    const physics::Fun007b8810PostHalfStepCallback& post_half_step) {
    state.validate_runtime_boundary(
        runtime_body_count,
        workspace_ready,
        participant_ready,
        participant_identity_join_proven);

    auto result =
        physics::execute_fun_00770e80_motion_read_machine_input_provider_chain(
            outer_timestep,
            state.body_bytes,
            physics_pass_provider,
            half_step_provider,
            post_half_step);

    const std::size_t expected_bytes =
        static_cast<std::size_t>(runtime_body_count) * physics::kBodyRecordSize;
    if (result.joined.joined.joined.final_body_bytes.size() != expected_bytes) {
        throw std::runtime_error(
            "explicit motion-read-machine-input update returned malformed BODY state");
    }

    std::vector<std::uint8_t> committed_body_bytes =
        result.joined.joined.joined.final_body_bytes;
    auto committed_pose_snapshots =
        physics::decode_persistent_body_pose_snapshots(
            committed_body_bytes,
            runtime_body_count);

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
    state.last_zero_noop_count = result.joined.joined.zero_noop_count;
    state.last_contact_outer_input_provider_call_count =
        result.joined.contact_outer_input_provider_call_count;
    state.last_contact_outer_native_call_count =
        result.joined.contact_outer_native_call_count;
    state.last_contact_outer_gate_open_count =
        result.joined.contact_outer_gate_open_count;

    // Historical telemetry fields are retained for ABI compatibility. The
    // active path no longer receives a precomputed effect from an external
    // provider: this count now records the one native machine-effect execution
    // at each pass anchor. No external delta consumer participates.
    state.last_motion_read_effect_provider_call_count =
        result.motion_read_native_effect_call_count;
    state.last_motion_read_delta_consumer_call_count = 0u;
    state.last_motion_read_gate_open_count =
        result.motion_read_gate_open_count;

    ++state.explicit_update_count;
    state.body_pose_snapshot_generation = state.explicit_update_count;
    return result;
}

}  // namespace shift::runtime
