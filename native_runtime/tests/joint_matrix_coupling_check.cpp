#include "shift_joint_matrix_coupling.hpp"

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

        const Matrix3d identity = {{
            {{1.0, 0.0, 0.0}},
            {{0.0, 1.0, 0.0}},
            {{0.0, 0.0, 1.0}},
        }};

        const auto terms =
            derive_fun_007bbb80_joint_tensor_terms(
                identity,
                {1.0, 2.0, 3.0});
        require_close(
            std::array<double, 9>{
                terms.d6, terms.d10, terms.d1,
                terms.d2, terms.d3, terms.d12,
                terms.d15, terms.d19, terms.d18,
            },
            std::array<double, 9>{
                0.0, 3.0, -2.0,
                -3.0, 0.0, 1.0,
                2.0, -1.0, 0.0,
            },
            1e-12,
            "JOINT tensor terms",
            max_absolute_error);

        const auto self =
            evaluate_fun_007bbb80_joint_self(
                identity,
                {1.0, 2.0, 3.0},
                2.0);
        require_close(
            self.lower_triangle,
            std::array<double, 6>{
                15.0, -2.0, 12.0,
                -3.0, -6.0, 7.0,
            },
            1e-12,
            "JOINT self block",
            max_absolute_error);

        const auto joint_pair =
            evaluate_fun_007bbb80_joint_joint(
                identity,
                {1.0, 2.0, 3.0},
                {4.0, 5.0, 6.0},
                2.0,
                5u,
                2u,
                true);
        require_close(
            joint_pair.raw_block,
            std::vector<double>{
                30.0, -8.0, -12.0,
                -5.0, 24.0, -15.0,
                -6.0, -12.0, 16.0,
            },
            1e-12,
            "JOINT/JOINT raw block",
            max_absolute_error);
        if (joint_pair.orientation !=
                "outer_rows_by_inner_columns" ||
            joint_pair.row_base != 5u ||
            joint_pair.column_base != 2u) {
            throw std::runtime_error(
                "JOINT/JOINT lower-triangle orientation mismatch");
        }

        const auto joint_pair_reverse =
            evaluate_fun_007bbb80_joint_joint(
                identity,
                {1.0, 2.0, 3.0},
                {4.0, 5.0, 6.0},
                2.0,
                2u,
                5u,
                false);
        require_close(
            joint_pair_reverse.block,
            std::vector<double>{
                -30.0, 5.0, 6.0,
                8.0, -24.0, 12.0,
                12.0, 15.0, -16.0,
            },
            1e-12,
            "JOINT/JOINT reversed block",
            max_absolute_error);
        if (joint_pair_reverse.orientation !=
            "inner_rows_by_outer_columns") {
            throw std::runtime_error(
                "JOINT/JOINT reversed orientation mismatch");
        }

        const auto hinge_pair =
            evaluate_fun_007bbb80_joint_hinge(
                identity,
                {1.0, 2.0, 3.0},
                {4.0, 5.0, 6.0},
                {7.0, 8.0, 9.0},
                5u,
                2u,
                true);
        require_close(
            hinge_pair.block,
            std::vector<double>{
                3.0, 6.0,
                -6.0, -12.0,
                3.0, 6.0,
            },
            1e-12,
            "JOINT/HINGE block",
            max_absolute_error);
        if (hinge_pair.rows != 3u ||
            hinge_pair.columns != 2u ||
            hinge_pair.orientation !=
                "joint_rows_by_hinge_columns") {
            throw std::runtime_error(
                "JOINT/HINGE orientation mismatch");
        }

        const auto hinge_pair_reverse =
            evaluate_fun_007bbb80_joint_hinge(
                identity,
                {1.0, 2.0, 3.0},
                {4.0, 5.0, 6.0},
                {7.0, 8.0, 9.0},
                2u,
                5u,
                false);
        require_close(
            hinge_pair_reverse.block,
            std::vector<double>{
                -3.0, 6.0, -3.0,
                -6.0, 12.0, -6.0,
            },
            1e-12,
            "JOINT/HINGE reversed block",
            max_absolute_error);

        const auto bar_pair =
            evaluate_fun_007bbb80_joint_bar(
                identity,
                {1.0, 2.0, 3.0},
                {4.0, 5.0, 6.0},
                {7.0, 8.0, 9.0},
                2.0,
                5u,
                2u,
                true);
        require_close(
            bar_pair.block,
            std::vector<double>{38.0, 22.0, 6.0},
            1e-12,
            "JOINT/BAR block",
            max_absolute_error);
        if (bar_pair.rows != 3u ||
            bar_pair.columns != 1u ||
            bar_pair.orientation !=
                "joint_rows_by_bar_column") {
            throw std::runtime_error(
                "JOINT/BAR orientation mismatch");
        }

        const auto bar_pair_reverse =
            evaluate_fun_007bbb80_joint_bar(
                identity,
                {1.0, 2.0, 3.0},
                {4.0, 5.0, 6.0},
                {7.0, 8.0, 9.0},
                2.0,
                2u,
                5u,
                false);
        require_close(
            bar_pair_reverse.block,
            std::vector<double>{-38.0, -22.0, -6.0},
            1e-12,
            "JOINT/BAR reversed block",
            max_absolute_error);

        const Matrix3d off_diagonal = {{
            {{2.0, 3.0, 4.0}},
            {{3.0, 5.0, 6.0}},
            {{4.0, 6.0, 7.0}},
        }};
        const auto off_terms =
            derive_fun_007bbb80_joint_tensor_terms(
                off_diagonal,
                {1.0, 2.0, 3.0});
        if (std::abs(off_terms.d15 - 1.0) > 1e-12) {
            throw std::runtime_error(
                "FUN_007bbb80 d15 source offset mismatch");
        }

        const std::vector<double> zero_matrix(25u, 0.0);
        const auto applied = apply_fun_007bbb80_block(
            zero_matrix,
            5u,
            2u,
            1u,
            {1.0, 2.0, 3.0, 4.0},
            2u,
            2u);
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
            "JOINT block application",
            max_absolute_error);

        bool range_rejected = false;
        try {
            (void)apply_fun_007bbb80_block(
                zero_matrix,
                5u,
                4u,
                4u,
                {1.0, 2.0, 3.0, 4.0},
                2u,
                2u);
        } catch (const std::out_of_range&) {
            range_rejected = true;
        }
        if (!range_rejected) {
            throw std::runtime_error(
                "JOINT matrix out-of-range block was accepted");
        }

        bool non_finite_rejected = false;
        try {
            Matrix3d invalid = identity;
            invalid[0][1] =
                std::numeric_limits<double>::quiet_NaN();
            (void)evaluate_fun_007bbb80_joint_self(
                invalid,
                {1.0, 2.0, 3.0},
                2.0);
        } catch (const std::invalid_argument&) {
            non_finite_rejected = true;
        }
        if (!non_finite_rejected) {
            throw std::runtime_error(
                "JOINT matrix non-finite input was accepted");
        }

        std::cout
            << "{\n"
            << "  \"format\": "
            << "\"SHIFT.NativeJointMatrixCouplingCheck/1\",\n"
            << "  \"source_function\": \"FUN_007bbb80\",\n"
            << "  \"source_line\": 819720,\n"
            << "  \"joint_stride\": 64,\n"
            << "  \"self_block_shape\": \"3x3-lower\",\n"
            << "  \"joint_pair_shape\": \"3x3\",\n"
            << "  \"hinge_pair_shape\": \"3x2\",\n"
            << "  \"bar_pair_shape\": \"3x1\",\n"
            << "  \"lower_triangle_orientation_verified\": true,\n"
            << "  \"d15_source_offset_verified\": true,\n"
            << "  \"block_application_verified\": true,\n"
            << "  \"range_rejected\": true,\n"
            << "  \"non_finite_rejected\": true,\n"
            << "  \"max_absolute_error\": "
            << std::setprecision(17)
            << max_absolute_error << ",\n"
            << "  \"oracle_tolerance\": 1e-12,\n"
            << "  \"oracle_within_tolerance\": true,\n"
            << "  \"full_fun_007bbb80_iteration_executed\": false,\n"
            << "  \"status\": \"ok\"\n"
            << "}\n";
        return EXIT_SUCCESS;
    } catch (const std::exception& error) {
        std::cerr
            << "shift_runtime_joint_matrix_coupling_check: "
            << error.what() << "\n";
        return EXIT_FAILURE;
    }
}
