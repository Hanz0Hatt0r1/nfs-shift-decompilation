#pragma once

#include "shift_body_state_feedback.hpp"

#include <algorithm>
#include <cstdint>
#include <cstdlib>
#include <limits>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

namespace shift::runtime {

inline constexpr const char* kNativeBodyFeedbackSchedulerFormat =
    "SHIFT.NativeBodyFeedbackScheduler/1";

struct BodyFeedbackScheduler {
    using BodyState = physics::BodyAccumulatorState;

    bool environment_checked = false;
    bool enabled = false;
    std::uint64_t step_count = 0;
    // Native lineage counters only. Generation zero is the admitted seed state;
    // every successful feedback step consumes the currently committed generation
    // and commits exactly one successor generation. This does not claim retail
    // scheduling cadence or BODY pose integration.
    std::uint64_t body_state_generation = 0;
    std::uint64_t last_input_body_state_generation = 0;
    std::size_t body_count = 0;
    std::size_t scalar_count = 0;
    std::size_t last_reset_call_count = 0;
    std::size_t last_reset_node_count = 0;
    double max_matrix_anchor_error = 0.0;

    physics::PreparedGeneratedBodyConstraintFrame source{};
    physics::PreparedConstraintSampleRelationFrame relations{};
    physics::PreparedConstraintRelationResetFrame reset_state{};
    physics::PreparedBuiltinSolverFrame solver_topology{};
    physics::PreparedPostSolveBodyProjection projection{};
    std::vector<BodyState> bodies;
    std::vector<double> last_generated_rhs;
    std::vector<double> last_solved_vector;

    static std::string required_environment_path(const char* name) {
        const char* value = std::getenv(name);
        if (value == nullptr || value[0] == '\0') {
            throw std::runtime_error(
                std::string("native BODY feedback requires environment variable ") +
                name);
        }
        return value;
    }

    void configure(
        physics::PreparedGeneratedBodyConstraintFrame source_frame,
        physics::PreparedConstraintSampleRelationFrame relation_frame,
        physics::PreparedConstraintRelationResetFrame relation_reset,
        physics::PreparedBuiltinSolverFrame solver_frame,
        physics::PreparedPostSolveBodyProjection post_solve) {

        const auto contract = physics::verify_body_state_feedback_contract(
            source_frame,
            relation_frame,
            post_solve);
        if (source_frame.scalar_count == 0 ||
            solver_frame.matrix.size() != source_frame.scalar_count ||
            post_solve.solver_vector.size() != source_frame.scalar_count) {
            throw std::runtime_error(
                "native BODY feedback scheduler scalar cardinality mismatch");
        }

        source = std::move(source_frame);
        relations = std::move(relation_frame);
        reset_state = std::move(relation_reset);
        solver_topology = std::move(solver_frame);
        projection = std::move(post_solve);
        bodies = projection.bodies;
        body_count = contract.body_count;
        scalar_count = source.scalar_count;
        step_count = 0;
        body_state_generation = 0;
        last_input_body_state_generation = 0;
        last_reset_call_count = 0;
        last_reset_node_count = 0;
        max_matrix_anchor_error = 0.0;
        last_generated_rhs.clear();
        last_solved_vector.clear();
        environment_checked = true;
        enabled = true;
    }

    void initialize_from_environment() {
        if (environment_checked) {
            return;
        }

        const char* raw_enabled = std::getenv("SHIFT_NATIVE_BODY_FEEDBACK");
        if (raw_enabled == nullptr || raw_enabled[0] == '\0' ||
            std::string(raw_enabled) == "0") {
            environment_checked = true;
            return;
        }
        if (std::string(raw_enabled) != "1") {
            throw std::runtime_error(
                "SHIFT_NATIVE_BODY_FEEDBACK must be 0 or 1");
        }

        // Keep environment_checked false until every required source contract
        // has loaded and configure() has committed the ready scheduler. A
        // failed fixed step can therefore be retried after the evidence paths
        // are corrected instead of silently degrading to disabled feedback.
        auto solver = physics::load_prepared_builtin_solver_frame(
            required_environment_path(
                "SHIFT_NATIVE_BODY_FEEDBACK_SOLVER_FRAME"));
        auto generated = physics::load_prepared_generated_body_constraint_frame(
            required_environment_path(
                "SHIFT_NATIVE_BODY_FEEDBACK_GBCF"));
        auto relation_frame = physics::load_prepared_constraint_sample_relation_frame(
            required_environment_path(
                "SHIFT_NATIVE_BODY_FEEDBACK_CSRF"));
        auto relation_reset = physics::load_prepared_constraint_relation_reset_frame(
            required_environment_path(
                "SHIFT_NATIVE_BODY_FEEDBACK_CRRF"));
        auto post_solve = physics::load_prepared_post_solve_body_projection(
            required_environment_path(
                "SHIFT_NATIVE_BODY_FEEDBACK_SBPS"));

        configure(
            std::move(generated),
            std::move(relation_frame),
            std::move(relation_reset),
            std::move(solver),
            std::move(post_solve));
    }

    void validate_runtime_boundary(
        std::uint32_t runtime_body_count,
        std::uint32_t runtime_scalar_count,
        bool workspace_ready,
        bool participant_ready,
        bool participant_identity_join_proven) const {

        if (!enabled) {
            return;
        }
        if (!workspace_ready) {
            throw std::runtime_error(
                "native BODY feedback requires ready physics workspace");
        }
        if (!participant_ready || !participant_identity_join_proven) {
            throw std::runtime_error(
                "native BODY feedback requires ready participant identity");
        }
        if (body_count != runtime_body_count ||
            scalar_count != runtime_scalar_count ||
            bodies.size() != body_count) {
            throw std::runtime_error(
                "native BODY feedback scheduler/runtime workspace mismatch");
        }
        if (body_state_generation != step_count) {
            throw std::runtime_error(
                "native BODY feedback persistent state generation is stale");
        }
    }

    void fixed_step() {
        if (!enabled) {
            return;
        }
        if (body_state_generation != step_count) {
            throw std::runtime_error(
                "native BODY feedback persistent state generation is stale");
        }
        if (body_state_generation ==
            std::numeric_limits<std::uint64_t>::max()) {
            throw std::runtime_error(
                "native BODY feedback persistent state generation overflow");
        }

        const std::uint64_t input_generation = body_state_generation;
        const auto result = physics::execute_body_state_feedback_step(
            source,
            relations,
            reset_state,
            solver_topology,
            projection,
            bodies);

        // Commit only after the complete solver/post-solve result exists. The
        // next call receives this exact bodies vector as its current_bodies
        // argument and must observe the successor generation.
        bodies = result.bodies;
        last_generated_rhs = result.generated_rhs;
        last_solved_vector = result.solved_vector;
        last_reset_call_count = result.reset_call_count;
        last_reset_node_count = result.reset_node_count;
        max_matrix_anchor_error = std::max(
            max_matrix_anchor_error,
            result.max_matrix_anchor_error);
        last_input_body_state_generation = input_generation;
        body_state_generation = input_generation + 1u;
        step_count = body_state_generation;
    }
};

}  // namespace shift::runtime
