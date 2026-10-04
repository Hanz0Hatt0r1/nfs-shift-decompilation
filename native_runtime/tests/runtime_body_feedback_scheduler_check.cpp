#include "runtime_state.hpp"

#include <cmath>
#include <cstdlib>
#include <iostream>
#include <stdexcept>
#include <utility>
#include <vector>

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
        body.row_indices = {0, 6, 12, 18, 24, 30};
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
    relations.bars.push_back(bar);
    return relations;
}

shift::runtime::physics::PreparedPostSolveBodyProjection make_projection(
    const shift::runtime::physics::PreparedGeneratedBodyConstraintFrame& source,
    const shift::runtime::physics::PreparedConstraintSampleRelationFrame& relations) {

    using namespace shift::runtime::physics;
    const auto refreshed = refresh_generated_body_constraint_frame(source, relations);
    PreparedPostSolveBodyProjection projection{};
    projection.solver_vector.assign(6, 0.0);
    projection.bodies.resize(2);
    projection.expected_bodies.resize(2);
    for (std::size_t body = 0; body < 2; ++body) {
        projection.bodies[body].angular =
            source.bodies[body].constraints.preprojection.angular_state;
        projection.bodies[body].linear =
            source.bodies[body].constraints.preprojection.linear_state;
        projection.expected_bodies[body] = projection.bodies[body];
    }

    const auto& joint = relations.joints[0];
    const auto& positive_joint =
        refreshed.frame.bodies[joint.positive.body_index]
            .constraints.joints[joint.positive.sample_index];
    const auto& negative_joint =
        refreshed.frame.bodies[joint.negative.body_index]
            .constraints.joints[joint.negative.sample_index];
    projection.joints.push_back({
        joint.positive.body_index,
        joint.negative.body_index,
        positive_joint.scalar_base,
        positive_joint.position,
        negative_joint.position,
    });

    const auto& hinge = relations.hinges[0];
    const auto& positive_hinge =
        refreshed.frame.bodies[hinge.positive.body_index]
            .constraints.hinges[hinge.positive.sample_index];
    const auto& negative_hinge =
        refreshed.frame.bodies[hinge.negative.body_index]
            .constraints.hinges[hinge.negative.sample_index];
    projection.hinges.push_back({
        hinge.positive.body_index,
        hinge.negative.body_index,
        positive_hinge.scalar_base,
        positive_hinge.angular,
        positive_hinge.linear,
        negative_hinge.angular,
        negative_hinge.linear,
    });

    const auto& bar = relations.bars[0];
    const auto& positive_bar =
        refreshed.frame.bodies[bar.positive.body_index]
            .constraints.bars[bar.positive.sample_index];
    const auto& negative_bar =
        refreshed.frame.bodies[bar.negative.body_index]
            .constraints.bars[bar.negative.sample_index];
    projection.bars.push_back({
        bar.positive.body_index,
        bar.negative.body_index,
        positive_bar.scalar_base,
        positive_bar.point,
        negative_bar.point,
        positive_bar.direction,
    });
    return projection;
}

shift::runtime::physics::PreparedBuiltinSolverFrame make_solver(
    const shift::runtime::physics::PreparedGeneratedBodyConstraintFrame& source,
    const shift::runtime::physics::PreparedConstraintSampleRelationFrame& relations) {

    using namespace shift::runtime::physics;
    const auto refreshed = refresh_generated_body_constraint_frame(source, relations);
    const auto generated = execute_prepared_generated_body_constraint_frame(
        refreshed.frame);
    PreparedBuiltinSolverFrame solver{};
    solver.matrix.assign(6, std::vector<double>(6, 0.0));
    for (std::size_t row = 0; row < 6; ++row) {
        for (std::size_t column = 0; column < 6; ++column) {
            solver.matrix[row][column] = generated.solver_matrix[row * 6 + column];
        }
    }
    solver.rhs = generated.solver_vector;
    solver.reset_nodes = {0, 1, 2, 3, 4, 5};
    auto graph = build_dense_solver_graph(6);
    solver.forward_records = std::move(graph.first);
    solver.reverse_records = std::move(graph.second);
    solver.expected_solution.assign(6, 0.0);
    return solver;
}

shift::runtime::physics::PreparedConstraintRelationResetFrame make_reset() {
    shift::runtime::physics::PreparedConstraintRelationResetFrame reset{};
    reset.joint_state_bit0 = {1u};
    reset.hinge_state_bit0 = {1u};
    reset.bar_state_bit0 = {1u};
    return reset;
}

void configure_feedback_state(shift::runtime::NativeRuntimeState& state) {
    auto source = make_frame();
    auto relations = make_relations();
    auto projection = make_projection(source, relations);
    auto solver = make_solver(source, relations);
    auto reset = make_reset();

    state.physics.workspace.configure(2, 1, 1);
    state.physics.participant_contract_ready = true;
    state.physics.participant_identity_join_proven = true;
    state.physics.participant_ready = true;
    state.body_feedback.configure(
        std::move(source),
        std::move(relations),
        std::move(reset),
        std::move(solver),
        std::move(projection));
}

}  // namespace

int main() {
    try {
        shift::runtime::NativeRuntimeState state{};
        configure_feedback_state(state);

        shift::runtime::VehicleControlIntent input{};
        input.throttle = true;
        state.fixed_step(input);
        input.throttle = false;
        input.steer_right = true;
        state.fixed_step(input);

        if (!state.body_feedback.enabled ||
            state.body_feedback.step_count != 2 ||
            state.physics.fixed_step != 2 ||
            state.physics.throttle_steps != 1 ||
            state.physics.steer_right_steps != 1 ||
            state.body_feedback.body_count != 2 ||
            state.body_feedback.scalar_count != 6 ||
            state.body_feedback.last_reset_node_count != 6 ||
            state.body_feedback.max_matrix_anchor_error != 0.0) {
            throw std::runtime_error(
                "runtime BODY feedback scheduler did not execute every fixed step");
        }

        shift::runtime::NativeRuntimeState bad{};
        bad.physics.workspace.configure(1, 1, 1);
        bad.physics.participant_identity_join_proven = true;
        bad.physics.participant_ready = true;
        bad.body_feedback.configure(
            make_frame(),
            make_relations(),
            make_reset(),
            make_solver(make_frame(), make_relations()),
            make_projection(make_frame(), make_relations()));
        bool rejected = false;
        try {
            bad.fixed_step({});
        } catch (const std::runtime_error&) {
            rejected = true;
        }
        if (!rejected) {
            throw std::runtime_error(
                "runtime BODY feedback scheduler accepted workspace mismatch");
        }

        // Phase 713: a failure after the camera swap and PhysicsTickBoundary
        // mutation must not commit a partial native tick.
        shift::runtime::NativeRuntimeState transactional{};
        configure_feedback_state(transactional);
        transactional.body_feedback.solver_topology.matrix.clear();
        shift::runtime::VehicleControlIntent failed_input{};
        failed_input.throttle = true;
        bool transactional_rejected = false;
        try {
            transactional.fixed_step(failed_input);
        } catch (const std::runtime_error&) {
            transactional_rejected = true;
        }
        if (!transactional_rejected ||
            transactional.physics.fixed_step != 0 ||
            transactional.physics.throttle_steps != 0 ||
            transactional.physics.last_input.throttle ||
            transactional.camera.active_index != 0 ||
            transactional.camera.update_in_progress ||
            transactional.camera.snapshot_count != 0 ||
            transactional.camera.native_update_count != 0 ||
            transactional.body_feedback.step_count != 0) {
            throw std::runtime_error(
                "failed native fixed step committed partial camera/physics state");
        }

        // Failed environment admission must remain retryable. In particular,
        // environment_checked must not latch true before all source contracts
        // have loaded successfully.
        if (setenv("SHIFT_NATIVE_BODY_FEEDBACK", "1", 1) != 0) {
            throw std::runtime_error("failed to set BODY feedback test environment");
        }
        unsetenv("SHIFT_NATIVE_BODY_FEEDBACK_SOLVER_FRAME");
        unsetenv("SHIFT_NATIVE_BODY_FEEDBACK_GBCF");
        unsetenv("SHIFT_NATIVE_BODY_FEEDBACK_CSRF");
        unsetenv("SHIFT_NATIVE_BODY_FEEDBACK_CRRF");
        unsetenv("SHIFT_NATIVE_BODY_FEEDBACK_SBPS");

        shift::runtime::NativeRuntimeState retryable{};
        bool environment_rejected = false;
        try {
            retryable.fixed_step({});
        } catch (const std::runtime_error&) {
            environment_rejected = true;
        }
        unsetenv("SHIFT_NATIVE_BODY_FEEDBACK");
        if (!environment_rejected ||
            retryable.body_feedback.environment_checked ||
            retryable.body_feedback.enabled ||
            retryable.physics.fixed_step != 0 ||
            retryable.camera.snapshot_count != 0) {
            throw std::runtime_error(
                "failed BODY feedback environment admission was not retry-safe");
        }

        // Phase 714: an admitted evidence snapshot must start from a completed
        // camera transaction. A recovered busy guard has no proven native
        // completion semantics and would otherwise block begin_swap forever.
        shift::runtime::CameraBufferRuntime camera{};
        camera.buffers[0].manager_mode = 17;
        camera.buffers[0].camera_id = 23;
        const bool busy_applied = camera.apply_evidence_snapshot(
            1u,
            true,
            99,
            7,
            42,
            3,
            2,
            1u);
        if (busy_applied || camera.active_index != 0u ||
            camera.update_in_progress || camera.snapshot_count != 0u ||
            camera.native_update_count != 0u ||
            camera.buffers[0].manager_mode != 17 ||
            camera.buffers[0].camera_id != 23) {
            throw std::runtime_error(
                "busy recovered camera evidence was not rejected transactionally");
        }

        const bool ready_applied = camera.apply_evidence_snapshot(
            1u,
            false,
            1,
            7,
            42,
            3,
            2,
            1u);
        if (!ready_applied || camera.active_index != 1u ||
            camera.update_in_progress || camera.active().manager_mode != 1 ||
            camera.active().camera_id != 42 ||
            camera.active().active_group != 3 ||
            camera.active().group_restore_value != 2 ||
            camera.active().active_buffer_sub_flag != 1u) {
            throw std::runtime_error(
                "completed recovered camera evidence was not admitted");
        }
        if (!camera.begin_swap()) {
            throw std::runtime_error(
                "admitted completed camera evidence could not start next native swap");
        }
        camera.complete_update();
        if (camera.update_in_progress || camera.snapshot_count != 1u ||
            camera.native_update_count != 1u) {
            throw std::runtime_error(
                "camera scheduler did not continue after completed evidence admission");
        }

        std::cout
            << "{\"format\":\"SHIFT.NativeBodyFeedbackScheduler/1\","
            << "\"ready\":true,"
            << "\"transactional_fixed_step\":true,"
            << "\"environment_retry_safe\":true,"
            << "\"busy_camera_evidence_rejected\":true,"
            << "\"completed_camera_evidence_continues\":true,"
            << "\"steps\":" << state.body_feedback.step_count << ","
            << "\"body_count\":" << state.body_feedback.body_count << ","
            << "\"scalar_count\":" << state.body_feedback.scalar_count << ","
            << "\"max_matrix_anchor_error\":"
            << state.body_feedback.max_matrix_anchor_error << "}\n";
        return 0;
    } catch (const std::exception& exc) {
        std::cerr << exc.what() << "\n";
        return 1;
    }
}
