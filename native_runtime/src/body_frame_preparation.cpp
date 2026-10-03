#include "shift_body_frame_preparation.hpp"

#include <cmath>
#include <stdexcept>
#include <string>

namespace shift::runtime::physics {
namespace {

template <typename Range>
void require_finite(const Range& values, const char* label) {
    for (const auto value : values) {
        if (!std::isfinite(static_cast<double>(value))) {
            throw std::invalid_argument(
                std::string(label) + " contains non-finite value");
        }
    }
}

float basis_at(
    const ConstraintRefreshFrame3f& basis,
    std::size_t row,
    std::size_t column) {
    return basis[row * 3u + column];
}

}  // namespace

BodyCoefficientInitializationResult
initialize_fun_007ba860_body_coefficients(
    const std::array<double, 3>& coefficients) {

    require_finite(coefficients, "FUN_007ba860 coefficient input");

    BodyCoefficientInitializationResult result{};
    for (std::size_t index = 0; index < 3u; ++index) {
        if (coefficients[index] == 0.0) {
            throw std::invalid_argument(
                "FUN_007ba860 coefficient must be non-zero");
        }
        result.stored_coefficients[index] =
            static_cast<float>(coefficients[index]);
        result.reciprocal_coefficients[index] =
            1.0 / coefficients[index];
        if (!std::isfinite(
                static_cast<double>(result.stored_coefficients[index])) ||
            !std::isfinite(result.reciprocal_coefficients[index])) {
            throw std::invalid_argument(
                "FUN_007ba860 coefficient conversion is non-finite");
        }
    }
    return result;
}

BodyTensor3f build_fun_007ba630_body_tensor(
    const std::array<double, 3>& diagonal,
    const ConstraintRefreshFrame3f& basis) {

    require_finite(diagonal, "FUN_007ba630 diagonal");
    require_finite(basis, "FUN_007ba630 basis");

    const std::array<float, 3> d = {
        static_cast<float>(diagonal[0]),
        static_cast<float>(diagonal[1]),
        static_cast<float>(diagonal[2]),
    };
    require_finite(d, "FUN_007ba630 float diagonal");

    BodyTensor3f result{};
    for (std::size_t row = 0; row < 3u; ++row) {
        for (std::size_t column = row; column < 3u; ++column) {
            const float value =
                basis_at(basis, row, 0u) * basis_at(basis, column, 0u) * d[0] +
                basis_at(basis, row, 1u) * basis_at(basis, column, 1u) * d[1] +
                basis_at(basis, row, 2u) * basis_at(basis, column, 2u) * d[2];
            if (!std::isfinite(static_cast<double>(value))) {
                throw std::invalid_argument(
                    "FUN_007ba630 tensor result is non-finite");
            }
            result[row][column] = value;
        }
    }

    result[1][0] = result[0][1];
    result[2][0] = result[0][2];
    result[2][1] = result[1][2];
    return result;
}

BodyFramePreparationResult prepare_fun_007ba7e0_body_frame_vector(
    const ConstraintRefreshFrame3f& basis,
    const ConstraintRefreshVector3d& body_vector,
    const std::array<float, 3>& scale) {

    require_finite(basis, "FUN_007ba7e0 basis");
    require_finite(body_vector, "FUN_007ba7e0 body vector");
    require_finite(scale, "FUN_007ba7e0 scale");

    BodyFramePreparationResult result{};
    result.local_vector =
        transform_fun_007af0a0_refresh(basis, body_vector);

    for (std::size_t component = 0; component < 3u; ++component) {
        result.scaled_local_vector[component] =
            static_cast<float>(
                result.local_vector[component] *
                static_cast<double>(scale[component]));
    }
    require_finite(
        result.scaled_local_vector,
        "FUN_007ba7e0 scaled local vector");

    const ConstraintRefreshVector3d scaled_as_double = {
        static_cast<double>(result.scaled_local_vector[0]),
        static_cast<double>(result.scaled_local_vector[1]),
        static_cast<double>(result.scaled_local_vector[2]),
    };
    result.output_vector =
        transform_fun_007aefb0_refresh(
            basis,
            scaled_as_double);
    return result;
}

}  // namespace shift::runtime::physics
