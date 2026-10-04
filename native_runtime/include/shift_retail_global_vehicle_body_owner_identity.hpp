#pragma once

#include "shift_persistent_bmw_vehicle_world_transform.hpp"

#include <cstdint>

namespace shift::runtime::physics {

inline constexpr const char* kRetailGlobalVehicleBodyOwnerIdentityFormat =
    "SHIFT.NativeRetailGlobalVehicleBodyOwnerIdentity/1";

struct RetailGlobalVehicleBodyOwnerIdentity {
    std::uint32_t global_vehicle_address = 0u;
    std::uint32_t body_owner_pointer_field_offset = 0u;
    bool body_array_owner_is_global_vehicle_base = false;
    bool body_array_owner_pointer_loaded_from_global_vehicle_base = false;
    GlobalVehicleBodyOwnerIdentityHandoff handoff{};
};

RetailGlobalVehicleBodyOwnerIdentity
retail_global_vehicle_body_owner_identity();

BmwVehicleWorldMatrixRuntimeHandoffResult
build_retail_bmw_vehicle_world_matrix_runtime_handoff(
    const shift::runtime::NativeRuntimeState& runtime,
    const ProvenBmwVhfBindFrame& vhf_bind,
    const ProvenBmwBody0BindFrame& body0_bind);

PersistentBmwVehicleWorldTransformSnapshot
commit_retail_bmw_vehicle_world_transform(
    PersistentBmwVehicleWorldTransformState& state,
    const shift::runtime::NativeRuntimeState& runtime,
    const ProvenBmwVhfBindFrame& vhf_bind,
    const ProvenBmwBody0BindFrame& body0_bind);

}  // namespace shift::runtime::physics
