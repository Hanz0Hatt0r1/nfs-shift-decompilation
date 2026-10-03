#pragma once

#include "shift_persistent_body_pose_snapshot.hpp"

#include <cstdint>
#include <vector>

namespace shift::runtime::physics {

inline constexpr const char* kNativeVehicleBodyPoseSelectionFormat =
    "SHIFT.NativeVehicleBodyPoseSelection/1";

struct VehicleBodyIdentitySelection {
    bool selection_proven = false;
    std::uint32_t body_index = 0u;
};

struct SelectedVehicleBodyPose {
    std::uint32_t body_index = 0u;
    std::uint64_t snapshot_generation = 0u;
    BodyFrameIntegrationVector3d origin{};
    ConstraintRefreshFrame3f basis{};
};

SelectedVehicleBodyPose select_proven_vehicle_body_pose(
    const std::vector<PersistentBodyPoseSnapshot>& snapshots,
    std::uint64_t snapshot_generation,
    std::uint64_t explicit_update_count,
    const VehicleBodyIdentitySelection& selection);

}  // namespace shift::runtime::physics
