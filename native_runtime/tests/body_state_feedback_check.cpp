#include "shift_body_state_feedback.hpp"

#include <cmath>
#include <iostream>
#include <stdexcept>

namespace {

shift::runtime::physics::PreparedGeneratedBodyConstraintFrame make_frame() {
    using namespace shift::runtime::physics;

    PreparedGeneratedBodyConstraintFrame frame{};
    frame.scalar_count = 6;
    frame.matrix_double_count = 36;
    frame.bodies.resize(2);

    for (std::size_t index = 0; index < frame.bodies.size(); ++index) {
        auto& body = frame.bodies[index];
        body.body_index = index;
        body.matrix_double_count = 36;
        body.provider_present = false;
        body.row_indices = {0, 1, 2, 3, 4, 5};
        body.constraints.scalar_count = 6;
        body.constraints.body_position = {
            static_cast<double>(index), 0.0, 0.0};
        body.constraints.preprojection.body_frame = {
            1.0f, 0.0f, 0.0f,
            0.0f, 1.0f, 0.0f,
            0.0f, 0.0f, 1.0f,
        };
        body.constraints.preprojection.angular_state = {
            1.0 + index, 2.0 + index, 3.0 + index};
        body.constraints.preprojection.linear_state = {
            4.0 + index, 5.0 + index, 6.0 + index};
        body.constraints.preprojection.inverse_scalar = 1.0;
        body.constraints.body_tensor = {{
            {{1.0, 0.0, 0.0}},
            {{0.0, 1.0, 0.0}},
            {{0.0, 0.0, 1.0}},
        }};
        body.constraints.scales.linear_scale = 1.0;
        body.constraints.scales.quadratic_scale = 1.0;

        PreparedJointSample joint{};
        joint.scalar_base = 0;
        joint.side_flag = index == 0 ? 1u : 0u;
        body.constraints.joints.push_back(joint);

        PreparedHingeSample hinge{};
        hinge.scalar_base = 3;
        hinge.side_flag = index == 0 ? 1u : 0u;
        hinge.position = {0.0, 1.0, 0.0};
        body.constraints.hinges.push_back(hinge);

        PreparedBarSample bar{};
        bar.scalar_base = 5;
        bar.side_flag = index == 0 ? 1u : 0u;
        bar.side_bias = 0.0;
        body.constraints.bars.push_back(bar);
    }
    return frame;
}

shift::runtime::physics::PreparedConstraintSampleRelationFrame make_relations() {
    using namespace shift::runtime::physics;

    PreparedConstraintSampleRelationFrame relations{};
    relations.body_count = 2;

    PreparedJointConstraintRelation joint{};
    joint.positive = {0, 0};
    joint.negative = {1, 0};
    joint.positive_local_position = {1.0, 2.0, 3.0};
    joint.negative_local_position = {-1.0, -2.0, -3.0};
    relations.joints.push_back(joint);

    PreparedHingeConstraintRelation hinge{};
    hinge.positive = {0, 0};
    hinge.negative = {1, 0};
    hinge.positive_angular_local = {1.0, 0.0, 0.0};
    hinge.positive_linear_local = {0.0, 1.0, 0.0};
    relations.hinges.push_back(hinge);

    PreparedBarConstraintRelation bar{};
    bar.positive = {0, 0};
    bar.negative = {1, 0};
    bar.positive_local_point = {0.0, 0.0, 0.0};
    bar.negative_local_point = {0.0, 0.0, 0.0};
    relations.bars.push_back(bar);

    return relations;
}

shift::runtime::physics::PreparedPostSolveBodyProjection make_projection(
    const shift::runtime::physics::PreparedGeneratedBodyConstraintFrame& source,
    const shift::runtime::physics::PreparedConstraintSampleRelationFrame& relations) {

    using namespace shift::runtime::physics;
    const auto refreshed =
        refresh_generated_body_constraint_frame(source, relations);

    PreparedPostSolveBodyProjection projection{};
    projection.solver_vector.assign(6, 0.0);
    projection.bodies.resize(source.bodies.size());
    projection.expected_bodies.resize(source.bodies.size());
    for (std::size_t body = 0; body < source.bodies.size(); ++body) {
        projection.bodies[body].angular =
            source.bodies[body].constraints.preprojection.angular_state;
        projection.bodies[body].linear =
            source.bodies[body].constraints.preprojection.linear_state;
        projection.expected_bodies[body] = projection.bodies[body];
    }

    const auto& joint_relation = relations.joints[0];
    const auto& positive_joint =
        refreshed.frame.bodies[joint_relation.positive.body_index]
            .constraints.joints[joint_relation.positive.sample_index];
    const auto& negative_joint =
        refreshed.frame.bodies[joint_relation.negative.body_index]
            .constraints.joints[joint_relation.negative.sample_index];
    projection.joints.push_back({
        joint_relation.positive.body_index,
        joint_relation.negative.body_index,
        positive_joint.scalar_base,
        positive_joint.position,
        negative_joint.position,
    });

    const auto& hinge_relation = relations.hinges[0];
    const auto& positive_hinge =
        refreshed.frame.bodies[hinge_relation.positive.body_index]
            .constraints.hinges[hinge_relation.positive.sample_index];
    const auto& negative_hinge =
        refreshed.frame.bodies[hinge_relation.negative.body_index]
            .constraints.hinges[hinge_relation.negative.sample_index];
    projection.hinges.push_back({
        hinge_relation.positive.body_index,
        hinge_relation.negative.body_index,
        positive_hinge.scalar_base,
        positive_hinge.angular,
        positive_hinge.linear,
        negative_hinge.angular,
        negative_hinge.linear,
    });

    const auto& bar_relation = relations.bars[0];
    const auto& positive_bar =
        refreshed.frame.bodies[bar_relation.positive.body_index]
            .constraints.bars[bar_relation.positive.sample_index];
    const auto& negative_bar =
        refreshed.frame.bodies[bar_relation.negative.body_index]
            .constraints.bars[bar_relation.negative.sample_index];
    projection.bars.push_back({
        bar_relation.positive.body_index,
        bar_relation.negative.body_index,
        positive_bar.scalar_base,
        positive_bar.point,
        negative_bar.point,
        positive_bar.direction,
    });

    return projection;
}

shift::runtime::physics::PreparedBuiltinSolverFrame make_solver_topology(
    const shift::runtime::physics::PreparedGeneratedBodyConstraintFrame& source,
    const shift::runtime::physics::PreparedConstraintSampleRelationFrame& relations) {

    using namespace shift::runtime::physics;
    const auto refreshed =
        refresh_generated_body_constraint_frame(source, relations);
    const auto generated =
        execute_prepared_generated_body_constraint_frame(refreshed.frame);

    PreparedBuiltinSolverFrame frame{};
    frame.matrix.assign(6, std::vector<double>(6, 0.0));
    for (std::size_t row = 0; row < 6; ++row) {
        for (std::size_t column = 0; column < 6; ++column) {
            frame.matrix[row][column] =
                generated.solver_matrix[row * 6 + column];
        }
    }
    frame.rhs = generated.solver_vector;
    frame.reset_nodes = {0, 1, 2, 3, 4, 5};
    auto graph = build_dense_solver_graph(6);
    frame.forward_records = std::move(graph.first);
    frame.reverse_records = std::move(graph.second);
    frame.expected_solution.assign(6, 0.0);
    return frame;
}

shift::runtime::physics::PreparedConstraintRelationResetFrame make_reset_state() {
    using namespace shift::runtime::physics;
    PreparedConstraintRelationResetFrame reset{};
    reset.joint_state_bit0 = {1u};
    reset.hinge_state_bit0 = {1u};
    reset.bar_state_bit0 = {1u};
    return reset;
}

}  // namespace

int main() {
    using namespace shift::runtime::physics;
    try {
        const auto source = make_frame();
        const auto relations = make_relations();
        auto projection = make_projection(source, relations);

        const auto joined = verify_body_state_feedback_contract(
            source, relations, projection);
        if (joined.body_count != 2 ||
            joined.joint_relation_count != 1 ||
            joined.hinge_relation_count != 1 ||
            joined.bar_relation_count != 1 ||
            joined.max_seed_error != 0.0 ||
            joined.max_row_error != 0.0) {
            throw std::runtime_error(
                "BODY feedback contract did not close exactly");
        }

        std::vector<BodyAccumulatorState> feedback = projection.bodies;
        feedback[0].angular[0] += 10.0;
        feedback[1].linear[2] -= 4.0;
        const auto fed = apply_body_accumulator_feedback(source, feedback);
        if (fed.bodies[0].constraints.preprojection.angular_state[0] !=
                feedback[0].angular[0] ||
            fed.bodies[1].constraints.preprojection.linear_state[2] !=
                feedback[1].linear[2]) {
            throw std::runtime_error(
                "BODY feedback did not reach next preprojection state");
        }

        const std::vector<double> dynamic_solution = {
            1.0, 2.0, 3.0, 4.0, 5.0, 6.0};
        const auto next = apply_post_solve_body_projection_rows(
            projection,
            dynamic_solution,
            projection.bodies);
        if (next.size() != 2) {
            throw std::runtime_error(
                "post-solve row kernel BODY count mismatch");
        }
        for (std::size_t component = 0; component < 3; ++component) {
            const double before =
                projection.bodies[0].linear[component] +
                projection.bodies[1].linear[component];
            const double after =
                next[0].linear[component] +
                next[1].linear[component];
            if (std::abs(after - before) > 1e-12) {
                throw std::runtime_error(
                    "post-solve row kernel broke paired linear conservation");
            }
        }

        const auto solver_topology =
            make_solver_topology(source, relations);
        const auto reset_state = make_reset_state();
        const auto first_step = execute_body_state_feedback_step(
            source,
            relations,
            reset_state,
            solver_topology,
            projection,
            projection.bodies);
        if (first_step.reset_call_count != 6 ||
            first_step.reset_node_count != 6 ||
            first_step.max_matrix_anchor_error != 0.0 ||
            first_step.solved_vector.size() != 6 ||
            first_step.bodies.size() != 2) {
            throw std::runtime_error(
                "dynamic BODY feedback step did not close full solver domain");
        }
        for (double value : first_step.solved_vector) {
            if (std::abs(value) > 1e-12) {
                throw std::runtime_error(
                    "all-reset dynamic BODY feedback solution must be zero");
            }
        }

        auto changed_bodies = projection.bodies;
        changed_bodies[0].angular[1] += 7.0;
        changed_bodies[1].linear[0] -= 3.0;
        const auto changed_step = execute_body_state_feedback_step(
            source,
            relations,
            reset_state,
            solver_topology,
            projection,
            changed_bodies);
        if (changed_step.max_matrix_anchor_error != 0.0) {
            throw std::runtime_error(
                "BODY state feedback unexpectedly changed solver matrix");
        }
        for (std::size_t body = 0; body < changed_bodies.size(); ++body) {
            for (std::size_t component = 0; component < 3; ++component) {
                if (std::abs(
                        changed_step.bodies[body].angular[component] -
                        changed_bodies[body].angular[component]) > 1e-12 ||
                    std::abs(
                        changed_step.bodies[body].linear[component] -
                        changed_bodies[body].linear[component]) > 1e-12) {
                    throw std::runtime_error(
                        "zero solved vector changed persistent BODY state");
                }
            }
        }

        auto bad_topology = solver_topology;
        bad_topology.matrix[0][0] += 0.5;
        bool matrix_rejected = false;
        try {
            (void)execute_body_state_feedback_step(
                source,
                relations,
                reset_state,
                bad_topology,
                projection,
                projection.bodies);
        } catch (const std::runtime_error&) {
            matrix_rejected = true;
        }
        if (!matrix_rejected) {
            throw std::runtime_error(
                "dynamic BODY feedback matrix-anchor mismatch was not rejected");
        }

        auto bad_projection = projection;
        bad_projection.joints[0].positive_lever_arm[0] += 1.0;
        bool rejected = false;
        try {
            (void)verify_body_state_feedback_contract(
                source, relations, bad_projection);
        } catch (const std::runtime_error&) {
            rejected = true;
        }
        if (!rejected) {
            throw std::runtime_error(
                "BODY feedback row mismatch was not rejected");
        }

        std::cout
            << "{\"format\":\"SHIFT.NativeBodyStateFeedbackStep/1\","
            << "\"ready\":true,"
            << "\"body_count\":" << joined.body_count << ","
            << "\"reset_node_count\":" << first_step.reset_node_count << ","
            << "\"max_seed_error\":" << joined.max_seed_error << ","
            << "\"max_row_error\":" << joined.max_row_error << ","
            << "\"max_matrix_anchor_error\":"
            << first_step.max_matrix_anchor_error << "}\n";
        return 0;
    } catch (const std::exception& exc) {
        std::cerr << exc.what() << "\n";
        return 1;
    }
}
