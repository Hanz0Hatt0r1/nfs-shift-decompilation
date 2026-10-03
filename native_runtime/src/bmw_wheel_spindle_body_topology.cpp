#include "shift_bmw_wheel_spindle_body_topology.hpp"

#include <stdexcept>

namespace shift::runtime::physics {
namespace {

constexpr std::array<std::size_t, kVehicleConstraintComponentCount>
    kExpectedWheelBodyIndices{{3u, 4u, 7u, 8u}};
constexpr std::array<std::size_t, kVehicleConstraintComponentCount>
    kExpectedSpindleBodyIndices{{1u, 2u, 5u, 6u}};
constexpr std::size_t kExpectedMainChassisBodyIndex = 0u;

void validate_retail_topology(const BmwWheelSpindleBodyTopology& topology) {
    if (topology.body_count != kBmwM3E36RetailBodyCount ||
        topology.wheel_body_indices != kExpectedWheelBodyIndices ||
        topology.spindle_body_indices != kExpectedSpindleBodyIndices ||
        !topology.wheel_spindle_body_indices_ready ||
        topology.rear_axle_body_index_ready ||
        !topology.main_chassis_body_selected ||
        topology.main_chassis_body_index != kExpectedMainChassisBodyIndex ||
        topology.update_child_to_vehicle_solver_base_continuity_proven ||
        topology.vehicle_body_selection_ready) {
        throw std::invalid_argument(
            "BMW BODY topology no longer matches the proven retail identity frontier");
    }
}

}  // namespace

const BmwWheelSpindleBodyTopology&
bmw_m3_e36_retail_wheel_spindle_body_topology() {
    static const BmwWheelSpindleBodyTopology topology{};
    return topology;
}

VehicleConstraintBodyIdentityMap
complete_bmw_vehicle_constraint_body_identity_map(
    const BmwWheelSpindleBodyTopology& topology,
    const ProvenRearAxleBodyIndex& rear_axle) {
    validate_retail_topology(topology);
    if (!rear_axle.proven) {
        throw std::invalid_argument(
            "BMW vehicle constraint BODY map requires a proven rear-axle BODY index");
    }
    if (rear_axle.body_index >= topology.body_count) {
        throw std::out_of_range(
            "BMW rear-axle BODY index is outside the exact retail SDF domain");
    }

    VehicleConstraintBodyIdentityMap map{};
    map.wheel_body_indices = topology.wheel_body_indices;
    map.spindle_body_indices = topology.spindle_body_indices;
    map.rear_axle_body_index = rear_axle.body_index;
    return map;
}

}  // namespace shift::runtime::physics
