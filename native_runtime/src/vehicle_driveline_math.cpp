#include "shift_vehicle_driveline_math.hpp"

#include <cmath>
#include <stdexcept>
#include <string>
#include <utility>

namespace shift::runtime::physics {
namespace {

constexpr double kRpmPowerScale = 0.73756105;
constexpr double kRpmPowerDivisor = 5252.0;

void require_finite(double value, const char* label) {
    if (!std::isfinite(value)) {
        throw std::invalid_argument(
            std::string(label) + " contains non-finite value");
    }
}

void require_valid_rpm_curve(const std::vector<RpmTorquePoint>& points) {
    for (std::size_t index = 0; index < points.size(); ++index) {
        const auto& point = points[index];
        require_finite(point.rpm, "RPMTorque RPM");
        require_finite(point.brake, "RPMTorque brake");
        require_finite(point.throttle, "RPMTorque throttle");
        if (index > 0 && point.rpm <= points[index - 1].rpm) {
            throw std::invalid_argument(
                "RPMTorque points must have strictly increasing RPM");
        }
    }
}

}  // namespace

RpmTorqueSample sample_fun_007becb0_rpm_torque(
    const std::vector<RpmTorquePoint>& points,
    double rpm) {

    require_finite(rpm, "RPMTorque sample RPM");
    require_valid_rpm_curve(points);

    RpmTorqueSample result{};
    if (points.empty()) {
        return result;
    }
    if (points.size() == 1u) {
        result.brake = points[0].brake;
        result.throttle = points[0].throttle;
        return result;
    }

    std::size_t upper = 1u;
    while (upper < points.size() &&
           rpm >= points[upper].rpm) {
        ++upper;
    }

    if (upper <= 1u) {
        result.low_index = 0u;
        result.high_index = 1u;
    } else if (upper < points.size()) {
        result.low_index = upper - 1u;
        result.high_index = upper;
    } else {
        result.low_index = points.size() - 2u;
        result.high_index = points.size() - 1u;
    }

    const auto& low = points[result.low_index];
    const auto& high = points[result.high_index];
    const double denominator = high.rpm - low.rpm;
    result.interpolation = (rpm - low.rpm) / denominator;
    result.brake =
        (high.brake - low.brake) * result.interpolation + low.brake;
    result.throttle =
        (high.throttle - low.throttle) * result.interpolation + low.throttle;

    if (result.brake > result.throttle) {
        const double midpoint =
            (result.brake + result.throttle) * 0.5;
        result.brake = midpoint;
        result.throttle = midpoint;
        result.midpoint_clamped = true;
    }

    require_finite(result.brake, "RPMTorque sampled brake");
    require_finite(result.throttle, "RPMTorque sampled throttle");
    require_finite(result.interpolation, "RPMTorque interpolation");
    return result;
}

RpmTorquePeakPower scan_rpm_torque_peak_power(
    const std::vector<RpmTorquePoint>& points) {

    require_valid_rpm_curve(points);
    RpmTorquePeakPower result{};
    for (std::size_t index = 0; index < points.size(); ++index) {
        const auto& point = points[index];
        const double value =
            point.rpm * point.throttle *
            kRpmPowerScale / kRpmPowerDivisor;
        require_finite(value, "RPMTorque peak-power candidate");
        if (result.peak < value) {
            result.peak = value;
            result.point_index = index;
            result.has_point = true;
            result.rpm = point.rpm;
            result.throttle_torque = point.throttle;
        }
    }
    return result;
}

DenseLinearSolveResult solve_fun_007af310_dense(
    const std::vector<std::vector<double>>& matrix,
    const std::vector<double>& rhs) {

    const std::size_t n = matrix.size();
    if (n == 0u || rhs.size() != n) {
        throw std::invalid_argument(
            "FUN_007af310 matrix/RHS cardinality mismatch");
    }
    if (n > 4096u) {
        throw std::invalid_argument(
            "FUN_007af310 dimension is out of native safety range");
    }

    DenseLinearSolveResult result{};
    result.reduced_matrix = matrix;
    result.reduced_rhs = rhs;

    for (std::size_t row = 0; row < n; ++row) {
        if (result.reduced_matrix[row].size() != n) {
            throw std::invalid_argument(
                "FUN_007af310 matrix must be square");
        }
        require_finite(result.reduced_rhs[row], "FUN_007af310 RHS");
        for (double value : result.reduced_matrix[row]) {
            require_finite(value, "FUN_007af310 matrix");
        }
    }

    for (std::size_t pivot = 0; pivot < n; ++pivot) {
        std::size_t pivot_row = pivot;
        while (pivot_row < n &&
               result.reduced_matrix[pivot_row][pivot] == 0.0) {
            ++pivot_row;
        }
        if (pivot_row == n) {
            result.solution.clear();
            result.success = false;
            return result;
        }
        if (pivot_row != pivot) {
            std::swap(
                result.reduced_matrix[pivot_row],
                result.reduced_matrix[pivot]);
            std::swap(
                result.reduced_rhs[pivot_row],
                result.reduced_rhs[pivot]);
            ++result.row_swap_count;
        }

        const double divisor =
            result.reduced_matrix[pivot][pivot];
        if (divisor == 0.0 || !std::isfinite(divisor)) {
            result.solution.clear();
            result.success = false;
            return result;
        }

        for (std::size_t column = pivot; column < n; ++column) {
            result.reduced_matrix[pivot][column] /= divisor;
        }
        result.reduced_rhs[pivot] /= divisor;

        for (std::size_t row = 0; row < n; ++row) {
            if (row == pivot) {
                continue;
            }
            const double scale =
                result.reduced_matrix[row][pivot];
            if (scale == 0.0) {
                continue;
            }
            for (std::size_t column = pivot; column < n; ++column) {
                result.reduced_matrix[row][column] -=
                    scale * result.reduced_matrix[pivot][column];
            }
            result.reduced_rhs[row] -=
                scale * result.reduced_rhs[pivot];
        }
    }

    for (std::size_t row = 0; row < n; ++row) {
        require_finite(
            result.reduced_rhs[row],
            "FUN_007af310 solved RHS");
        for (double value : result.reduced_matrix[row]) {
            require_finite(value, "FUN_007af310 reduced matrix");
        }
    }

    result.solution = result.reduced_rhs;
    result.success = true;
    return result;
}

}  // namespace shift::runtime::physics
