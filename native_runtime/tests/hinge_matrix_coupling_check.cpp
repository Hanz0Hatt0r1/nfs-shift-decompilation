#include "shift_hinge_matrix_coupling.hpp"

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

        const std::array<float, 9> diagonal = {
            1.0f, 0.0f, 0.0f,
            0.0f, 2.0f, 0.0f,
            0.0f, 0.0f, 3.0f,
        };
        const auto transformed =
            transform_fun_007bb250_hinge_rows(
                diagonal,
                {1.0, 2.0, 3.0},
                {4.0, 5.0, 6.0});
        require_close(
            transformed.angular,
            std::array<double, 3>{1.0, 4.0, 9.0},
            1e-12,
            "HINGE transformed angular",
            max_absolute_error);
        require_close(
            transformed.linear,
            std::array<double, 3>{4.0, 10.0, 18.0},
            1e-12,
            "HINGE transformed linear",
            max_absolute_error);

        const auto self =
            evaluate_fun_007bb250_hinge_self(
                diagonal,
                {1.0, 2.0, 3.0},
                {4.0, 5.0, 6.0});
        require_close(
            self.lower_triangle,
            std::array<double, 3>{36.0, 78.0, 174.0},
            1e-12,
            "HINGE self lower triangle",
            max_absolute_error);

        const std::array<float, 9> identity = {
            1.0f, 0.0f, 0.0f,
            0.0f, 1.0f, 0.0f,
            0.0f, 0.0f, 1.0f,
        };
        const auto pair =
            evaluate_fun_007bb250_hinge_pair(
                identity,
                {1.0, 2.0, 3.0},
                {4.0, 5.0, 6.0},
                {7.0, 8.0, 9.0},
                {10.0, 11.0, 12.0},
                4u,
                2u,
                true);
        require_close(
            pair.raw_coefficients,
            std::array<double, 4>{
                50.0, 68.0, 122.0, 167.0
            },
            1e-12,
            "HINGE pair raw coefficients",
            max_absolute_error);
        require_close(
            pair.block,
            std::array<double, 4>{
                50.0, 68.0,
                122.0, 167.0,
            },
            1e-12,
            "HINGE pair outer orientation",
            max_absolute_error);
        if (pair.orientation !=
                "outer_rows_by_inner_columns" ||
            pair.row_base != 4u ||
            pair.column_base != 2u) {
            throw std::runtime_error(
                "HINGE outer storage orientation mismatch");
        }

        const auto reverse =
            evaluate_fun_007bb250_hinge_pair(
                identity,
                {1.0, 2.0, 3.0},
                {4.0, 5.0, 6.0},
                {7.0, 8.0, 9.0},
                {10.0, 11.0, 12.0},
                2u,
                4u,
                false);
        require_close(
            reverse.block,
            std::array<double, 4>{
                -50.0, -122.0,
                -68.0, -167.0,
            },
            1e-12,
            "HINGE pair reversed orientation",
            max_absolute_error);
        if (reverse.orientation !=
            "inner_rows_by_outer_columns") {
            throw std::runtime_error(
                "HINGE reversed storage orientation mismatch");
        }

        const std::vector<double> zero_matrix(25u, 0.0);
        const auto applied =
            apply_fun_007bb250_hinge_block(
                zero_matrix,
                5u,
                2u,
                1u,
                {1.0, 2.0, 3.0, 4.0});
        require_close(
            applied,
            std::vector<double>{
                0.0, 0.0, 0.0, 0.0, 0.0,
                0.0, 0.0, 0.0, 0.0, 0.0,
                0.0, 1.0, 2.0, 0.0, 0.0,
                0.0, 3.0, 4.0, 0.0, 0.0,
                0.0, 0.0, 0.0, 0.0, 0.0,
            },
            1e-12,
            "HINGE block application",
            max_absolute_error);

        bool range_rejected = false;
        try {
            (void)apply_fun_007bb250_hinge_block(
                zero_matrix,
                5u,
                4u,
                4u,
                {1.0, 2.0, 3.0, 4.0});
        } catch (const std::out_of_range&) {
            range_rejected = true;
        }
        if (!range_rejected) {
            throw std::runtime_error(
                "HINGE out-of-range block was accepted");
        }

        bool non_finite_rejected = false;
        try {
            auto invalid = identity;
            invalid[0] =
                std::numeric_limits<float>::quiet_NaN();
            (void)evaluate_fun_007bb250_hinge_self(
                invalid,
                {1.0, 2.0, 3.0},
                {4.0, 5.0, 6.0});
        } catch (const std::invalid_argument&) {
            non_finite_rejected = true;
        }
        if (!non_finite_rejected) {
            throw std::runtime_error(
                "HINGE non-finite body frame was accepted");
        }

        std::cout
            << "{\n"
            << "  \"format\": "
            << "\"SHIFT.NativeHingeMatrixCouplingCheck/1\",\n"
            << "  \"source_function\": \"FUN_007bb250\",\n"
            << "  \"transform_source_function\": \"FUN_007aefb0\",\n"
            << "  \"source_line\": 819302,\n"
            << "  \"sample_stride\": 160,\n"
            << "  \"self_block_shape\": \"2x2-lower\",\n"
            << "  \"pair_block_shape\": \"2x2\",\n"
            << "  \"lower_triangle_orientation_verified\": true,\n"
            << "  \"block_application_verified\": true,\n"
            << "  \"range_rejected\": true,\n"
            << "  \"non_finite_rejected\": true,\n"
            << "  \"max_absolute_error\": "
            << std::setprecision(17)
            << max_absolute_error << ",\n"
            << "  \"oracle_tolerance\": 1e-12,\n"
            << "  \"oracle_within_tolerance\": true,\n"
            << "  \"hinge_bar_coupling_executed\": false,\n"
            << "  \"full_fun_007bb250_iteration_executed\": false,\n"
            << "  \"status\": \"ok\"\n"
            << "}\n";
        return EXIT_SUCCESS;
    } catch (const std::exception& error) {
        std::cerr
            << "shift_runtime_hinge_matrix_coupling_check: "
            << error.what() << "\n";
        return EXIT_FAILURE;
    }
}
