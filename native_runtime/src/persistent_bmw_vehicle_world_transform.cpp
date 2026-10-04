#include "shift_persistent_bmw_vehicle_world_transform.hpp"

#include "runtime_state.hpp"

#include <limits>
#include <stdexcept>

namespace shift::runtime::physics {
namespace {

PersistentBmwVehicleWorldTransformSnapshot snapshot_from_state(
    const PersistentBmwVehicleWorldTransformState& state) {
    PersistentBmwVehicleWorldTransformSnapshot out{};
    out.body_index = state.body_index;
    out.source_runtime_body_count = state.source_runtime_body_count;
    out.source_pose_snapshot_generation =
        state.source_pose_snapshot_generation;
    out.source_explicit_update_count = state.source_explicit_update_count;
    out.commit_generation = state.commit_generation;
    out.source_origin = state.source_origin;
    out.source_basis = state.source_basis;
    out.vehicle_world_matrix = state.vehicle_world_matrix;
    return out;
}

void require_current_source_pose(
    const PersistentBmwVehicleWorldTransformState& state,
    const shift::runtime::NativeRuntimeState& runtime) {
    if (!state.ready) {
        throw std::runtime_error(
            "persistent BMW vehicle world transform is not ready");
    }
    if (!runtime.outer_update.initialized) {
        throw std::runtime_error(
            "persistent BMW vehicle world transform requires initialized outer state");
    }
    if (state.body_index != 0u ||
        state.source_runtime_body_count != runtime.outer_update.body_count ||
        state.body_index >= runtime.outer_update.body_pose_snapshots.size() ||
        state.source_pose_snapshot_generation !=
            runtime.outer_update.body_pose_snapshot_generation ||
        state.source_explicit_update_count !=
            runtime.outer_update.explicit_update_count) {
        throw std::logic_error(
            "persistent BMW vehicle world transform is stale relative to BODY pose state");
    }

    const auto& current =
        runtime.outer_update.body_pose_snapshots[state.body_index];
    if (current.body_index != state.body_index ||
        current.origin != state.source_origin ||
        current.basis != state.source_basis) {
        throw std::logic_error(
            "persistent BMW vehicle world transform source BODY pose changed without matching provenance");
    }
}

}  // namespace

PersistentBmwVehicleWorldTransformSnapshot
commit_bmw_vehicle_world_transform(
    PersistentBmwVehicleWorldTransformState& state,
    const shift::runtime::NativeRuntimeState& runtime,
    const GlobalVehicleBodyOwnerIdentityHandoff& identity,
    const ProvenBmwVhfBindFrame& vhf_bind,
    const ProvenBmwBody0BindFrame& body0_bind) {

    const auto handoff = build_bmw_vehicle_world_matrix_runtime_handoff(
        runtime,
        identity,
        vhf_bind,
        body0_bind);

    if (state.commit_generation ==
        std::numeric_limits<std::uint64_t>::max()) {
        throw std::overflow_error(
            "persistent BMW vehicle world transform generation overflow");
    }
    if (!runtime.outer_update.initialized ||
        handoff.pose.body_index != 0u ||
        handoff.runtime_body_count != runtime.outer_update.body_count ||
        handoff.pose.snapshot_generation !=
            runtime.outer_update.body_pose_snapshot_generation ||
        handoff.explicit_update_count !=
            runtime.outer_update.explicit_update_count) {
        throw std::logic_error(
            "Phase 705 handoff provenance no longer matches runtime outer state");
    }

    PersistentBmwVehicleWorldTransformState next{};
    next.ready = true;
    next.body_index = handoff.pose.body_index;
    next.source_runtime_body_count = handoff.runtime_body_count;
    next.source_pose_snapshot_generation = handoff.pose.snapshot_generation;
    next.source_explicit_update_count = handoff.explicit_update_count;
    next.commit_generation = state.commit_generation + 1u;
    next.source_origin = handoff.pose.origin;
    next.source_basis = handoff.pose.basis;
    next.vehicle_world_matrix = handoff.vehicle_world_matrix;

    state = next;
    return snapshot_from_state(state);
}

PersistentBmwVehicleWorldTransformSnapshot
read_current_bmw_vehicle_world_transform(
    const PersistentBmwVehicleWorldTransformState& state,
    const shift::runtime::NativeRuntimeState& runtime) {
    require_current_source_pose(state, runtime);
    return snapshot_from_state(state);
}

}  // namespace shift::runtime::physics
