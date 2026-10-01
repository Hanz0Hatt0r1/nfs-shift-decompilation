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
#include <string>
#include <vector>

namespace {

template <typename Actual, typename Expected>
void require_close(
    const Actual& actual,
    const Expected& expected,
    double tolerance,
    const char* label,
    double& observed_max) {

    if (actual.size() != expected.size()) {
        throw std::runtime_error(
            std::string(label) + " cardinality mismatch");
    }
    for (std::size_t index = 0; index < actual.size(); ++index) {
        const double error = std::abs(actual[index] - expected[index]);
        observed_max = std::max(observed_max, error);
        if (error > tolerance) {
            throw std::runtime_error(
                std::string(label) + " mismatch");
        }
    }
}

}  // namespace

int main() {
    try {
        using namespace shift::runtime::physics;
        double max_absolute_error = 0.0;

        HingeProjectionInput zero_side{};
        zero_side.body_axis = {0.2, 0.3, 0.4};
        zero_side.residual_vector = {0.1, 0.2, 0.3};
        zero_side.sample_angular = {1.1, 1.2, 1.3};
        zero_side.sample_linear = {2.1, 2.2, 2.3};
        zero_side.sample_position = {1.5, 2.5, 3.5};
        zero_side.sample_frame_offset = {0.5, 0.75, 1.0};
        zero_side.linear_scale = 2.0;
        zero_side.quadratic_scale = 3.0;
        zero_side.side_flag = 0;

        const auto first = evaluate_fun_007bae40_hinge(zero_side);
        require_close(
            first.raw_lanes,
            std::array<double, 2>{2.94, 5.34},
            1e-12,
            "HINGE zero-side raw lanes",
            max_absolute_error);
        require_close(
            first.signed_lanes,
            std::array<double, 2>{2.94, 5.34},
            1e-12,
            "HINGE zero-side signed lanes",
            max_absolute_error);
        if (first.transformed_sample_position.has_value() ||
            first.cross_vector.has_value()) {
            throw std::runtime_error(
                "zero-side HINGE unexpectedly used body frame");
        }

        HingeProjectionInput identity{};
        identity.body_axis = {1.0, 0.0, 0.0};
        identity.sample_angular = {1.0, 0.0, 0.0};
        identity.sample_linear = {0.0, 1.0, 0.0};
        identity.sample_position = {1.0, 2.0, 3.0};
        identity.sample_frame_offset = {0.0, 1.0, 0.0};
        identity.body_frame = std::array<float, 9>{
            1.0f, 0.0f, 0.0f,
            0.0f, 1.0f, 0.0f,
            0.0f, 0.0f, 1.0f,
        };
        identity.quadratic_scale = 2.0;
        identity.side_flag = 3;

        const auto second = evaluate_fun_007bae40_hinge(identity);
        require_close(
            *second.transformed_sample_position,
            std::array<double, 3>{1.0, 2.0, 3.0},
            1e-12,
            "HINGE identity transform",
            max_absolute_error);
        require_close(
            *second.cross_vector,
            std::array<double, 3>{3.0, 0.0, -1.0},
            1e-12,
            "HINGE identity cross vector",
            max_absolute_error);
        require_close(
            second.raw_lanes,
            std::array<double, 2>{6.0, 0.0},
            1e-12,
            "HINGE nonzero-side raw lanes",
            max_absolute_error);
        require_close(
            second.signed_lanes,
            std::array<double, 2>{-6.0, 0.0},
            1e-12,
            "HINGE nonzero-side signed lanes",
            max_absolute_error);

        HingeProjectionInput matrix_case{};
        matrix_case.sample_angular = {1.0, 1.0, 0.0};
        matrix_case.sample_linear = {0.0, 0.0, 1.0};
        matrix_case.sample_position = {1.0, 2.0, 3.0};
        matrix_case.sample_frame_offset = {1.0, 0.0, 0.0};
        matrix_case.body_frame = std::array<float, 9>{
            1.0f, 2.0f, 3.0f,
            4.0f, 5.0f, 6.0f,
            7.0f, 8.0f, 9.0f,
        };
        matrix_case.quadratic_scale = 2.0;
        matrix_case.side_flag = 1;

        const auto third = evaluate_fun_007bae40_hinge(matrix_case);
        require_close(
            *third.transformed_sample_position,
            std::array<double, 3>{14.0, 32.0, 50.0},
            1e-12,
            "HINGE FUN_007aefb0 transform",
            max_absolute_error);
        require_close(
            *third.cross_vector,
            std::array<double, 3>{0.0, -50.0, 32.0},
            1e-12,
            "HINGE FUN_007b1320 cross vector",
            max_absolute_error);
        require_close(
            third.signed_lanes,
            std::array<double, 2>{100.0, -64.0},
            1e-12,
            "HINGE transformed signed lanes",
            max_absolute_error);

        const std::vector<double> base = {
            10.0, 20.0, 30.0, 40.0
        };
        const auto applied = apply_fun_007bae40_hinge(
            base,
            1u,
            {1.5, 2.5});
        require_close(
            applied,
            std::vector<double>{10.0, 21.5, 32.5, 40.0},
            1e-12,
            "HINGE solver-vector write",
            max_absolute_error);

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

        bool missing_frame_rejected = false;
        try {
            HingeProjectionInput invalid = identity;
            invalid.body_frame.reset();
            (void)evaluate_fun_007bae40_hinge(invalid);
        } catch (const std::invalid_argument&) {
            missing_frame_rejected = true;
        }
        if (!missing_frame_rejected) {
            throw std::runtime_error(
                "nonzero-side HINGE without body frame was accepted");
        }

        bool non_finite_rejected = false;
        try {
            HingeProjectionInput invalid = zero_side;
            invalid.sample_linear[1] =
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
            << "  \"format\": \"SHIFT.NativeHingeProjectionCheck/1\",\n"
            << "  \"source_function\": \"FUN_007bae40\",\n"
            << "  \"transform_source_function\": \"FUN_007aefb0\",\n"
            << "  \"cross_source_function\": \"FUN_007b1320\",\n"
            << "  \"sample_stride\": 160,\n"
            << "  \"scalar_width\": 2,\n"
            << "  \"cases\": 3,\n"
            << "  \"solver_vector_application_verified\": true,\n"
            << "  \"range_rejected\": true,\n"
            << "  \"missing_frame_rejected\": true,\n"
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
