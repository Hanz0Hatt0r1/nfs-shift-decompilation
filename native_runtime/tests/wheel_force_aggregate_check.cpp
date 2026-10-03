#include "shift_wheel_force_aggregate.hpp"

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

        const WheelForceAggregateRecord record = {
            2.0,
            {0.0, 1.0, 0.0},
            3.0,
            {1.0, 0.0, 0.0},
            {0.0, 0.0, 2.0},
        };
        const std::array<WheelForceAggregateRecord, 3> records = {
            record,
            record,
            record,
        };
        const ConstraintRefreshFrame3f identity = {
            1.0f, 0.0f, 0.0f,
            0.0f, 1.0f, 0.0f,
            0.0f, 0.0f, 1.0f,
        };
        const auto result =
            execute_fun_00759c90_wheel_force_aggregate(
                records,
                {0.0, 0.0, 1.0},
                identity,
                3.0);

        const double expected_total[3] = {9.0, 6.0, 0.0};
        const double expected_cross[3] = {-6.0, 9.0, 0.0};
        for (std::size_t component = 0; component < 3u; ++component) {
            require_close(
                result.total[component],
                expected_total[component],
                0.0,
                "FUN_00759c90 total vector",
                max_error);
            require_close(
                result.cross_total[component],
                expected_cross[component],
                0.0,
                "FUN_00759c90 cross total",
                max_error);
            require_close(
                result.transformed_total[component],
                expected_total[component],
                0.0,
                "FUN_00759c90 transformed total",
                max_error);
        }
        require_close(
            result.scalar_output,
            3.0,
            0.0,
            "FUN_00759c90 scalar output",
            max_error);

        const ConstraintRefreshFrame3f nontrivial = {
            2.0f, 0.0f, 0.0f,
            0.0f, 3.0f, 0.0f,
            0.0f, 0.0f, 4.0f,
        };
        const auto transformed =
            execute_fun_00759c90_wheel_force_aggregate(
                records,
                {0.0, 0.0, 1.0},
                nontrivial,
                6.0);
        require_close(
            transformed.transformed_total[0],
            18.0,
            0.0,
            "FUN_00759c90 nontrivial transformed X",
            max_error);
        require_close(
            transformed.transformed_total[1],
            18.0,
            0.0,
            "FUN_00759c90 nontrivial transformed Y",
            max_error);
        require_close(
            transformed.scalar_output,
            3.0,
            0.0,
            "FUN_00759c90 nontrivial scalar output",
            max_error);

        bool zero_divisor_rejected = false;
        try {
            (void)execute_fun_00759c90_wheel_force_aggregate(
                records,
                {0.0, 0.0, 0.0},
                identity,
                0.0);
        } catch (const std::invalid_argument&) {
            zero_divisor_rejected = true;
        }
        if (!zero_divisor_rejected) {
            throw std::runtime_error(
                "FUN_00759c90 accepted zero BODY +0x120");
        }

        bool non_finite_rejected = false;
        try {
            auto bad = records;
            bad[0].scalar_at_base = std::numeric_limits<double>::infinity();
            (void)execute_fun_00759c90_wheel_force_aggregate(
                bad,
                {0.0, 0.0, 0.0},
                identity,
                1.0);
        } catch (const std::invalid_argument&) {
            non_finite_rejected = true;
        }
        if (!non_finite_rejected) {
            throw std::runtime_error(
                "FUN_00759c90 accepted non-finite record state");
        }

        std::cout
            << "{\"format\":\"SHIFT.NativeWheelForceAggregate/1\","
            << "\"ready\":true,"
            << "\"function\":\"FUN_00759c90\","
            << "\"record_count\":3,"
            << "\"record_stride\":336,"
            << "\"transform_function\":\"FUN_007af0a0\","
            << "\"body_divisor_offset\":288,"
            << "\"zero_divisor_rejected\":true,"
            << "\"non_finite_rejected\":true,"
            << "\"max_absolute_error\":" << max_error << "}\n";
        return 0;
    } catch (const std::exception& exc) {
        std::cerr << exc.what() << "\n";
        return 1;
    }
}
