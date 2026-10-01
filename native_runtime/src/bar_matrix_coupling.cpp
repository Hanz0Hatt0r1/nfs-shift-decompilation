#include "shift_bar_matrix_coupling.hpp"

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

}  // namespace

BarCrossFrameResult evaluate_fun_007bb6c0_cross_frame(
    const std::array<float, 9>& body_frame,
    const std::array<double, 3>& point,
    const std::array<double, 3>& direction) {

    require_finite(body_frame, "BAR body frame");
    require_finite(point, "BAR point");
    require_finite(direction, "BAR direction");

    const double px = point[0];
    const double py = point[1];
    const double pz = point[2];
    const double qx = direction[0];
    const double qy = direction[1];
    const double qz = direction[2];

    BarCrossFrameResult result{};
    result.cross = {
        py * qz - pz * qy,
        pz * qx - qz * px,
        qy * px - py * qx,
    };
    result.transformed =
        transform_fun_007aefb0(
            body_frame,
            result.cross);
    require_finite(
        result.cross,
        "FUN_007bb6c0 BAR cross");
    require_finite(
        result.transformed,
        "FUN_007bb6c0 transformed BAR cross");
    return result;
}

BarSelfCoefficientResult evaluate_fun_007bb6c0_bar_self(
    const std::array<float, 9>& body_frame,
    const std::array<double, 3>& point,
    const std::array<double, 3>& direction,
    double inverse_scalar) {

    if (!std::isfinite(inverse_scalar)) {
        throw std::invalid_argument(
            "BAR inverse scalar must be finite");
    }
    const auto frame =
        evaluate_fun_007bb6c0_cross_frame(
            body_frame,
            point,
            direction);

    const double px = point[0];
    const double py = point[1];
    const double pz = point[2];
    const double qx = direction[0];
    const double qy = direction[1];
    const double qz = direction[2];
    const double lx = frame.transformed[0];
    const double ly = frame.transformed[1];
    const double lz = frame.transformed[2];

    BarSelfCoefficientResult result{};
    result.frame = frame;
    result.inverse_scalar_terms = {
        qx * inverse_scalar,
        qy * inverse_scalar,
        qz * inverse_scalar,
    };
    const double dx = result.inverse_scalar_terms[0];
    const double dy = result.inverse_scalar_terms[1];
    const double dz = result.inverse_scalar_terms[2];

    result.coefficient =
        ((py * lx - px * ly) + dz) * qz +
        qy * ((px * lz - pz * lx) + dy) +
        qx * ((pz * ly - py * lz) + dx);
    if (!std::isfinite(result.coefficient)) {
        throw std::invalid_argument(
            "FUN_007bb6c0 BAR self coefficient is non-finite");
    }
    return result;
}

BarPairCoefficientResult evaluate_fun_007bb6c0_bar_pair(
    const std::array<float, 9>& body_frame,
    const std::array<double, 3>& outer_point,
    const std::array<double, 3>& outer_direction,
    const std::array<double, 3>& inner_point,
    const std::array<double, 3>& inner_direction,
    double inverse_scalar,
    std::size_t outer_base,
    std::size_t inner_base,
    bool same_side) {

    if (!std::isfinite(inverse_scalar)) {
        throw std::invalid_argument(
            "BAR inverse scalar must be finite");
    }
    require_finite(inner_point, "inner BAR point");
    require_finite(inner_direction, "inner BAR direction");

    const auto frame =
        evaluate_fun_007bb6c0_cross_frame(
            body_frame,
            outer_point,
            outer_direction);

    const double qx = outer_direction[0];
    const double qy = outer_direction[1];
    const double qz = outer_direction[2];
    const double lx = frame.transformed[0];
    const double ly = frame.transformed[1];
    const double lz = frame.transformed[2];
    const double ix = inner_point[0];
    const double iy = inner_point[1];
    const double iz = inner_point[2];
    const double iqx = inner_direction[0];
    const double iqy = inner_direction[1];
    const double iqz = inner_direction[2];

    BarPairCoefficientResult result{};
    result.outer_frame = frame;
    result.inverse_scalar_terms = {
        qx * inverse_scalar,
        qy * inverse_scalar,
        qz * inverse_scalar,
    };
    const double dx = result.inverse_scalar_terms[0];
    const double dy = result.inverse_scalar_terms[1];
    const double dz = result.inverse_scalar_terms[2];

    result.raw_coefficient =
        iqy * ((lz * ix - lx * iz) + dy) +
        iqx * ((ly * iz - iy * lz) + dx) +
        iqz * ((lx * iy - ly * ix) + dz);
    result.sign = same_side ? 1.0 : -1.0;
    result.coefficient =
        result.sign * result.raw_coefficient;
    result.row = std::max(outer_base, inner_base);
    result.column = std::min(outer_base, inner_base);

    if (!std::isfinite(result.raw_coefficient) ||
        !std::isfinite(result.coefficient)) {
        throw std::invalid_argument(
            "FUN_007bb6c0 BAR pair coefficient is non-finite");
    }
    return result;
}

std::vector<double> apply_fun_007bb6c0_bar_scalar(
    const std::vector<double>& matrix,
    std::size_t dimension,
    std::size_t row,
    std::size_t column,
    double value) {

    require_finite(matrix, "BAR coupling destination matrix");
    if (!std::isfinite(value)) {
        throw std::invalid_argument(
            "BAR coupling scalar must be finite");
    }
    if (dimension == 0 ||
        matrix.size() != dimension * dimension) {
        throw std::invalid_argument(
            "BAR destination matrix shape is invalid");
    }
    if (row >= dimension || column >= dimension) {
        throw std::out_of_range(
            "BAR matrix cell is outside destination matrix");
    }

    std::vector<double> result = matrix;
    result[row * dimension + column] += value;
    return result;
}

}  // namespace shift::runtime::physics
