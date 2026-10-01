#include "shift_bar_matrix_coupling.hpp"

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
        const double error =
            std::abs(actual[index] - expected[index]);
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

        const std::array<float, 9> diagonal = {
            1.0f, 0.0f, 0.0f,
            0.0f, 2.0f, 0.0f,
            0.0f, 0.0f, 3.0f,
        };
        const auto frame =
            evaluate_fun_007bb6c0_cross_frame(
                diagonal,
                {1.0, 2.0, 3.0},
                {4.0, 5.0, 6.0});
        require_close(
            frame.cross,
            std::array<double, 3>{-3.0, 6.0, -3.0},
            1e-12,
            "BAR cross",
            max_absolute_error);
        require_close(
            frame.transformed,
            std::array<double, 3>{-3.0, 12.0, -9.0},
            1e-12,
            "BAR transformed cross",
            max_absolute_error);

        const auto self =
            evaluate_fun_007bb6c0_bar_self(
                diagonal,
                {1.0, 2.0, 3.0},
                {4.0, 5.0, 6.0},
                2.0);
        require_scalar(
            self.coefficient,
            262.0,
            1e-12,
            "BAR self coefficient",
            max_absolute_error);
        require_close(
            self.inverse_scalar_terms,
            std::array<double, 3>{8.0, 10.0, 12.0},
            1e-12,
            "BAR inverse scalar terms",
            max_absolute_error);

        const std::array<float, 9> identity = {
            1.0f, 0.0f, 0.0f,
            0.0f, 1.0f, 0.0f,
            0.0f, 0.0f, 1.0f,
        };
        const auto positive =
            evaluate_fun_007bb6c0_bar_pair(
                identity,
                {1.0, 2.0, 3.0},
                {4.0, 5.0, 6.0},
                {7.0, 8.0, 9.0},
                {10.0, 11.0, 12.0},
                2.0,
                5u,
                3u,
                true);
        require_scalar(
            positive.raw_coefficient,
            388.0,
            1e-12,
            "BAR pair raw coefficient",
            max_absolute_error);
        require_scalar(
            positive.coefficient,
            388.0,
            1e-12,
            "BAR pair positive coefficient",
            max_absolute_error);
        if (positive.row != 5u ||
            positive.column != 3u) {
            throw std::runtime_error(
                "BAR pair lower-triangle cell mismatch");
        }

        const auto negative =
            evaluate_fun_007bb6c0_bar_pair(
                identity,
                {1.0, 2.0, 3.0},
                {4.0, 5.0, 6.0},
                {7.0, 8.0, 9.0},
                {10.0, 11.0, 12.0},
                2.0,
                3u,
                5u,
                false);
        require_scalar(
            negative.coefficient,
            -388.0,
            1e-12,
            "BAR pair negative coefficient",
            max_absolute_error);
        if (negative.row != 5u ||
            negative.column != 3u) {
            throw std::runtime_error(
                "BAR pair reversed lower-triangle cell mismatch");
        }

        const std::vector<double> zero_matrix(9u, 0.0);
        const auto applied =
            apply_fun_007bb6c0_bar_scalar(
                zero_matrix,
                3u,
                2u,
                1u,
                3.5);
        require_close(
            applied,
            std::vector<double>{
                0.0, 0.0, 0.0,
                0.0, 0.0, 0.0,
                0.0, 3.5, 0.0,
            },
            1e-12,
            "BAR scalar application",
            max_absolute_error);

        bool range_rejected = false;
        try {
            (void)apply_fun_007bb6c0_bar_scalar(
                zero_matrix,
                3u,
                3u,
                0u,
                1.0);
        } catch (const std::out_of_range&) {
            range_rejected = true;
        }
        if (!range_rejected) {
            throw std::runtime_error(
                "BAR out-of-range matrix cell was accepted");
        }

        bool non_finite_rejected = false;
        try {
            auto invalid = identity;
            invalid[0] =
                std::numeric_limits<float>::quiet_NaN();
            (void)evaluate_fun_007bb6c0_bar_self(
                invalid,
                {1.0, 2.0, 3.0},
                {4.0, 5.0, 6.0},
                2.0);
        } catch (const std::invalid_argument&) {
            non_finite_rejected = true;
        }
        if (!non_finite_rejected) {
            throw std::runtime_error(
                "BAR non-finite body frame was accepted");
        }

        std::cout
            << "{\n"
            << "  \"format\": "
            << "\"SHIFT.NativeBarMatrixCouplingCheck/1\",\n"
            << "  \"source_function\": \"FUN_007bb6c0\",\n"
            << "  \"transform_source_function\": \"FUN_007aefb0\",\n"
            << "  \"source_line\": 819471,\n"
            << "  \"sample_stride\": 96,\n"
            << "  \"self_coefficient_verified\": true,\n"
            << "  \"pair_coefficient_verified\": true,\n"
            << "  \"lower_triangle_cell_verified\": true,\n"
            << "  \"scalar_application_verified\": true,\n"
            << "  \"range_rejected\": true,\n"
            << "  \"non_finite_rejected\": true,\n"
            << "  \"max_absolute_error\": "
            << std::setprecision(17)
            << max_absolute_error << ",\n"
            << "  \"oracle_tolerance\": 1e-12,\n"
            << "  \"oracle_within_tolerance\": true,\n"
            << "  \"full_fun_007bb6c0_iteration_executed\": false,\n"
            << "  \"status\": \"ok\"\n"
            << "}\n";
        return EXIT_SUCCESS;
    } catch (const std::exception& error) {
        std::cerr
            << "shift_runtime_bar_matrix_coupling_check: "
            << error.what() << "\n";
        return EXIT_FAILURE;
    }
}
