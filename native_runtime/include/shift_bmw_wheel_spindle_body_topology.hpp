#pragma once

#include "shift_constraint_relation_state_mutation.hpp"

#include <array>
#include <cstddef>

namespace shift::runtime::physics {

inline constexpr const char* kNativeBmwWheelSpindleBodyTopologyFormat =
    "SHIFT.NativeBMWWheelSpindleBodyTopology/1";
inline constexpr std::size_t kBmwM3E36RetailBodyCount = 11u;

struct BmwWheelSpindleBodyTopology {
    std::size_t body_count = kBmwM3E36RetailBodyCount;
    std::array<std::size_t, kVehicleConstraintComponentCount>
        wheel_body_indices{{3u, 4u, 7u, 8u}};
    std::array<std::size_t, kVehicleConstraintComponentCount>
        spindle_body_indices{{1u, 2u, 5u, 6u}};
    bool wheel_spindle_body_indices_ready = true;
    bool rear_axle_body_index_ready = false;
    bool main_chassis_body_selected = true;
    std::size_t main_chassis_body_index = 0u;
    bool update_child_to_vehicle_solver_base_continuity_proven = false;
    bool vehicle_body_selection_ready = false;
};

struct ProvenRearAxleBodyIndex {
    bool proven = false;
    std::size_t body_index = 0u;
};

const BmwWheelSpindleBodyTopology&
bmw_m3_e36_retail_wheel_spindle_body_topology();

VehicleConstraintBodyIdentityMap
complete_bmw_vehicle_constraint_body_identity_map(
    const BmwWheelSpindleBodyTopology& topology,
    const ProvenRearAxleBodyIndex& rear_axle);

}  // namespace shift::runtime::physics
