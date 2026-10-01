#pragma once

#include <array>
#include <cstdint>

namespace shift::runtime::physics {

inline constexpr const char* kPostSolveSourceFunction =
    "FUN_007b4110";
inline constexpr const char* kPositiveBodyAccumulatorSourceFunction =
    "FUN_007baa70";
inline constexpr const char* kNegativeBodyAccumulatorSourceFunction =
    "FUN_007baaf0";

using Vec3d = std::array<double, 3>;

struct BodyAccumulatorState {
    Vec3d angular{0.0, 0.0, 0.0};
    Vec3d linear{0.0, 0.0, 0.0};
};

struct BodyAccumulatorDelta {
    Vec3d angular{0.0, 0.0, 0.0};
    Vec3d linear{0.0, 0.0, 0.0};
    int sign = 1;
};

struct JointPostSolveResult {
    BodyAccumulatorState positive{};
    BodyAccumulatorState negative{};
    Vec3d solution{};
};

struct HingePostSolveResult {
    BodyAccumulatorState positive{};
    BodyAccumulatorState negative{};
    Vec3d positive_delta{};
    Vec3d negative_delta{};
    std::array<double, 2> solution{0.0, 0.0};
};

struct BarPostSolveResult {
    BodyAccumulatorState positive{};
    BodyAccumulatorState negative{};
    Vec3d vector_solution{};
    double solution_scalar = 0.0;
};

BodyAccumulatorDelta body_accumulator_delta(
    const Vec3d& lever_arm,
    const Vec3d& contribution,
    int sign);

BodyAccumulatorDelta apply_body_accumulator_delta(
    BodyAccumulatorState& state,
    const Vec3d& lever_arm,
    const Vec3d& contribution,
    int sign);

JointPostSolveResult apply_joint_solution(
    const BodyAccumulatorState& positive_state,
    const BodyAccumulatorState& negative_state,
    const Vec3d& solution,
    const Vec3d& positive_lever_arm,
    const Vec3d& negative_lever_arm);

Vec3d hinge_angular_delta(
    const std::array<double, 2>& solution,
    const Vec3d& angular_row,
    const Vec3d& linear_row,
    int sign);

HingePostSolveResult apply_hinge_solution(
    const BodyAccumulatorState& positive_state,
    const BodyAccumulatorState& negative_state,
    const std::array<double, 2>& solution,
    const Vec3d& positive_angular_row,
    const Vec3d& positive_linear_row,
    const Vec3d& negative_angular_row,
    const Vec3d& negative_linear_row);

BarPostSolveResult apply_bar_solution(
    const BodyAccumulatorState& positive_state,
    const BodyAccumulatorState& negative_state,
    double solution_scalar,
    const Vec3d& positive_lever_arm,
    const Vec3d& negative_lever_arm,
    const Vec3d& bar_direction);

}  // namespace shift::runtime::physics
