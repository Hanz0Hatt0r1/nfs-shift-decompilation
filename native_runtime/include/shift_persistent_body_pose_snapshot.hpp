#pragma once

#include "shift_body_record_adapter.hpp"

#include <cstddef>
#include <cstdint>
#include <vector>

namespace shift::runtime::physics {

inline constexpr const char* kNativePersistentBodyPoseSnapshotFormat =
    "SHIFT.NativePersistentBodyPoseSnapshot/1";

struct PersistentBodyPoseSnapshot {
    std::size_t body_index = 0u;
    BodyFrameIntegrationVector3d origin{};
    ConstraintRefreshFrame3f basis{};
};

std::vector<PersistentBodyPoseSnapshot> decode_persistent_body_pose_snapshots(
    const std::vector<std::uint8_t>& body_bytes,
    std::uint32_t body_count);

}  // namespace shift::runtime::physics
