#include "shift_bar_projection.hpp"

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

void require_scalar(
    double actual,
    double expected,
    double tolerance,
    const char* label,
    double& observed_max) {

    const double error = std::abs(actual - expected);
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

        BarProjectionInput input{};
        input.body_position = {1.0, 2.0, 3.0};
        input.body_axis = {0.2, 0.3, 0.4};
        input.body_correction = {0.5, 0.6, 0.7};
        input.sample_position = {1.5, 2.5, 3.5};
        input.sample_weight = {1.1, 1.2, 1.3};
        input.residual_vector = {0.1, 0.2, 0.3};
        input.scaled_linear = {0.4, 0.5, 0.6};
        input.linear_scale = 2.0;
        input.quadratic_scale = 3.0;
        input.side_bias = 0.75;
        input.side_flag = 0;

        const auto positive = evaluate_fun_007bb090_bar(input);
        require_close(
            positive.cross_terms,
            std::array<double, 3>{0.05, -0.10, 0.05},
            1e-12,
            "BAR cross terms",
            max_absolute_error);
        require_close(
            positive.basis,
            std::array<double, 3>{9.005, 15.11, 21.515},
            1e-12,
            "BAR basis",
            max_absolute_error);
        require_scalar(
            positive.raw_lane,
            56.007,
            1e-12,
            "BAR raw lane",
            max_absolute_error);
        require_scalar(
            positive.signed_lane,
            56.007,
            1e-12,
            "BAR positive lane",
            max_absolute_error);

        input.side_flag = 9;
        const auto negative = evaluate_fun_007bb090_bar(input);
        require_scalar(
            negative.side_correction,
            2.25,
            1e-12,
            "BAR side correction",
            max_absolute_error);
        require_scalar(
            negative.signed_lane,
            -53.757,
            1e-12,
            "BAR nonzero-side lane",
            max_absolute_error);

        const std::vector<double> base = {
            10.0, 20.0, 30.0, 40.0
        };
        const auto applied = apply_fun_007bb090_bar(
            base,
            2u,
            -3.5);
        require_close(
            applied,
            std::vector<double>{10.0, 20.0, 26.5, 40.0},
            1e-12,
            "BAR solver-vector write",
            max_absolute_error);

        bool range_rejected = false;
        try {
            (void)apply_fun_007bb090_bar(
                base,
                base.size(),
                1.0);
        } catch (const std::out_of_range&) {
            range_rejected = true;
        }
        if (!range_rejected) {
            throw std::runtime_error(
                "BAR out-of-range scalar base was accepted");
        }

        bool non_finite_rejected = false;
        try {
            BarProjectionInput invalid = input;
            invalid.side_bias =
                std::numeric_limits<double>::quiet_NaN();
            (void)evaluate_fun_007bb090_bar(invalid);
        } catch (const std::invalid_argument&) {
            non_finite_rejected = true;
        }
        if (!non_finite_rejected) {
            throw std::runtime_error(
                "BAR non-finite input was accepted");
        }

        std::cout
            << "{\n"
            << "  \"format\": \"SHIFT.NativeBarProjectionCheck/1\",\n"
            << "  \"source_function\": \"FUN_007bb090\",\n"
            << "  \"sample_stride\": 96,\n"
            << "  \"scalar_width\": 1,\n"
            << "  \"side_bias_offset\": \"+0x38\",\n"
            << "  \"cases\": 2,\n"
            << "  \"solver_vector_application_verified\": true,\n"
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
            << "shift_runtime_bar_projection_check: "
            << error.what() << "\n";
        return EXIT_FAILURE;
    }
}
