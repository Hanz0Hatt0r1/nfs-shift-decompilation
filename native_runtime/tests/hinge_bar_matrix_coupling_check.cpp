#include "shift_hinge_bar_matrix_coupling.hpp"

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

}  // namespace

int main() {
    try {
        using namespace shift::runtime::physics;
        double max_absolute_error = 0.0;

        const std::array<float, 9> identity = {
            1.0f, 0.0f, 0.0f,
            0.0f, 1.0f, 0.0f,
            0.0f, 0.0f, 1.0f,
        };

        const auto forward =
            evaluate_fun_007bb250_hinge_bar(
                identity,
                {2.0, 3.0, 4.0},
                {5.0, 6.0, 7.0},
                {1.0, 0.0, 2.0},
                {3.0, 4.0, 5.0},
                6u,
                2u,
                true);
        require_close(
            forward.raw_coefficients,
            std::array<double, 2>{3.0, -6.0},
            1e-12,
            "HINGE/BAR raw coefficients",
            max_absolute_error);
        require_close(
            forward.block,
            std::vector<double>{3.0, -6.0},
            1e-12,
            "HINGE/BAR forward block",
            max_absolute_error);
        if (forward.rows != 2u ||
            forward.columns != 1u ||
            forward.row_base != 6u ||
            forward.column_base != 2u ||
            forward.orientation !=
                "hinge_rows_by_bar_column") {
            throw std::runtime_error(
                "HINGE/BAR forward orientation mismatch");
        }

        const auto reverse =
            evaluate_fun_007bb250_hinge_bar(
                identity,
                {2.0, 3.0, 4.0},
                {5.0, 6.0, 7.0},
                {1.0, 0.0, 2.0},
                {3.0, 4.0, 5.0},
                2u,
                6u,
                false);
        require_close(
            reverse.block,
            std::vector<double>{-3.0, 6.0},
            1e-12,
            "HINGE/BAR reverse block",
            max_absolute_error);
        if (reverse.rows != 1u ||
            reverse.columns != 2u ||
            reverse.row_base != 6u ||
            reverse.column_base != 2u ||
            reverse.orientation !=
                "bar_row_by_hinge_columns") {
            throw std::runtime_error(
                "HINGE/BAR reverse orientation mismatch");
        }

        const std::vector<double> zero_matrix(25u, 0.0);
        const auto applied_forward =
            apply_fun_007bb250_hinge_bar_block(
                zero_matrix,
                5u,
                2u,
                1u,
                {2.0, -3.0},
                2u,
                1u);
        require_close(
            applied_forward,
            std::vector<double>{
                0.0, 0.0, 0.0, 0.0, 0.0,
                0.0, 0.0, 0.0, 0.0, 0.0,
                0.0, 2.0, 0.0, 0.0, 0.0,
                0.0, -3.0, 0.0, 0.0, 0.0,
                0.0, 0.0, 0.0, 0.0, 0.0,
            },
            1e-12,
            "HINGE/BAR block application",
            max_absolute_error);

        bool range_rejected = false;
        try {
            (void)apply_fun_007bb250_hinge_bar_block(
                zero_matrix,
                5u,
                4u,
                4u,
                {1.0, 2.0},
                2u,
                1u);
        } catch (const std::out_of_range&) {
            range_rejected = true;
        }
        if (!range_rejected) {
            throw std::runtime_error(
                "HINGE/BAR out-of-range block was accepted");
        }

        bool non_finite_rejected = false;
        try {
            auto invalid = identity;
            invalid[0] =
                std::numeric_limits<float>::quiet_NaN();
            (void)evaluate_fun_007bb250_hinge_bar(
                invalid,
                {2.0, 3.0, 4.0},
                {5.0, 6.0, 7.0},
                {1.0, 0.0, 2.0},
                {3.0, 4.0, 5.0},
                6u,
                2u,
                true);
        } catch (const std::invalid_argument&) {
            non_finite_rejected = true;
        }
        if (!non_finite_rejected) {
            throw std::runtime_error(
                "HINGE/BAR non-finite frame was accepted");
        }

        std::cout
            << "{\n"
            << "  \"format\": "
            << "\"SHIFT.NativeHingeBarMatrixCouplingCheck/1\",\n"
            << "  \"source_function\": \"FUN_007bb250\",\n"
            << "  \"transform_source_function\": \"FUN_007aefb0\",\n"
            << "  \"source_line\": 819302,\n"
            << "  \"hinge_stride\": 160,\n"
            << "  \"bar_stride\": 96,\n"
            << "  \"block_shape\": \"2x1\",\n"
            << "  \"lower_triangle_orientation_verified\": true,\n"
            << "  \"block_application_verified\": true,\n"
            << "  \"range_rejected\": true,\n"
            << "  \"non_finite_rejected\": true,\n"
            << "  \"max_absolute_error\": "
            << std::setprecision(17)
            << max_absolute_error << ",\n"
            << "  \"oracle_tolerance\": 1e-12,\n"
            << "  \"oracle_within_tolerance\": true,\n"
            << "  \"full_fun_007bb250_iteration_executed\": false,\n"
            << "  \"status\": \"ok\"\n"
            << "}\n";
        return EXIT_SUCCESS;
    } catch (const std::exception& error) {
        std::cerr
            << "shift_runtime_hinge_bar_matrix_coupling_check: "
            << error.what() << "\n";
        return EXIT_FAILURE;
    }
}
