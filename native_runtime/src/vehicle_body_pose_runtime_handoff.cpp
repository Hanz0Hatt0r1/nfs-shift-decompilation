#include "shift_vehicle_body_pose_runtime_handoff.hpp"

#include "runtime_state.hpp"

#include <stdexcept>

namespace shift::runtime::physics {

VehicleBodyPoseRuntimeHandoffResult build_vehicle_body_pose_runtime_handoff(
    const shift::runtime::NativeRuntimeState& runtime,
    const VehicleBodyIdentitySelection& selection) {
    if (!runtime.physics.workspace.ready) {
        throw std::runtime_error(
            "vehicle BODY pose runtime handoff requires ready physics workspace");
    }
    if (!runtime.physics.participant_ready ||
        !runtime.physics.participant_identity_join_proven) {
        throw std::runtime_error(
            "vehicle BODY pose runtime handoff requires admitted participant identity");
    }
    if (!runtime.outer_update.initialized) {
        throw std::runtime_error(
            "vehicle BODY pose runtime handoff requires initialized persistent outer state");
    }
    if (runtime.outer_update.body_count != runtime.physics.workspace.body_count) {
        throw std::logic_error(
            "vehicle BODY pose runtime handoff BODY cardinality disagrees with workspace");
    }
    if (runtime.outer_update.body_pose_snapshots.size() !=
        runtime.outer_update.body_count) {
        throw std::logic_error(
            "vehicle BODY pose runtime handoff snapshot cardinality mismatch");
    }

    VehicleBodyPoseRuntimeHandoffResult result{};
    result.pose = select_proven_vehicle_body_pose(
        runtime.outer_update.body_pose_snapshots,
        runtime.outer_update.body_pose_snapshot_generation,
        runtime.outer_update.explicit_update_count,
        selection);
    result.runtime_body_count = runtime.outer_update.body_count;
    result.explicit_update_count = runtime.outer_update.explicit_update_count;
    return result;
}

}  // namespace shift::runtime::physics
