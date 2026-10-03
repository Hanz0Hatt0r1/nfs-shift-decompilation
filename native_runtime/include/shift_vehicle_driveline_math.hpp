#pragma once

#include <cstddef>
#include <vector>

namespace shift::runtime::physics {

inline constexpr const char* kNativeVehicleDrivelineMathFormat =
    "SHIFT.NativeVehicleDrivelineMath/1";
inline constexpr const char* kRpmTorqueSourceFunction = "FUN_007becb0";
inline constexpr const char* kDrivelineLinearSolverSourceFunction = "FUN_007af310";

struct RpmTorquePoint {
    double rpm = 0.0;
    double brake = 0.0;
    double throttle = 0.0;
};

struct RpmTorqueSample {
    double brake = 0.0;
    double throttle = 0.0;
    std::size_t low_index = 0;
    std::size_t high_index = 0;
    double interpolation = 0.0;
    bool midpoint_clamped = false;
};

struct RpmTorquePeakPower {
    double peak = 1.0;
    std::size_t point_index = 0;
    bool has_point = false;
    double rpm = 0.0;
    double throttle_torque = 0.0;
};

RpmTorqueSample sample_fun_007becb0_rpm_torque(
    const std::vector<RpmTorquePoint>& points,
    double rpm);

RpmTorquePeakPower scan_rpm_torque_peak_power(
    const std::vector<RpmTorquePoint>& points);

struct DenseLinearSolveResult {
    bool success = false;
    std::vector<std::vector<double>> reduced_matrix;
    std::vector<double> reduced_rhs;
    std::vector<double> solution;
    std::size_t row_swap_count = 0;
};

DenseLinearSolveResult solve_fun_007af310_dense(
    const std::vector<std::vector<double>>& matrix,
    const std::vector<double>& rhs);

}  // namespace shift::runtime::physics
