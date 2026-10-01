#include "shift_joint_projection.hpp"

#include <algorithm>
#include <array>
#include <cmath>
#include <cstdlib>
#include <exception>
#include <iomanip>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <vector>

namespace {

double max_error(
    const std::array<double, 3>& actual,
    const std::array<double, 3>& expected) {

    double result = 0.0;
    for (std::size_t index = 0; index < actual.size(); ++index) {
        result = std::max(
            result,
            std::abs(actual[index] - expected[index]));
    }
    return result;
}

void require_close(
    const std::array<double, 3>& actual,
    const std::array<double, 3>& expected,
    double tolerance,
    const char* label,
    double& observed_max) {

    const double error = max_error(actual, expected);
    observed_max = std::max(observed_max, error);
    if (error > tolerance) {
        throw std::runtime_error(
            std::string(label) + " mismatch");
    }
}

}  // namespace

int main() {
    try {
        using namespace shift::runtime::physics;
        double max_absolute_error = 0.0;

        const auto scales = derive_sdf_constraint_scales(10);
        if (scales.linear_scale != 16.0 ||
            scales.quadratic_scale != 64.0) {
            throw std::runtime_error(
                "FUN_0070fe90 constraint scales mismatch");
        }

        JointProjectionInput input{};
        input.body_position = {1.0, 2.0, 3.0};
        input.body_axis = {0.2, 0.3, 0.4};
        input.body_correction = {0.5, 0.6, 0.7};
        input.sample_position = {1.5, 2.5, 3.5};
        input.residual_vector = {0.1, 0.2, 0.3};
        input.scaled_linear = {0.4, 0.5, 0.6};
        input.linear_scale = 2.0;
        input.quadratic_scale = 3.0;
        input.side_flag = 0;

        const auto positive =
            evaluate_fun_007bac60_joint(input);
        require_close(
            positive.cross_terms,
            {-0.05, -0.15, -0.05},
            1e-12,
            "JOINT cross terms",
            max_absolute_error);
        require_close(
            positive.raw_lanes,
            {4.95, 17.95, 21.35},
            1e-12,
            "JOINT raw lanes",
            max_absolute_error);
        require_close(
            positive.signed_lanes,
            {4.95, 17.95, 21.35},
            1e-12,
            "JOINT positive lanes",
            max_absolute_error);

        input.side_flag = 7;
        const auto negative =
            evaluate_fun_007bac60_joint(input);
        require_close(
            negative.signed_lanes,
            {-4.95, -17.95, -21.35},
            1e-12,
            "JOINT negative lanes",
            max_absolute_error);

        const std::vector<double> base = {
            10.0, 20.0, 30.0, 40.0, 50.0
        };
        const auto applied =
            apply_fun_007bac60_joint(
                base,
                1u,
                {1.5, 2.5, 3.5});
        const std::vector<double> expected = {
            10.0, 21.5, 32.5, 43.5, 50.0
        };
        for (std::size_t index = 0;
             index < applied.size();
             ++index) {
            max_absolute_error = std::max(
                max_absolute_error,
                std::abs(applied[index] - expected[index]));
            if (std::abs(applied[index] - expected[index]) > 1e-12) {
                throw std::runtime_error(
                    "JOINT solver-vector write mismatch");
            }
        }

        bool range_rejected = false;
        try {
            (void)apply_fun_007bac60_joint(
                base,
                4u,
                {1.0, 2.0, 3.0});
        } catch (const std::out_of_range&) {
            range_rejected = true;
        }
        if (!range_rejected) {
            throw std::runtime_error(
                "JOINT out-of-range scalar base was accepted");
        }

        bool non_finite_rejected = false;
        try {
            JointProjectionInput invalid = input;
            invalid.linear_scale =
                std::numeric_limits<double>::quiet_NaN();
            (void)evaluate_fun_007bac60_joint(invalid);
        } catch (const std::invalid_argument&) {
            non_finite_rejected = true;
        }
        if (!non_finite_rejected) {
            throw std::runtime_error(
                "JOINT non-finite input was accepted");
        }

        std::cout
            << "{\n"
            << "  \"format\": "
            << "\"SHIFT.NativeJointProjectionCheck/1\",\n"
            << "  \"source_function\": \"FUN_007bac60\",\n"
            << "  \"scale_source_function\": \"FUN_0070fe90\",\n"
            << "  \"sample_stride\": 64,\n"
            << "  \"scalar_width\": 3,\n"
            << "  \"cases\": 3,\n"
            << "  \"range_rejected\": true,\n"
            << "  \"non_finite_rejected\": true,\n"
            << "  \"max_absolute_error\": "
            << std::setprecision(17)
            << max_absolute_error << ",\n"
            << "  \"full_fun_007bc680_executed\": false,\n"
            << "  \"status\": \"ok\"\n"
            << "}\n";
        return EXIT_SUCCESS;
    } catch (const std::exception& error) {
        std::cerr
            << "shift_runtime_joint_projection_check: "
            << error.what() << "\n";
        return EXIT_FAILURE;
    }
}
