#pragma once

#include "shift_bmw_vehicle_world_matrix_runtime_handoff.hpp"

#include <cstdint>

namespace shift::runtime::physics {

inline constexpr const char* kPersistentBmwVehicleWorldTransformFormat =
    "SHIFT.PersistentBMWVehicleWorldTransform/1";

struct PersistentBmwVehicleWorldTransformState {
    bool ready = false;
    std::uint32_t body_index = 0u;
    std::uint64_t source_pose_snapshot_generation = 0u;
    std::uint64_t source_explicit_update_count = 0u;
    std::uint64_t commit_generation = 0u;
    shift::runtime::render::VehicleWorldMatrix vehicle_world_matrix{};
};

struct PersistentBmwVehicleWorldTransformSnapshot {
    std::uint32_t body_index = 0u;
    std::uint64_t source_pose_snapshot_generation = 0u;
    std::uint64_t source_explicit_update_count = 0u;
    std::uint64_t commit_generation = 0u;
    shift::runtime::render::VehicleWorldMatrix vehicle_world_matrix{};
};

PersistentBmwVehicleWorldTransformSnapshot
commit_bmw_vehicle_world_transform(
    PersistentBmwVehicleWorldTransformState& state,
    const shift::runtime::NativeRuntimeState& runtime,
    const GlobalVehicleBodyOwnerIdentityHandoff& identity,
    const ProvenBmwVhfBindFrame& vhf_bind,
    const ProvenBmwBody0BindFrame& body0_bind);

PersistentBmwVehicleWorldTransformSnapshot
read_current_bmw_vehicle_world_transform(
    const PersistentBmwVehicleWorldTransformState& state,
    const shift::runtime::NativeRuntimeState& runtime);

}  // namespace shift::runtime::physics
