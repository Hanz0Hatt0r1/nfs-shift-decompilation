#include "shift_bmw_chassis_body_selection_gate.hpp"

#include <stdexcept>

namespace shift::runtime::physics {

VehicleBodyIdentitySelection build_bmw_main_chassis_body_identity_selection(
    const BmwWheelSpindleBodyTopology& topology,
    const ProvenUpdateChildVehicleSolverBaseContinuity& continuity) {
    if (topology.body_count != kBmwM3E36RetailBodyCount ||
        !topology.wheel_spindle_body_indices_ready ||
        !topology.main_chassis_body_selected ||
        topology.main_chassis_body_index != 0u ||
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
