#pragma once

#include <array>
#include <cstddef>
#include <string>
#include <vector>

namespace shift::runtime::physics {

using Matrix3d = std::array<std::array<double, 3>, 3>;

struct JointTensorTerms {
    double d6 = 0.0;
    double d10 = 0.0;
    double d1 = 0.0;
    double d2 = 0.0;
    double d3 = 0.0;
    double d12 = 0.0;
    double d15 = 0.0;
    double d19 = 0.0;
    double d18 = 0.0;
};

struct JointSelfBlockResult {
    JointTensorTerms terms{};
    std::array<double, 6> lower_triangle{};
};

struct JointCouplingBlockResult {
    JointTensorTerms terms{};
    std::vector<double> raw_block;
    std::size_t raw_rows = 0;
    std::size_t raw_columns = 0;
    std::vector<double> block;
    std::size_t rows = 0;
    std::size_t columns = 0;
    std::size_t row_base = 0;
    std::size_t column_base = 0;
    double sign = 1.0;
    std::string orientation;
};

JointTensorTerms derive_fun_007bbb80_joint_tensor_terms(
    const Matrix3d& body_tensor,
    const std::array<double, 3>& joint_position);

JointSelfBlockResult evaluate_fun_007bbb80_joint_self(
    const Matrix3d& body_tensor,
    const std::array<double, 3>& joint_position,
    double inverse_scalar);

JointCouplingBlockResult evaluate_fun_007bbb80_joint_joint(
    const Matrix3d& body_tensor,
    const std::array<double, 3>& outer_position,
    const std::array<double, 3>& inner_position,
    double inverse_scalar,
    std::size_t outer_base,
    std::size_t inner_base,
    bool same_side);

JointCouplingBlockResult evaluate_fun_007bbb80_joint_hinge(
    const Matrix3d& body_tensor,
    const std::array<double, 3>& joint_position,
    const std::array<double, 3>& hinge_angular,
    const std::array<double, 3>& hinge_linear,
    std::size_t joint_base,
    std::size_t hinge_base,
    bool same_side);

JointCouplingBlockResult evaluate_fun_007bbb80_joint_bar(
    const Matrix3d& body_tensor,
    const std::array<double, 3>& joint_position,
    const std::array<double, 3>& bar_point,
    const std::array<double, 3>& bar_direction,
    double inverse_scalar,
    std::size_t joint_base,
    std::size_t bar_base,
    bool same_side);

std::vector<double> apply_fun_007bbb80_block(
    const std::vector<double>& matrix,
    std::size_t dimension,
    std::size_t row_base,
    std::size_t column_base,
    const std::vector<double>& block,
    std::size_t rows,
    std::size_t columns);

}  // namespace shift::runtime::physics
