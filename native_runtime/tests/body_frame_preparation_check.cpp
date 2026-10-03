#include "shift_body_frame_preparation.hpp"

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

        const auto coefficients =
            initialize_fun_007ba860_body_coefficients({2.0, 4.0, 8.0});
        require_close(
            coefficients.stored_coefficients[0], 2.0, 0.0,
            "FUN_007ba860 stored coefficient 0", max_error);
        require_close(
            coefficients.stored_coefficients[1], 4.0, 0.0,
            "FUN_007ba860 stored coefficient 1", max_error);
        require_close(
            coefficients.stored_coefficients[2], 8.0, 0.0,
            "FUN_007ba860 stored coefficient 2", max_error);
        require_close(
            coefficients.reciprocal_coefficients[0], 0.5, 0.0,
            "FUN_007ba860 reciprocal 0", max_error);
        require_close(
            coefficients.reciprocal_coefficients[1], 0.25, 0.0,
            "FUN_007ba860 reciprocal 1", max_error);
        require_close(
            coefficients.reciprocal_coefficients[2], 0.125, 0.0,
            "FUN_007ba860 reciprocal 2", max_error);

        const ConstraintRefreshFrame3f identity = {
            1.0f, 0.0f, 0.0f,
            0.0f, 1.0f, 0.0f,
            0.0f, 0.0f, 1.0f,
        };
        const auto identity_tensor =
            build_fun_007ba630_body_tensor({2.0, 3.0, 5.0}, identity);
        const double expected_identity[3][3] = {
            {2.0, 0.0, 0.0},
            {0.0, 3.0, 0.0},
            {0.0, 0.0, 5.0},
        };
        for (std::size_t row = 0; row < 3u; ++row) {
            for (std::size_t column = 0; column < 3u; ++column) {
                require_close(
                    identity_tensor[row][column],
                    expected_identity[row][column],
                    0.0,
                    "FUN_007ba630 identity tensor",
                    max_error);
            }
        }

        const ConstraintRefreshFrame3f nontrivial_basis = {
            1.0f, 2.0f, 3.0f,
            4.0f, 5.0f, 6.0f,
            7.0f, 8.0f, 9.0f,
        };
        const auto tensor =
            build_fun_007ba630_body_tensor(
                {2.0, 3.0, 5.0},
                nontrivial_basis);
        const double expected_tensor[3][3] = {
            {59.0, 128.0, 197.0},
            {128.0, 287.0, 446.0},
            {197.0, 446.0, 695.0},
        };
        for (std::size_t row = 0; row < 3u; ++row) {
            for (std::size_t column = 0; column < 3u; ++column) {
                require_close(
                    tensor[row][column],
                    expected_tensor[row][column],
                    0.0,
                    "FUN_007ba630 nontrivial tensor",
                    max_error);
            }
        }

        const ConstraintRefreshFrame3f diagonal_basis = {
            1.0f, 0.0f, 0.0f,
            0.0f, 2.0f, 0.0f,
            0.0f, 0.0f, 3.0f,
        };
        const auto prepared =
            prepare_fun_007ba7e0_body_frame_vector(
                diagonal_basis,
                {1.0, 2.0, 3.0},
                {4.0f, 5.0f, 6.0f});
        const double expected_local[3] = {1.0, 4.0, 9.0};
        const double expected_scaled[3] = {4.0, 20.0, 54.0};
        const double expected_output[3] = {4.0, 40.0, 162.0};
        for (std::size_t component = 0; component < 3u; ++component) {
            require_close(
                prepared.local_vector[component],
                expected_local[component],
                0.0,
                "FUN_007ba7e0 local vector",
                max_error);
            require_close(
                prepared.scaled_local_vector[component],
                expected_scaled[component],
                0.0,
                "FUN_007ba7e0 scaled local vector",
                max_error);
            require_close(
                prepared.output_vector[component],
                expected_output[component],
                0.0,
                "FUN_007ba7e0 output vector",
                max_error);
        }

        bool zero_rejected = false;
        try {
            (void)initialize_fun_007ba860_body_coefficients({1.0, 0.0, 2.0});
        } catch (const std::invalid_argument&) {
            zero_rejected = true;
        }
        if (!zero_rejected) {
            throw std::runtime_error(
                "FUN_007ba860 accepted zero reciprocal coefficient");
        }

        bool non_finite_rejected = false;
        try {
            auto bad_basis = identity;
            bad_basis[4] = std::numeric_limits<float>::infinity();
            (void)build_fun_007ba630_body_tensor(
                {1.0, 2.0, 3.0}, bad_basis);
        } catch (const std::invalid_argument&) {
            non_finite_rejected = true;
        }
        if (!non_finite_rejected) {
            throw std::runtime_error(
                "FUN_007ba630 accepted non-finite basis");
        }

        std::cout
            << "{\"format\":\"SHIFT.NativeBodyFramePreparation/1\","
            << "\"ready\":true,"
            << "\"coefficient_init_function\":\"FUN_007ba860\","
            << "\"tensor_function\":\"FUN_007ba630\","
            << "\"frame_prepare_function\":\"FUN_007ba7e0\","
            << "\"zero_coefficient_rejected\":true,"
            << "\"non_finite_rejected\":true,"
            << "\"max_absolute_error\":" << max_error << "}\n";
        return 0;
    } catch (const std::exception& exc) {
        std::cerr << exc.what() << "\n";
        return 1;
    }
}
