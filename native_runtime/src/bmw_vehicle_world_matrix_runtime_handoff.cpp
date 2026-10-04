#include "shift_bmw_vehicle_world_matrix_runtime_handoff.hpp"

namespace shift::runtime::physics {

BmwVehicleWorldMatrixRuntimeHandoffResult
build_bmw_vehicle_world_matrix_runtime_handoff(
    const shift::runtime::NativeRuntimeState& runtime,
    const GlobalVehicleBodyOwnerIdentityHandoff& identity,
    const ProvenBmwVhfBindFrame& vhf_bind,
    const ProvenBmwBody0BindFrame& body0_bind) {

    const auto pose_handoff =
        build_global_vehicle_body_pose_runtime_handoff(runtime, identity);
    const auto composition =
        compose_bmw_body0_pose_to_vehicle_world_matrix(
            pose_handoff.pose,
            vhf_bind,
            body0_bind);

    BmwVehicleWorldMatrixRuntimeHandoffResult result{};
    result.pose = pose_handoff.pose;
    result.body0_runtime_row = composition.body0_runtime_row;
    result.vehicle_world_matrix = composition.vehicle_world_matrix;
    result.runtime_body_count = pose_handoff.runtime_body_count;
    result.explicit_update_count = pose_handoff.explicit_update_count;
    return result;
}

}  // namespace shift::runtime::physics
