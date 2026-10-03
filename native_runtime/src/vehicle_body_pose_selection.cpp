#include "shift_vehicle_body_pose_selection.hpp"

#include <cmath>
#include <cstddef>
#include <stdexcept>

namespace shift::runtime::physics {
namespace {

void require_finite_pose(const PersistentBodyPoseSnapshot& snapshot) {
    for (double value : snapshot.origin) {
        if (!std::isfinite(value)) {
            throw std::invalid_argument(
                "selected vehicle BODY pose origin contains non-finite value");
        }
    }
    for (float value : snapshot.basis) {
        if (!std::isfinite(value)) {
            throw std::invalid_argument(
                "selected vehicle BODY pose basis contains non-finite value");
        }
    }
}

}  // namespace

SelectedVehicleBodyPose select_proven_vehicle_body_pose(
    const std::vector<PersistentBodyPoseSnapshot>& snapshots,
    std::uint64_t snapshot_generation,
    std::uint64_t explicit_update_count,
    const VehicleBodyIdentitySelection& selection) {
    if (!selection.selection_proven) {
        throw std::invalid_argument(
            "vehicle BODY pose selection requires proven BODY identity");
    }
    if (snapshot_generation != explicit_update_count) {
        throw std::logic_error(
            "vehicle BODY pose snapshot generation is not synchronized with persistent update state");
    }
    if (snapshots.empty()) {
        throw std::invalid_argument(
            "vehicle BODY pose selection requires persistent BODY snapshots");
    }
    if (selection.body_index >= snapshots.size()) {
        throw std::out_of_range(
            "vehicle BODY pose selected BODY index exceeds persistent snapshot domain");
    }

    const auto& snapshot = snapshots[selection.body_index];
    if (snapshot.body_index != selection.body_index) {
        throw std::logic_error(
            "vehicle BODY pose selected snapshot identity does not match BODY index");
    }
    require_finite_pose(snapshot);

    SelectedVehicleBodyPose result{};
    result.body_index = selection.body_index;
    result.snapshot_generation = snapshot_generation;
    result.origin = snapshot.origin;
    result.basis = snapshot.basis;
    return result;
}

}  // namespace shift::runtime::physics
