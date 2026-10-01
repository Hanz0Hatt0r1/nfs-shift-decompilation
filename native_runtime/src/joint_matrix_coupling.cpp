#include "shift_joint_matrix_coupling.hpp"

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

void require_finite_tensor(const Matrix3d& matrix) {
    for (const auto& row : matrix) {
        require_finite(row, "JOINT body tensor");
    }
}

std::vector<double> signed_copy(
    const std::vector<double>& values,
    double sign) {

    std::vector<double> result;
    result.reserve(values.size());
    for (double value : values) {
        result.push_back(sign * value);
    }
    return result;
}

std::vector<double> transpose(
    const std::vector<double>& values,
    std::size_t rows,
    std::size_t columns) {

    if (values.size() != rows * columns) {
        throw std::invalid_argument(
            "coupling block shape does not match payload");
    }
    std::vector<double> result(values.size(), 0.0);
    for (std::size_t row = 0; row < rows; ++row) {
        for (std::size_t column = 0; column < columns; ++column) {
            result[column * rows + row] =
                values[row * columns + column];
        }
    }
    return result;
}

}  // namespace

JointTensorTerms derive_fun_007bbb80_joint_tensor_terms(
    const Matrix3d& body_tensor,
    const std::array<double, 3>& joint_position) {

    require_finite_tensor(body_tensor);
    require_finite(joint_position, "JOINT position");

    const double x = joint_position[0];
    const double y = joint_position[1];
    const double z = joint_position[2];
    const double a = body_tensor[0][0];
    const double b = body_tensor[0][1];
    const double c = body_tensor[0][2];
    const double d = body_tensor[1][1];
    const double e = body_tensor[1][2];
    const double f = body_tensor[2][2];

    JointTensorTerms result{};
    result.d6 = b * z - c * y;
    result.d10 = d * z - e * y;
    result.d1 = e * z - f * y;
    result.d2 = c * x - a * z;
    result.d3 = e * x - b * z;
    result.d12 = f * x - e * z;
    result.d15 = a * y - b * x;
    result.d19 = b * y - d * x;
    result.d18 = c * y - e * x;
    return result;
}

JointSelfBlockResult evaluate_fun_007bbb80_joint_self(
    const Matrix3d& body_tensor,
    const std::array<double, 3>& joint_position,
    double inverse_scalar) {

    if (!std::isfinite(inverse_scalar)) {
        throw std::invalid_argument(
            "JOINT inverse scalar must be finite");
    }
    const auto terms = derive_fun_007bbb80_joint_tensor_terms(
        body_tensor,
        joint_position);
    const double x = joint_position[0];
    const double y = joint_position[1];
    const double z = joint_position[2];

    const double d7 = z * terms.d10 - y * terms.d1 + inverse_scalar;
    const double d13 = z * terms.d3 - y * terms.d12;
    const double d11 = x * terms.d12 - z * terms.d2 + inverse_scalar;
    const double d17 = z * terms.d19 - y * terms.d18;
    const double d16 = x * terms.d18 - z * terms.d15;
    const double d14 = y * terms.d15 - x * terms.d19 + inverse_scalar;

    JointSelfBlockResult result{};
    result.terms = terms;
    result.lower_triangle = {d7, d13, d11, d17, d16, d14};
    require_finite(
        result.lower_triangle,
        "FUN_007bbb80 JOINT self block");
    return result;
}

JointCouplingBlockResult evaluate_fun_007bbb80_joint_joint(
    const Matrix3d& body_tensor,
    const std::array<double, 3>& outer_position,
    const std::array<double, 3>& inner_position,
    double inverse_scalar,
    std::size_t outer_base,
    std::size_t inner_base,
    bool same_side) {

    if (!std::isfinite(inverse_scalar)) {
        throw std::invalid_argument(
            "JOINT inverse scalar must be finite");
    }
    require_finite(inner_position, "inner JOINT position");
    const auto terms = derive_fun_007bbb80_joint_tensor_terms(
        body_tensor,
        outer_position);

    const double ix = inner_position[0];
    const double iy = inner_position[1];
    const double iz = inner_position[2];

    const double d7 =
        iz * terms.d10 - iy * terms.d1 + inverse_scalar;
    const double d13 =
        iz * terms.d3 - iy * terms.d12;
    const double d11 =
        ix * terms.d12 - iz * terms.d2 + inverse_scalar;
    const double d17 =
        iz * terms.d19 - iy * terms.d18;
    const double d16 =
        ix * terms.d18 - iz * terms.d15;
    const double d14 =
        iy * terms.d15 - ix * terms.d19 + inverse_scalar;
    const double d9 =
        ix * terms.d1 - iz * terms.d6;
    const double d8 =
        terms.d6 * iy - ix * terms.d10;
    const double d20 =
        iy * terms.d2 - ix * terms.d3;

    JointCouplingBlockResult result{};
    result.terms = terms;
    result.raw_rows = 3;
    result.raw_columns = 3;
    result.raw_block = {
        d7, d9, d8,
        d13, d11, d20,
        d17, d16, d14,
    };
    result.sign = same_side ? 1.0 : -1.0;

    if (inner_base < outer_base) {
        result.block = signed_copy(
            result.raw_block,
            result.sign);
        result.rows = 3;
        result.columns = 3;
        result.row_base = outer_base;
        result.column_base = inner_base;
        result.orientation =
            "outer_rows_by_inner_columns";
    } else {
        result.block = signed_copy(
            transpose(result.raw_block, 3, 3),
            result.sign);
        result.rows = 3;
        result.columns = 3;
        result.row_base = inner_base;
        result.column_base = outer_base;
        result.orientation =
            "inner_rows_by_outer_columns";
    }

    require_finite(
        result.raw_block,
        "FUN_007bbb80 JOINT/JOINT raw block");
    require_finite(
        result.block,
        "FUN_007bbb80 JOINT/JOINT stored block");
    return result;
}

JointCouplingBlockResult evaluate_fun_007bbb80_joint_hinge(
    const Matrix3d& body_tensor,
    const std::array<double, 3>& joint_position,
    const std::array<double, 3>& hinge_angular,
    const std::array<double, 3>& hinge_linear,
    std::size_t joint_base,
    std::size_t hinge_base,
    bool same_side) {

    require_finite(hinge_angular, "HINGE angular vector");
    require_finite(hinge_linear, "HINGE linear vector");
    const auto terms = derive_fun_007bbb80_joint_tensor_terms(
        body_tensor,
        joint_position);

    const double ax = hinge_angular[0];
    const double ay = hinge_angular[1];
    const double az = hinge_angular[2];
    const double lx = hinge_linear[0];
    const double ly = hinge_linear[1];
    const double lz = hinge_linear[2];

    const double d7 =
        az * terms.d1 + ay * terms.d10 + ax * terms.d6;
    const double d14 =
        az * terms.d12 + ax * terms.d2 + ay * terms.d3;
    const double d17 =
        az * terms.d18 + ax * terms.d15 + ay * terms.d19;
    const double d11 =
        lz * terms.d1 + ly * terms.d10 + lx * terms.d6;
    const double d13 =
        lz * terms.d12 + lx * terms.d2 + ly * terms.d3;
    const double d16 =
        lz * terms.d18 + lx * terms.d15 + ly * terms.d19;

    JointCouplingBlockResult result{};
    result.terms = terms;
    result.raw_rows = 3;
    result.raw_columns = 2;
    result.raw_block = {
        d7, d11,
        d14, d13,
        d17, d16,
    };
    result.sign = same_side ? 1.0 : -1.0;

    if (hinge_base < joint_base) {
        result.block = signed_copy(
            result.raw_block,
            result.sign);
        result.rows = 3;
        result.columns = 2;
        result.row_base = joint_base;
        result.column_base = hinge_base;
        result.orientation =
            "joint_rows_by_hinge_columns";
    } else {
        result.block = signed_copy(
            transpose(result.raw_block, 3, 2),
            result.sign);
        result.rows = 2;
        result.columns = 3;
        result.row_base = hinge_base;
        result.column_base = joint_base;
        result.orientation =
            "hinge_rows_by_joint_columns";
    }

    require_finite(
        result.raw_block,
        "FUN_007bbb80 JOINT/HINGE raw block");
    require_finite(
        result.block,
        "FUN_007bbb80 JOINT/HINGE stored block");
    return result;
}

JointCouplingBlockResult evaluate_fun_007bbb80_joint_bar(
    const Matrix3d& body_tensor,
    const std::array<double, 3>& joint_position,
    const std::array<double, 3>& bar_point,
    const std::array<double, 3>& bar_direction,
    double inverse_scalar,
    std::size_t joint_base,
    std::size_t bar_base,
    bool same_side) {

    if (!std::isfinite(inverse_scalar)) {
        throw std::invalid_argument(
            "JOINT/BAR inverse scalar must be finite");
    }
    require_finite(bar_point, "BAR point");
    require_finite(bar_direction, "BAR direction");
    const auto terms = derive_fun_007bbb80_joint_tensor_terms(
        body_tensor,
        joint_position);

    const double px = bar_point[0];
    const double py = bar_point[1];
    const double pz = bar_point[2];
    const double qx = bar_direction[0];
    const double qy = bar_direction[1];
    const double qz = bar_direction[2];

    const double d7 =
        (terms.d6 * py - px * terms.d10) * qz +
        (pz * terms.d10 - terms.d1 * py + inverse_scalar) * qx +
        qy * (px * terms.d1 - pz * terms.d6);
    const double d11 =
        (pz * terms.d3 - terms.d12 * py) * qx +
        qy * (px * terms.d12 - pz * terms.d2 + inverse_scalar) +
        qz * (terms.d2 * py - px * terms.d3);
    const double d13 =
        qz * (terms.d15 * py - px * terms.d19 + inverse_scalar) +
        (pz * terms.d19 - terms.d18 * py) * qx +
        qy * (px * terms.d18 - pz * terms.d15);

    JointCouplingBlockResult result{};
    result.terms = terms;
    result.raw_rows = 3;
    result.raw_columns = 1;
    result.raw_block = {d7, d11, d13};
    result.sign = same_side ? 1.0 : -1.0;

    if (bar_base < joint_base) {
        result.block = signed_copy(
            result.raw_block,
            result.sign);
        result.rows = 3;
        result.columns = 1;
        result.row_base = joint_base;
        result.column_base = bar_base;
        result.orientation =
            "joint_rows_by_bar_column";
    } else {
        result.block = signed_copy(
            transpose(result.raw_block, 3, 1),
            result.sign);
        result.rows = 1;
        result.columns = 3;
        result.row_base = bar_base;
        result.column_base = joint_base;
        result.orientation =
            "bar_row_by_joint_columns";
    }

    require_finite(
        result.raw_block,
        "FUN_007bbb80 JOINT/BAR raw block");
    require_finite(
        result.block,
        "FUN_007bbb80 JOINT/BAR stored block");
    return result;
}

std::vector<double> apply_fun_007bbb80_block(
    const std::vector<double>& matrix,
    std::size_t dimension,
    std::size_t row_base,
    std::size_t column_base,
    const std::vector<double>& block,
    std::size_t rows,
    std::size_t columns) {

    require_finite(matrix, "JOINT coupling destination matrix");
    require_finite(block, "JOINT coupling block");
    if (dimension == 0 ||
        matrix.size() != dimension * dimension) {
        throw std::invalid_argument(
            "JOINT coupling destination matrix shape is invalid");
    }
    if (rows == 0 || columns == 0 ||
        block.size() != rows * columns) {
        throw std::invalid_argument(
            "JOINT coupling block shape is invalid");
    }
    if (row_base > dimension ||
        column_base > dimension ||
        rows > dimension - row_base ||
        columns > dimension - column_base) {
        throw std::out_of_range(
            "JOINT coupling block is outside destination matrix");
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
