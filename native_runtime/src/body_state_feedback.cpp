#include "shift_body_state_feedback.hpp"

#include <algorithm>
#include <cmath>
#include <stdexcept>
#include <string>

namespace shift::runtime::physics {
namespace {

double compare_value(
    double actual,
    double expected,
    double tolerance,
    const char* label) {

    if (!std::isfinite(actual) || !std::isfinite(expected)) {
        throw std::runtime_error(
            std::string(label) + " contains non-finite value");
    }
    const double error = std::abs(actual - expected);
    const double limit =
        tolerance * std::max(1.0, std::abs(expected));
    if (error > limit) {
        throw std::runtime_error(
            std::string(label) + " mismatch");
    }
    return error;
}

template <typename A, typename B>
double compare_vec3(
    const A& actual,
    const B& expected,
    double tolerance,
    const char* label) {

    double max_error = 0.0;
    for (std::size_t i = 0; i < 3; ++i) {
        max_error = std::max(
            max_error,
            compare_value(actual[i], expected[i], tolerance, label));
    }
    return max_error;
}

void require_relation_counts(
    const PreparedConstraintSampleRelationFrame& relations,
    const PreparedPostSolveBodyProjection& projection) {

    if (relations.joints.size() != projection.joints.size() ||
        relations.hinges.size() != projection.hinges.size() ||
        relations.bars.size() != projection.bars.size()) {
        throw std::runtime_error(
            "BODY feedback relation/post-solve row cardinality mismatch");
    }
}

}  // namespace

BodyStateFeedbackContractResult verify_body_state_feedback_contract(
    const PreparedGeneratedBodyConstraintFrame& source,
    const PreparedConstraintSampleRelationFrame& relations,
    const PreparedPostSolveBodyProjection& projection,
    double tolerance) {

    if (!std::isfinite(tolerance) || tolerance <= 0.0) {
        throw std::invalid_argument(
            "BODY feedback tolerance must be finite and positive");
    }
    if (source.bodies.empty() ||
        source.bodies.size() != projection.bodies.size() ||
        source.bodies.size() != relations.body_count) {
        throw std::runtime_error(
            "BODY feedback body cardinality mismatch");
    }
    require_relation_counts(relations, projection);

    BodyStateFeedbackContractResult result{};
    result.body_count = source.bodies.size();
    result.joint_relation_count = relations.joints.size();
    result.hinge_relation_count = relations.hinges.size();
    result.bar_relation_count = relations.bars.size();

    for (std::size_t body = 0; body < source.bodies.size(); ++body) {
        const auto& prepared = source.bodies[body].constraints.preprojection;
        const auto& post_solve = projection.bodies[body];
        result.max_seed_error = std::max(
            result.max_seed_error,
            compare_vec3(
                prepared.angular_state,
                post_solve.angular,
                tolerance,
                "BODY feedback angular seed"));
        result.max_seed_error = std::max(
            result.max_seed_error,
            compare_vec3(
                prepared.linear_state,
                post_solve.linear,
                tolerance,
                "BODY feedback linear seed"));
    }

    const auto refreshed = refresh_generated_body_constraint_frame(
        source,
        relations);
    const auto& frame = refreshed.frame;

    for (std::size_t index = 0; index < relations.joints.size(); ++index) {
        const auto& relation = relations.joints[index];
        const auto& row = projection.joints[index];
        if (row.positive_body != relation.positive.body_index ||
            row.negative_body != relation.negative.body_index) {
            throw std::runtime_error(
                "BODY feedback JOINT body identity mismatch");
        }
        const auto& positive =
            frame.bodies[relation.positive.body_index]
                .constraints.joints[relation.positive.sample_index];
        const auto& negative =
            frame.bodies[relation.negative.body_index]
                .constraints.joints[relation.negative.sample_index];
        if (positive.scalar_base != negative.scalar_base ||
            row.scalar_base != positive.scalar_base) {
            throw std::runtime_error(
                "BODY feedback JOINT scalar identity mismatch");
        }
        result.max_row_error = std::max(
            result.max_row_error,
            compare_vec3(
                row.positive_lever_arm,
                positive.position,
                tolerance,
                "BODY feedback JOINT positive row"));
        result.max_row_error = std::max(
            result.max_row_error,
            compare_vec3(
                row.negative_lever_arm,
                negative.position,
                tolerance,
                "BODY feedback JOINT negative row"));
    }

    for (std::size_t index = 0; index < relations.hinges.size(); ++index) {
        const auto& relation = relations.hinges[index];
        const auto& row = projection.hinges[index];
        if (row.positive_body != relation.positive.body_index ||
            row.negative_body != relation.negative.body_index) {
            throw std::runtime_error(
                "BODY feedback HINGE body identity mismatch");
        }
        const auto& positive =
            frame.bodies[relation.positive.body_index]
                .constraints.hinges[relation.positive.sample_index];
        const auto& negative =
            frame.bodies[relation.negative.body_index]
                .constraints.hinges[relation.negative.sample_index];
        if (positive.scalar_base != negative.scalar_base ||
            row.scalar_base != positive.scalar_base) {
            throw std::runtime_error(
                "BODY feedback HINGE scalar identity mismatch");
        }
        result.max_row_error = std::max(
            result.max_row_error,
            compare_vec3(
                row.positive_angular_row,
                positive.angular,
                tolerance,
                "BODY feedback HINGE positive angular row"));
        result.max_row_error = std::max(
            result.max_row_error,
            compare_vec3(
                row.positive_linear_row,
                positive.linear,
                tolerance,
                "BODY feedback HINGE positive linear row"));
        result.max_row_error = std::max(
            result.max_row_error,
            compare_vec3(
                row.negative_angular_row,
                negative.angular,
                tolerance,
                "BODY feedback HINGE negative angular row"));
        result.max_row_error = std::max(
            result.max_row_error,
            compare_vec3(
                row.negative_linear_row,
                negative.linear,
                tolerance,
                "BODY feedback HINGE negative linear row"));
    }

    for (std::size_t index = 0; index < relations.bars.size(); ++index) {
        const auto& relation = relations.bars[index];
        const auto& row = projection.bars[index];
        if (row.positive_body != relation.positive.body_index ||
            row.negative_body != relation.negative.body_index) {
            throw std::runtime_error(
                "BODY feedback BAR body identity mismatch");
        }
        const auto& positive =
            frame.bodies[relation.positive.body_index]
                .constraints.bars[relation.positive.sample_index];
        const auto& negative =
            frame.bodies[relation.negative.body_index]
                .constraints.bars[relation.negative.sample_index];
        if (positive.scalar_base != negative.scalar_base ||
            row.scalar_base != positive.scalar_base) {
            throw std::runtime_error(
                "BODY feedback BAR scalar identity mismatch");
        }
        result.max_row_error = std::max(
            result.max_row_error,
            compare_vec3(
                row.positive_lever_arm,
                positive.point,
                tolerance,
                "BODY feedback BAR positive row"));
        result.max_row_error = std::max(
            result.max_row_error,
            compare_vec3(
                row.negative_lever_arm,
                negative.point,
                tolerance,
                "BODY feedback BAR negative row"));
        result.max_row_error = std::max(
            result.max_row_error,
            compare_vec3(
                row.direction,
                positive.direction,
                tolerance,
                "BODY feedback BAR positive direction"));
        result.max_row_error = std::max(
            result.max_row_error,
            compare_vec3(
                row.direction,
                negative.direction,
                tolerance,
                "BODY feedback BAR negative direction"));
    }

    return result;
}

PreparedGeneratedBodyConstraintFrame apply_body_accumulator_feedback(
    const PreparedGeneratedBodyConstraintFrame& source,
    const std::vector<BodyAccumulatorState>& bodies) {

    if (source.bodies.size() != bodies.size()) {
        throw std::runtime_error(
            "BODY feedback state cardinality mismatch");
    }

    PreparedGeneratedBodyConstraintFrame result = source;
    for (std::size_t body = 0; body < bodies.size(); ++body) {
        for (double value : bodies[body].angular) {
            if (!std::isfinite(value)) {
                throw std::runtime_error(
                    "BODY feedback angular state contains non-finite value");
            }
        }
        for (double value : bodies[body].linear) {
            if (!std::isfinite(value)) {
                throw std::runtime_error(
                    "BODY feedback linear state contains non-finite value");
            }
        }
        result.bodies[body].constraints.preprojection.angular_state =
            bodies[body].angular;
        result.bodies[body].constraints.preprojection.linear_state =
            bodies[body].linear;
    }
    return result;
}

}  // namespace shift::runtime::physics
