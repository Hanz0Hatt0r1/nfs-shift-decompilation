#include "shift_hinge_bar_matrix_coupling.hpp"

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

}  // namespace

HingeBarPairResult evaluate_fun_007bb250_hinge_bar(
    const std::array<float, 9>& body_frame,
    const std::array<double, 3>& hinge_angular,
    const std::array<double, 3>& hinge_linear,
    const std::array<double, 3>& bar_point,
    const std::array<double, 3>& bar_direction,
    std::size_t hinge_base,
    std::size_t bar_base,
    bool same_side) {

    require_finite(bar_point, "BAR point");
    require_finite(bar_direction, "BAR direction");
    const auto transformed =
        transform_fun_007bb250_hinge_rows(
            body_frame,
            hinge_angular,
            hinge_linear);

    const double a0 = transformed.angular[0];
    const double a1 = transformed.angular[1];
    const double a2 = transformed.angular[2];
    const double b0 = transformed.linear[0];
    const double b1 = transformed.linear[1];
    const double b2 = transformed.linear[2];
    const double px = bar_point[0];
    const double py = bar_point[1];
    const double pz = bar_point[2];
    const double qx = bar_direction[0];
    const double qy = bar_direction[1];
    const double qz = bar_direction[2];

    const double d5 =
        (a0 * py - px * a1) * qz +
        (a2 * px - pz * a0) * qy +
        qx * (pz * a1 - a2 * py);
    const double d6 =
        (b0 * py - px * b1) * qz +
        (b2 * px - pz * b0) * qy +
        qx * (pz * b1 - b2 * py);

    HingeBarPairResult result{};
    result.transformed_hinge = transformed;
    result.raw_coefficients = {d5, d6};
    result.sign = same_side ? 1.0 : -1.0;

    if (bar_base < hinge_base) {
        result.block = {
            result.sign * d5,
            result.sign * d6,
        };
        result.rows = 2;
        result.columns = 1;
        result.row_base = hinge_base;
        result.column_base = bar_base;
        result.orientation =
            "hinge_rows_by_bar_column";
    } else {
        result.block = {
            result.sign * d5,
            result.sign * d6,
        };
        result.rows = 1;
        result.columns = 2;
        result.row_base = bar_base;
        result.column_base = hinge_base;
        result.orientation =
            "bar_row_by_hinge_columns";
    }

    require_finite(
        result.raw_coefficients,
        "FUN_007bb250 HINGE/BAR raw coefficients");
    require_finite(
        result.block,
        "FUN_007bb250 HINGE/BAR stored block");
    return result;
}

std::vector<double> apply_fun_007bb250_hinge_bar_block(
    const std::vector<double>& matrix,
    std::size_t dimension,
    std::size_t row_base,
    std::size_t column_base,
    const std::vector<double>& block,
    std::size_t rows,
    std::size_t columns) {

    require_finite(matrix, "HINGE/BAR destination matrix");
    require_finite(block, "HINGE/BAR coupling block");
    if (dimension == 0 ||
        matrix.size() != dimension * dimension) {
        throw std::invalid_argument(
            "HINGE/BAR destination matrix shape is invalid");
    }
    if (rows == 0 || columns == 0 ||
        block.size() != rows * columns) {
        throw std::invalid_argument(
            "HINGE/BAR block shape is invalid");
    }
    if (row_base > dimension ||
        column_base > dimension ||
        rows > dimension - row_base ||
        columns > dimension - column_base) {
        throw std::out_of_range(
            "HINGE/BAR block is outside destination matrix");
    }

    std::vector<double> result = matrix;
    for (std::size_t row = 0; row < rows; ++row) {
        for (std::size_t column = 0; column < columns; ++column) {
            result[(row_base + row) * dimension +
                   column_base + column] +=
                block[row * columns + column];
        }
    }
    return result;
}

}  // namespace shift::runtime::physics
