#include "shift_bmw_chassis_body_selection_gate.hpp"

#include <stdexcept>

namespace shift::runtime::physics {

VehicleBodyIdentitySelection build_bmw_main_chassis_body_identity_selection(
    const BmwWheelSpindleBodyTopology& topology,
    const ProvenUpdateChildVehicleSolverBaseContinuity& continuity) {
    const auto& expected = bmw_m3_e36_retail_wheel_spindle_body_topology();
    if (topology.body_count != expected.body_count ||
        topology.wheel_body_indices != expected.wheel_body_indices ||
        topology.spindle_body_indices != expected.spindle_body_indices ||
        topology.wheel_spindle_body_indices_ready !=
            expected.wheel_spindle_body_indices_ready ||
        topology.rear_axle_body_index_ready !=
            expected.rear_axle_body_index_ready ||
        topology.main_chassis_body_selected !=
            expected.main_chassis_body_selected ||
        topology.main_chassis_body_index != expected.main_chassis_body_index ||
        topology.update_child_to_vehicle_solver_base_continuity_proven !=
            expected.update_child_to_vehicle_solver_base_continuity_proven ||
        topology.vehicle_body_selection_ready !=
            expected.vehicle_body_selection_ready ||
        topology.main_chassis_body_index >= topology.body_count) {
        throw std::invalid_argument(
            "BMW chassis selection gate requires the proven retail BODY topology");
    }
    if (!continuity.proven) {
        throw std::invalid_argument(
            "BMW chassis selection gate requires proven update-child to vehicle solver-base continuity");
    }

    VehicleBodyIdentitySelection selection{};
    selection.selection_proven = true;
    selection.body_index = static_cast<std::uint32_t>(
        topology.main_chassis_body_index);
    return selection;
}

}  // namespace shift::runtime::physics
