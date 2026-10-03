#include "shift_wheel_contact_factor.hpp"

#include <algorithm>
#include <cmath>
#include <iostream>
#include <limits>
#include <stdexcept>

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

        const auto zero = execute_fun_00758ad0_contact_factor(0.0, 0.0);
        require_close(zero.clamped_value, 0.0, 0.0, "zero clamp mismatch", max_error);
        require_close(zero.factor, 1.0, 2e-7, "zero factor mismatch", max_error);

        const auto high = execute_fun_00758ad0_contact_factor(100.0, 0.0);
        require_close(high.clamped_value, 6.0, 0.0, "upper clamp mismatch", max_error);
        require_close(high.factor, 0.95, 2e-6, "upper factor mismatch", max_error);

        const auto midpoint = execute_fun_00758ad0_contact_factor(3.0, 0.0);
        require_close(
            midpoint.angle_radians,
            kWheelContactFactorPiNumerator / 2.0,
            1e-15,
            "midpoint angle mismatch",
            max_error);
        if (std::abs(midpoint.cosine) >= 2e-7) {
            throw std::runtime_error("midpoint cosine mismatch");
        }
        require_close(
            midpoint.factor,
            kWheelContactFactorCosBias,
            2e-7,
            "midpoint factor mismatch",
            max_error);

        const auto shifted = execute_fun_00758ad0_contact_factor(4.0, 2.0);
        require_close(shifted.pre_clamp, 3.0, 0.0, "threshold pre-clamp mismatch", max_error);
        require_close(shifted.clamped_value, 3.0, 0.0, "threshold clamp mismatch", max_error);

        const auto rows = execute_fun_00765c40_four_wheel_factor_storage(
            {0.0, 1.0, 2.0, 3.0},
            0.0,
            true,
            true,
            17.5);
        const double expected_factors[4] = {1.0, 0.9966506, 0.9875, 0.975};
        for (std::size_t wheel = 0; wheel < kWheelContactFactorCount; ++wheel) {
            if (rows[wheel].wheel_index != wheel) {
                throw std::runtime_error("four-wheel source order mismatch");
            }
            require_close(
                rows[wheel].factor,
                expected_factors[wheel],
                2e-6,
                "four-wheel factor mismatch",
                max_error);
            require_close(
                rows[wheel].previous_value,
                17.5,
                0.0,
                "four-wheel previous/reference mismatch",
                max_error);
            if (rows[wheel].wheel_factor_offset !=
                    kWheelContactFactorValueBase + wheel * kWheelContactFactorStride ||
                rows[wheel].previous_value_offset !=
                    kWheelContactPreviousValueBase + wheel * kWheelContactFactorStride) {
                throw std::runtime_error("four-wheel storage offset mismatch");
            }
        }

        const auto disabled = execute_fun_00765c40_four_wheel_factor_storage(
            {1.0, 2.0, 3.0, 4.0},
            2.0,
            false,
            false,
            99.0);
        for (const auto& row : disabled) {
            require_close(row.factor, 1.0, 0.0, "disabled factor mismatch", max_error);
            require_close(row.previous_value, 0.0, 0.0, "disabled previous mismatch", max_error);
        }

        bool non_finite_rejected = false;
        try {
            (void)execute_fun_00758ad0_contact_factor(
                std::numeric_limits<double>::infinity(),
                0.0);
        } catch (const std::invalid_argument&) {
            non_finite_rejected = true;
        }
        if (!non_finite_rejected) {
            throw std::runtime_error("non-finite FUN_00758ad0 input was accepted");
        }

        std::cout
            << "{\"format\":\"SHIFT.NativeWheelContactFactor/1\","
            << "\"ready\":true,"
            << "\"function\":\"FUN_00758ad0\","
            << "\"caller\":\"FUN_00765c40\","
            << "\"threshold_global_offset\":\"0xc10f94\","
            << "\"wheel_count\":4,"
            << "\"wheel_stride\":\"0x150\","
            << "\"previous_base\":\"0xa70\","
            << "\"factor_base\":\"0xa78\","
            << "\"float32_result_rounding_proven\":true,"
            << "\"four_wheel_storage_proven\":true,"
            << "\"disabled_factor_proven\":true,"
            << "\"non_finite_rejected\":true,"
            << "\"max_absolute_error\":" << max_error << "}\n";
        return 0;
    } catch (const std::exception& exc) {
        std::cerr << exc.what() << "\n";
        return 1;
    }
}
