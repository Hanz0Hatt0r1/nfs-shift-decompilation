#pragma once

#include "shift_bmw_wheel_spindle_body_topology.hpp"
#include "shift_vehicle_body_pose_selection.hpp"

namespace shift::runtime::physics {

inline constexpr const char* kNativeBmwChassisBodySelectionGateFormat =
    "SHIFT.NativeBMWChassisBodySelectionGate/1";

struct ProvenUpdateChildVehicleSolverBaseContinuity {
    bool proven = false;
};

VehicleBodyIdentitySelection build_bmw_main_chassis_body_identity_selection(
    const BmwWheelSpindleBodyTopology& topology,
    const ProvenUpdateChildVehicleSolverBaseContinuity& continuity);

}  // namespace shift::runtime::physics
