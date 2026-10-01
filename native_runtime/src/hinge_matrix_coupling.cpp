#include "shift_hinge_matrix_coupling.hpp"

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

std::array<double, 3> transform_fun_007aefb0(
    const std::array<float, 9>& matrix,
    const std::array<double, 3>& vector) {

    const float x = static_cast<float>(vector[0]);
    const float y = static_cast<float>(vector[1]);
    const float z = static_cast<float>(vector[2]);
    return {
        static_cast<double>(
            matrix[2] * z + matrix[0] * x + matrix[1] * y),
        static_cast<double>(
            matrix[5] * z + matrix[4] * y + matrix[3] * x),
        static_cast<double>(
            matrix[8] * z + matrix[7] * y + matrix[6] * x),
    };
}

double dot(
    const std::array<double, 3>& left,
    const std::array<double, 3>& right) {

    return left[0] * right[0] +
           left[1] * right[1] +
           left[2] * right[2];
}

}  // namespace

HingeMatrixRows transform_fun_007bb250_hinge_rows(
    const std::array<float, 9>& body_frame,
    const std::array<double, 3>& angular,
    const std::array<double, 3>& linear) {

    require_finite(body_frame, "HINGE body frame");
    require_finite(angular, "HINGE angular row");
    require_finite(linear, "HINGE linear row");

    HingeMatrixRows result{};
    result.angular =
        transform_fun_007aefb0(body_frame, angular);
    result.linear =
        transform_fun_007aefb0(body_frame, linear);
    require_finite(
        result.angular,
        "FUN_007bb250 transformed angular row");
    require_finite(
        result.linear,
        "FUN_007bb250 transformed linear row");
    return result;
}

HingeSelfBlockResult evaluate_fun_007bb250_hinge_self(
    const std::array<float, 9>& body_frame,
    const std::array<double, 3>& angular,
    const std::array<double, 3>& linear) {

    const auto transformed =
        transform_fun_007bb250_hinge_rows(
            body_frame,
            angular,
            linear);

    HingeSelfBlockResult result{};
    result.transformed = transformed;
    result.lower_triangle = {
        dot(angular, transformed.angular),
        dot(angular, transformed.linear),
        dot(linear, transformed.linear),
    };
    require_finite(
        result.lower_triangle,
        "FUN_007bb250 HINGE self block");
    return result;
}

HingePairBlockResult evaluate_fun_007bb250_hinge_pair(
    const std::array<float, 9>& body_frame,
    const std::array<double, 3>& outer_angular,
    const std::array<double, 3>& outer_linear,
    const std::array<double, 3>& inner_angular,
    const std::array<double, 3>& inner_linear,
    std::size_t outer_base,
    std::size_t inner_base,
    bool same_side) {

    require_finite(inner_angular, "inner HINGE angular row");
    require_finite(inner_linear, "inner HINGE linear row");
    const auto transformed =
        transform_fun_007bb250_hinge_rows(
            body_frame,
            outer_angular,
            outer_linear);

    const double d5 =
        dot(inner_angular, transformed.angular);
    const double d6 =
        dot(inner_linear, transformed.angular);
    const double d8 =
        dot(inner_angular, transformed.linear);
    const double d7 =
        dot(inner_linear, transformed.linear);

    HingePairBlockResult result{};
    result.transformed_outer = transformed;
    result.raw_coefficients = {d5, d6, d8, d7};
    result.sign = same_side ? 1.0 : -1.0;

    if (inner_base < outer_base) {
        result.block = {
            result.sign * d5,
            result.sign * d6,
            result.sign * d8,
            result.sign * d7,
        };
        result.row_base = outer_base;
        result.column_base = inner_base;
        result.orientation =
            "outer_rows_by_inner_columns";
    } else {
        result.block = {
            result.sign * d5,
            result.sign * d8,
            result.sign * d6,
            result.sign * d7,
        };
        result.row_base = inner_base;
        result.column_base = outer_base;
        result.orientation =
            "inner_rows_by_outer_columns";
    }

    require_finite(
        result.raw_coefficients,
        "FUN_007bb250 HINGE raw coefficients");
    require_finite(
        result.block,
        "FUN_007bb250 HINGE stored block");
    return result;
}

std::vector<double> apply_fun_007bb250_hinge_block(
    const std::vector<double>& matrix,
    std::size_t dimension,
    std::size_t row_base,
    std::size_t column_base,
    const std::array<double, 4>& block) {

    require_finite(matrix, "HINGE coupling destination matrix");
    require_finite(block, "HINGE coupling block");
    if (dimension == 0 ||
        matrix.size() != dimension * dimension) {
        throw std::invalid_argument(
            "HINGE coupling destination matrix shape is invalid");
    }
    if (row_base > dimension ||
        column_base > dimension ||
        2u > dimension - row_base ||
        2u > dimension - column_base) {
        throw std::out_of_range(
            "HINGE coupling block is outside destination matrix");
    }

    std::vector<double> result = matrix;
    result[row_base * dimension + column_base] += block[0];
    result[row_base * dimension + column_base + 1u] += block[1];
    result[(row_base + 1u) * dimension + column_base] += block[2];
    result[(row_base + 1u) * dimension + column_base + 1u] +=
        block[3];
    return result;
}

}  // namespace shift::runtime::physics
