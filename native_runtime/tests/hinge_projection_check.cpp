#include "shift_hinge_projection.hpp"

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

template <std::size_t N>
double max_error(
    const std::array<double, N>& actual,
    const std::array<double, N>& expected) {

    double result = 0.0;
    for (std::size_t index = 0; index < N; ++index) {
        result = std::max(
            result,
            std::abs(actual[index] - expected[index]));
    }
    return result;
}

template <std::size_t N>
void require_close(
    const std::array<double, N>& actual,
    const std::array<double, N>& expected,
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

        HingeProjectionInput zero_flag{};
        zero_flag.body_axis = {0.2, 0.3, 0.4};
        zero_flag.residual_vector = {0.1, 0.2, 0.3};
        zero_flag.sample_angular = {1.1, 1.2, 1.3};
        zero_flag.sample_linear = {2.1, 2.2, 2.3};
        zero_flag.sample_position = {1.5, 2.5, 3.5};
        zero_flag.sample_frame_offset = {0.5, 0.75, 1.0};
        zero_flag.body_frame = {
            1.0f, 0.0f, 0.0f,
            0.0f, 1.0f, 0.0f,
            0.0f, 0.0f, 1.0f,
        };
        zero_flag.linear_scale = 2.0;
        zero_flag.quadratic_scale = 3.0;
        zero_flag.side_flag = 0;

        const auto positive =
            evaluate_fun_007bae40_hinge(zero_flag);
        require_close(
            positive.raw_lanes,
            {2.94, 5.34},
            1e-12,
            "HINGE zero-flag lanes",
            max_absolute_error);
        require_close(
            positive.signed_lanes,
            {2.94, 5.34},
            1e-12,
            "HINGE zero-flag signed lanes",
            max_absolute_error);
        if (positive.frame_correction_applied) {
            throw std::runtime_error(
                "HINGE zero-flag branch transformed sample position");
        }

        HingeProjectionInput nonzero{};
        nonzero.body_axis = {1.0, 0.0, 0.0};
        nonzero.residual_vector = {0.0, 0.0, 0.0};
        nonzero.sample_angular = {1.0, 0.0, 0.0};
        nonzero.sample_linear = {0.0, 1.0, 0.0};
        nonzero.sample_position = {1.0, 2.0, 3.0};
        nonzero.sample_frame_offset = {0.0, 1.0, 0.0};
        nonzero.body_frame = zero_flag.body_frame;
        nonzero.linear_scale = 0.0;
        nonzero.quadratic_scale = 2.0;
        nonzero.side_flag = 3;

        const auto negative =
            evaluate_fun_007bae40_hinge(nonzero);
        if (!negative.frame_correction_applied) {
            throw std::runtime_error(
                "HINGE nonzero branch skipped sample transform");
        }
        require_close(
            negative.transformed_sample_position,
            {1.0, 2.0, 3.0},
            1e-12,
            "HINGE transformed sample position",
            max_absolute_error);
        require_close(
            negative.cross_vector,
            {3.0, 0.0, -1.0},
            1e-12,
            "FUN_007b1320 cross vector",
            max_absolute_error);
        require_close(
            negative.raw_lanes,
            {6.0, 0.0},
            1e-12,
            "HINGE nonzero raw lanes",
            max_absolute_error);
        require_close(
            negative.signed_lanes,
            {-6.0, 0.0},
            1e-12,
            "HINGE nonzero signed lanes",
            max_absolute_error);

        HingeProjectionInput matrix_case = nonzero;
        matrix_case.body_frame = {
            1.0f, 2.0f, 3.0f,
            4.0f, 5.0f, 6.0f,
            7.0f, 8.0f, 9.0f,
        };
        const auto matrix_result =
            evaluate_fun_007bae40_hinge(matrix_case);
        require_close(
            matrix_result.transformed_sample_position,
            {14.0, 32.0, 50.0},
            1e-12,
            "FUN_007aefb0 non-identity transform",
            max_absolute_error);
        require_close(
            matrix_result.cross_vector,
            {50.0, 0.0, -14.0},
            1e-12,
            "FUN_007b1320 non-identity cross",
            max_absolute_error);
        require_close(
            matrix_result.raw_lanes,
            {100.0, 0.0},
            1e-12,
            "HINGE non-identity raw lanes",
            max_absolute_error);
        require_close(
            matrix_result.signed_lanes,
            {-100.0, 0.0},
            1e-12,
            "HINGE non-identity signed lanes",
            max_absolute_error);

        const std::vector<double> base = {
            10.0, 20.0, 30.0, 40.0
        };
        const auto applied =
            apply_fun_007bae40_hinge(
                base,
                1u,
                {1.5, -2.5});
        const std::vector<double> expected = {
            10.0, 21.5, 27.5, 40.0
        };
        for (std::size_t index = 0;
             index < applied.size();
             ++index) {
            const double error =
                std::abs(applied[index] - expected[index]);
            max_absolute_error =
                std::max(max_absolute_error, error);
            if (error > 1e-12) {
                throw std::runtime_error(
                    "HINGE solver-vector write mismatch");
            }
        }

        bool range_rejected = false;
        try {
            (void)apply_fun_007bae40_hinge(
                base,
                3u,
                {1.0, 2.0});
        } catch (const std::out_of_range&) {
            range_rejected = true;
        }
        if (!range_rejected) {
            throw std::runtime_error(
                "HINGE out-of-range scalar base was accepted");
        }

        bool non_finite_rejected = false;
        try {
            HingeProjectionInput invalid = zero_flag;
            invalid.quadratic_scale =
                std::numeric_limits<double>::quiet_NaN();
            (void)evaluate_fun_007bae40_hinge(invalid);
        } catch (const std::invalid_argument&) {
            non_finite_rejected = true;
        }
        if (!non_finite_rejected) {
            throw std::runtime_error(
                "HINGE non-finite input was accepted");
        }

        std::cout
            << "{\n"
            << "  \"format\": "
            << "\"SHIFT.NativeHingeProjectionCheck/1\",\n"
            << "  \"source_function\": \"FUN_007bae40\",\n"
            << "  \"transform_source_function\": \"FUN_007aefb0\",\n"
            << "  \"cross_source_function\": \"FUN_007b1320\",\n"
            << "  \"sample_stride\": 160,\n"
            << "  \"scalar_width\": 2,\n"
            << "  \"cases\": 3,\n"
            << "  \"range_rejected\": true,\n"
            << "  \"non_finite_rejected\": true,\n"
            << "  \"max_absolute_error\": "
            << std::setprecision(17)
            << max_absolute_error << ",\n"
            << "  \"oracle_tolerance\": 1e-12,\n"
            << "  \"oracle_within_tolerance\": true,\n"
            << "  \"full_fun_007bc680_executed\": false,\n"
            << "  \"status\": \"ok\"\n"
            << "}\n";
        return EXIT_SUCCESS;
    } catch (const std::exception& error) {
        std::cerr
            << "shift_runtime_hinge_projection_check: "
            << error.what() << "\n";
        return EXIT_FAILURE;
    }
}
