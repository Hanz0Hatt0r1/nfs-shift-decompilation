#include "shift_post_solve_application.hpp"

#include <cmath>
#include <stdexcept>

namespace shift::runtime::physics {
namespace {

void require_finite(const Vec3d& value, const char* label) {
    for (double component : value) {
        if (!std::isfinite(component)) {
            throw std::invalid_argument(
                std::string(label) + " contains non-finite component");
        }
    }
}

void require_finite(
    const std::array<double, 2>& value,
    const char* label) {
    for (double component : value) {
        if (!std::isfinite(component)) {
            throw std::invalid_argument(
                std::string(label) + " contains non-finite component");
        }
    }
}

void require_state(
    const BodyAccumulatorState& state,
    const char* label) {
    require_finite(state.angular, label);
    require_finite(state.linear, label);
}

Vec3d add3(const Vec3d& lhs, const Vec3d& rhs) {
    return {
        lhs[0] + rhs[0],
        lhs[1] + rhs[1],
        lhs[2] + rhs[2],
    };
}

}  // namespace

BodyAccumulatorDelta body_accumulator_delta(
    const Vec3d& lever_arm,
    const Vec3d& contribution,
    int sign) {

    if (sign != 1 && sign != -1) {
        throw std::invalid_argument(
            "body accumulator sign must be +1 or -1");
    }
    require_finite(lever_arm, "lever_arm");
    require_finite(contribution, "contribution");

    const double s = static_cast<double>(sign);
    BodyAccumulatorDelta result{};
    result.sign = sign;
    result.linear = {
        s * contribution[0],
        s * contribution[1],
        s * contribution[2],
    };
    result.angular = {
        s * (
            lever_arm[1] * contribution[2] -
            lever_arm[2] * contribution[1]),
        s * (
            lever_arm[2] * contribution[0] -
            lever_arm[0] * contribution[2]),
        s * (
            lever_arm[0] * contribution[1] -
            lever_arm[1] * contribution[0]),
    };
    return result;
}

BodyAccumulatorDelta apply_body_accumulator_delta(
    BodyAccumulatorState& state,
    const Vec3d& lever_arm,
    const Vec3d& contribution,
    int sign) {

    require_state(state, "body_state");
    const BodyAccumulatorDelta delta =
        body_accumulator_delta(
            lever_arm,
            contribution,
            sign);
    state.angular = add3(state.angular, delta.angular);
    state.linear = add3(state.linear, delta.linear);
    return delta;
}

JointPostSolveResult apply_joint_solution(
    const BodyAccumulatorState& positive_state,
    const BodyAccumulatorState& negative_state,
    const Vec3d& solution,
    const Vec3d& positive_lever_arm,
    const Vec3d& negative_lever_arm) {

    require_state(positive_state, "positive_state");
    require_state(negative_state, "negative_state");
    require_finite(solution, "joint_solution");

    JointPostSolveResult result{};
    result.positive = positive_state;
    result.negative = negative_state;
    result.solution = solution;
    apply_body_accumulator_delta(
        result.positive,
        positive_lever_arm,
        solution,
        +1);
    apply_body_accumulator_delta(
        result.negative,
        negative_lever_arm,
        solution,
        -1);
    return result;
}

Vec3d hinge_angular_delta(
    const std::array<double, 2>& solution,
    const Vec3d& angular_row,
    const Vec3d& linear_row,
    int sign) {

    if (sign != 1 && sign != -1) {
        throw std::invalid_argument(
            "hinge angular sign must be +1 or -1");
    }
    require_finite(solution, "hinge_solution");
    require_finite(angular_row, "angular_row");
    require_finite(linear_row, "linear_row");

    const double s = static_cast<double>(sign);
    return {
        s * (
            angular_row[0] * solution[0] +
            linear_row[0] * solution[1]),
        s * (
            angular_row[1] * solution[0] +
            linear_row[1] * solution[1]),
        s * (
            angular_row[2] * solution[0] +
            linear_row[2] * solution[1]),
    };
}

HingePostSolveResult apply_hinge_solution(
    const BodyAccumulatorState& positive_state,
    const BodyAccumulatorState& negative_state,
    const std::array<double, 2>& solution,
    const Vec3d& positive_angular_row,
    const Vec3d& positive_linear_row,
    const Vec3d& negative_angular_row,
    const Vec3d& negative_linear_row) {

    require_state(positive_state, "positive_state");
    require_state(negative_state, "negative_state");

    HingePostSolveResult result{};
    result.positive = positive_state;
    result.negative = negative_state;
    result.solution = solution;
    result.positive_delta =
        hinge_angular_delta(
            solution,
            positive_angular_row,
            positive_linear_row,
            +1);
    result.negative_delta =
        hinge_angular_delta(
            solution,
            negative_angular_row,
            negative_linear_row,
            -1);
    result.positive.angular =
        add3(
            result.positive.angular,
            result.positive_delta);
    result.negative.angular =
        add3(
            result.negative.angular,
            result.negative_delta);
    return result;
}

BarPostSolveResult apply_bar_solution(
    const BodyAccumulatorState& positive_state,
    const BodyAccumulatorState& negative_state,
    double solution_scalar,
    const Vec3d& positive_lever_arm,
    const Vec3d& negative_lever_arm,
    const Vec3d& bar_direction) {

    if (!std::isfinite(solution_scalar)) {
        throw std::invalid_argument(
            "bar solution scalar must be finite");
    }
    require_state(positive_state, "positive_state");
    require_state(negative_state, "negative_state");
    require_finite(bar_direction, "bar_direction");

    BarPostSolveResult result{};
    result.positive = positive_state;
    result.negative = negative_state;
    result.solution_scalar = solution_scalar;
    result.vector_solution = {
        bar_direction[0] * solution_scalar,
        bar_direction[1] * solution_scalar,
        bar_direction[2] * solution_scalar,
    };
    apply_body_accumulator_delta(
        result.positive,
        positive_lever_arm,
        result.vector_solution,
        +1);
    apply_body_accumulator_delta(
        result.negative,
        negative_lever_arm,
        result.vector_solution,
        -1);
    return result;
}

}  // namespace shift::runtime::physics
