#include "shift_vehicle_driveline_math.hpp"

#include <algorithm>
#include <cmath>
#include <iostream>
#include <stdexcept>
#include <vector>

namespace {

void require_close(
    double actual,
    double expected,
    double tolerance,
    const char* label,
    double& max_error) {

    const double error = std::abs(actual - expected);
    max_error = std::max(max_error, error);
    if (!std::isfinite(actual) || error > tolerance) {
        throw std::runtime_error(label);
    }
}

}  // namespace

int main() {
    using namespace shift::runtime::physics;
    try {
        double max_error = 0.0;

        const std::vector<RpmTorquePoint> points = {
            {1000.0, -30.0, 100.0},
            {2000.0, -10.0, 200.0},
            {3000.0, -20.0, 150.0},
        };
        const auto middle = sample_fun_007becb0_rpm_torque(points, 1500.0);
        require_close(middle.brake, -20.0, 1e-12, "RPMTorque middle brake", max_error);
        require_close(middle.throttle, 150.0, 1e-12, "RPMTorque middle throttle", max_error);
        if (middle.low_index != 0u || middle.high_index != 1u ||
            middle.midpoint_clamped) {
            throw std::runtime_error("RPMTorque middle bracket mismatch");
        }

        const auto below = sample_fun_007becb0_rpm_torque(points, 500.0);
        require_close(below.brake, -40.0, 1e-12, "RPMTorque low extrapolation brake", max_error);
        require_close(below.throttle, 50.0, 1e-12, "RPMTorque low extrapolation throttle", max_error);

        const auto above = sample_fun_007becb0_rpm_torque(points, 3500.0);
        require_close(above.brake, -25.0, 1e-12, "RPMTorque high extrapolation brake", max_error);
        require_close(above.throttle, 125.0, 1e-12, "RPMTorque high extrapolation throttle", max_error);

        const std::vector<RpmTorquePoint> clamp_points = {
            {1000.0, 200.0, 100.0},
            {2000.0, 300.0, 100.0},
        };
        const auto clamped = sample_fun_007becb0_rpm_torque(
            clamp_points, 1500.0);
        require_close(clamped.brake, 175.0, 1e-12, "RPMTorque midpoint brake", max_error);
        require_close(clamped.throttle, 175.0, 1e-12, "RPMTorque midpoint throttle", max_error);
        if (!clamped.midpoint_clamped) {
            throw std::runtime_error("RPMTorque midpoint branch was not taken");
        }

        const auto peak = scan_rpm_torque_peak_power(points);
        if (!peak.has_point || peak.point_index != 1u ||
            peak.rpm != 2000.0 || peak.throttle_torque != 200.0) {
            throw std::runtime_error("RPMTorque peak-power scan mismatch");
        }
        require_close(
            peak.peak,
            2000.0 * 200.0 * 0.73756105 / 5252.0,
            1e-12,
            "RPMTorque peak power",
            max_error);

        const auto solve2 = solve_fun_007af310_dense(
            {{2.0, 1.0}, {1.0, 3.0}},
            {5.0, 7.0});
        if (!solve2.success || solve2.solution.size() != 2u) {
            throw std::runtime_error("FUN_007af310 2x2 solve failed");
        }
        require_close(solve2.solution[0], 1.6, 1e-12, "FUN_007af310 x0", max_error);
        require_close(solve2.solution[1], 1.8, 1e-12, "FUN_007af310 x1", max_error);

        const auto swap = solve_fun_007af310_dense(
            {{0.0, 2.0}, {1.0, 3.0}},
            {4.0, 5.0});
        if (!swap.success || swap.row_swap_count != 1u) {
            throw std::runtime_error("FUN_007af310 row-swap path failed");
        }
        require_close(swap.solution[0], -1.0, 1e-12, "FUN_007af310 swap x0", max_error);
        require_close(swap.solution[1], 2.0, 1e-12, "FUN_007af310 swap x1", max_error);

        const auto solve4 = solve_fun_007af310_dense(
            {
                {1.0, 0.0, 0.0, 0.0},
                {0.0, 2.0, 0.0, 0.0},
                {0.0, 0.0, 4.0, 0.0},
                {0.0, 0.0, 0.0, 8.0},
            },
            {1.0, 4.0, 12.0, 32.0});
        if (!solve4.success || solve4.solution.size() != 4u) {
            throw std::runtime_error("FUN_007af310 4x4 curve solve failed");
        }
        for (std::size_t index = 0; index < 4u; ++index) {
            require_close(
                solve4.solution[index],
                static_cast<double>(index + 1u),
                1e-12,
                "FUN_007af310 4x4 solution",
                max_error);
        }

        const auto solve6 = solve_fun_007af310_dense(
            {
                {1.0, 0.0, 0.0, 0.0, 0.0, 0.0},
                {0.0, 2.0, 0.0, 0.0, 0.0, 0.0},
                {0.0, 0.0, 3.0, 0.0, 0.0, 0.0},
                {0.0, 0.0, 0.0, 4.0, 0.0, 0.0},
                {0.0, 0.0, 0.0, 0.0, 5.0, 0.0},
                {0.0, 0.0, 0.0, 0.0, 0.0, 6.0},
            },
            {1.0, 4.0, 9.0, 16.0, 25.0, 36.0});
        if (!solve6.success || solve6.solution.size() != 6u) {
            throw std::runtime_error("FUN_007af310 6x6 driveline solve failed");
        }
        for (std::size_t index = 0; index < 6u; ++index) {
            require_close(
                solve6.solution[index],
                static_cast<double>(index + 1u),
                1e-12,
                "FUN_007af310 6x6 solution",
                max_error);
        }

        const auto singular = solve_fun_007af310_dense(
            {{1.0, 2.0}, {2.0, 4.0}},
            {3.0, 6.0});
        if (singular.success || !singular.solution.empty()) {
            throw std::runtime_error("FUN_007af310 singular system was accepted");
        }

        bool non_monotonic_rejected = false;
        try {
            (void)sample_fun_007becb0_rpm_torque(
                {{2000.0, 0.0, 1.0}, {1000.0, 0.0, 1.0}},
                1500.0);
        } catch (const std::invalid_argument&) {
            non_monotonic_rejected = true;
        }
        if (!non_monotonic_rejected) {
            throw std::runtime_error("invalid RPMTorque ordering was accepted");
        }

        std::cout
            << "{\"format\":\"SHIFT.NativeVehicleDrivelineMath/1\","
            << "\"ready\":true,"
            << "\"rpm_torque_function\":\"FUN_007becb0\","
            << "\"linear_solver_function\":\"FUN_007af310\","
            << "\"curve_solver_dimension\":4,"
            << "\"driveline_solver_dimension\":6,"
            << "\"row_swap_proven\":true,"
            << "\"singular_rejected\":true,"
            << "\"max_absolute_error\":" << max_error << "}\n";
        return 0;
    } catch (const std::exception& exc) {
        std::cerr << exc.what() << "\n";
        return 1;
    }
}
