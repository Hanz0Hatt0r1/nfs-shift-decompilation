#pragma once

#include "shift_bar_matrix_coupling.hpp"
#include "shift_bar_projection.hpp"
#include "shift_body_preprojection.hpp"
#include "shift_hinge_bar_matrix_coupling.hpp"
#include "shift_hinge_matrix_coupling.hpp"
#include "shift_hinge_projection.hpp"
#include "shift_joint_matrix_coupling.hpp"
#include "shift_joint_projection.hpp"

#include <array>
#include <cstddef>
#include <cstdint>
#include <vector>

namespace shift::runtime::physics {

struct PreparedJointSample {
    std::array<double, 3> position{};
    std::size_t scalar_base = 0;
    std::uint8_t side_flag = 0;
};

struct PreparedHingeSample {
    std::array<double, 3> angular{};
    std::array<double, 3> linear{};
    std::array<double, 3> position{};
    std::array<double, 3> frame_offset{};
    std::size_t scalar_base = 0;
    std::uint8_t side_flag = 0;
};

struct PreparedBarSample {
    std::array<double, 3> point{};
    std::array<double, 3> direction{};
    double side_bias = 0.0;
    std::size_t scalar_base = 0;
    std::uint8_t side_flag = 0;
};

struct BodyConstraintAssemblyInput {
    std::size_t scalar_count = 0;
    std::array<double, 3> body_position{};
    BodyPreProjectionInput preprojection{};
    Matrix3d body_tensor{};
    SdfConstraintScales scales{};
    std::vector<PreparedJointSample> joints;
    std::vector<PreparedHingeSample> hinges;
    std::vector<PreparedBarSample> bars;
};

struct BodyConstraintAssemblyResult {
    BodyPreProjectionResult preprojection{};
    std::vector<double> solver_vector;
    std::vector<double> lower_matrix;
    std::size_t joint_projection_count = 0;
    std::size_t hinge_projection_count = 0;
    std::size_t bar_projection_count = 0;
    std::size_t joint_matrix_self_count = 0;
    std::size_t joint_matrix_pair_count = 0;
    std::size_t hinge_matrix_self_count = 0;
    std::size_t hinge_matrix_pair_count = 0;
    std::size_t hinge_bar_pair_count = 0;
    std::size_t bar_matrix_self_count = 0;
    std::size_t bar_matrix_pair_count = 0;
};

BodyConstraintAssemblyResult assemble_fun_007bc680_body_constraints(
    const BodyConstraintAssemblyInput& input);

}  // namespace shift::runtime::physics
