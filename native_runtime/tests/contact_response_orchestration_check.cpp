#include "shift_contact_response_orchestration.hpp"

#include <algorithm>
#include <cmath>
#include <iostream>
#include <limits>
#include <stdexcept>

namespace {

void require_close(
    double actual,
    double expected,
    double tolerance,
    const char* label,
    double& max_error) {
    const double error = std::abs(actual - expected);
    max_error = std::max(max_error, error);
    if (!std::isfinite(actual) || error > tolerance) {
        throw std::runtime_error(label);
    }
}

shift::runtime::physics::CollisionQueryOutput hit_output(double contact_height) {
    using namespace shift::runtime::physics;
    const auto query = build_fun_00765c40_collision_query_record(
        {0.0, 10.0, 0.0}, 1234u);
    CollisionSurfaceRecord surface{};
    surface.address_token = 1234u;
    surface.query_point = {0.0, 10.15, 0.0};
    surface.normal = {0.0, 1.0, 0.0};
    surface.contact_height = contact_height;
    surface.triangle_a = {0.0, 0.0, 0.0};
    surface.triangle_b = {1.0, 0.0, 0.0};
    surface.triangle_c = {0.0, 0.0, 1.0};
    return apply_fun_007b0710_collision_query_result(query, surface);
}

shift::runtime::physics::ContactResponseOrchestrationInput base_input() {
    using namespace shift::runtime::physics;
    ContactResponseOrchestrationInput input{};
    input.query_response.original_world_y = 10.0;
    input.query_response.fallback_and_query_limit = 4.0;
    input.query_response.query_output = hit_output(7.0);
    input.query_response.depth_slope = 2.0;
    input.query_response.base_offset = 1.0;
    input.query_response.directional_curve = {0.0, 0.0, 0.0, 0.0};
    input.query_response.tangent_x = 0.0;
    input.query_response.tangent_z = 1.0;
    input.query_response.body_frame = {
        1.0f, 0.0f, 0.0f,
        0.0f, 1.0f, 0.0f,
        0.0f, 0.0f, 1.0f,
    };
    input.query_response.body_source_vector = {-1.0, 2.0, 3.0};
    input.query_response.response_table.negative_or_zero = {{
        {{1.0, 0.0, 0.0}},
        {{0.0, 2.0, 0.0}},
        {{0.0, 0.0, 3.0}},
    }};
    input.query_response.response_table.positive = {{
        {{4.0, 0.0, 0.0}},
        {{0.0, 5.0, 0.0}},
        {{0.0, 0.0, 6.0}},
    }};
    input.query_response.response_table.component_scales = {1.0, 1.0, 1.0};

    input.body_transform.angular = {0.0, 0.0, 0.0};
    input.body_transform.body_position = {0.0, 0.0, 0.0};
    input.body_transform.translation = {5.0, 4.0, 1.0};
    input.aux_reference_point = {2.0, 3.0, 5.0};

    AuxContactRecord record{};
    record.active = true;
    record.point = {5.0, 4.0, 1.0};
    record.directional_curve = {0.0, 0.0, 0.0, 0.0};
    record.gain = 2.0;
    record.scale = 2.0;
    input.aux_records[0] = record;
    input.aux_records[1] = record;

    BodyAccumulatorState barrier{};
    barrier.angular = {1.0, 2.0, 3.0};
    barrier.linear = {4.0, 5.0, 6.0};
    input.body_accumulator_after_primary_application = barrier;
    return input;
}

}  // namespace

int main() {
    using namespace shift::runtime::physics;
    try {
        double max_error = 0.0;
        const auto input = base_input();
        const auto result = execute_fun_00766510_partial_contact_chain(input);

        require_close(result.query_response.caller_query_scalar, 3.0, 0.0,
                      "query scalar", max_error);
        require_close(result.query_response.response.clamped_query_scalar, 3.0, 0.0,
                      "clamped query scalar", max_error);
        require_close(result.query_response.response.response_gain, 7.0, 0.0,
                      "response gain", max_error);
        const double expected_response[3] = {1.0, 20.0, 54.0};
        for (std::size_t i = 0; i < 3u; ++i) {
            require_close(result.query_response.response.response_vector[i],
                          expected_response[i], 0.0,
                          "response vector", max_error);
        }

        const double expected_barrier_angular[3] = {1.0, 2.0, 3.0};
        const double expected_barrier_linear[3] = {4.0, 5.0, 6.0};
        const double expected_final_angular[3] = {193.0, -318.0, 323.0};
        const double expected_final_linear[3] = {4.0, 69.0, 70.0};
        if (result.aux_pair.applied_count != 2u) {
            throw std::runtime_error("auxiliary pair count mismatch");
        }
        for (std::size_t i = 0; i < 3u; ++i) {
            require_close(result.body_accumulator_at_primary_barrier.angular[i],
                          expected_barrier_angular[i], 0.0,
                          "barrier angular state", max_error);
            require_close(result.body_accumulator_at_primary_barrier.linear[i],
                          expected_barrier_linear[i], 0.0,
                          "barrier linear state", max_error);
            require_close(result.body_accumulator.angular[i],
                          expected_final_angular[i], 0.0,
                          "final angular state", max_error);
            require_close(result.body_accumulator.linear[i],
                          expected_final_linear[i], 0.0,
                          "final linear state", max_error);
        }

        // The composed result must match invoking the already-proven auxiliary
        // pair directly from the externally supplied post-primary state.
        AuxContactPairInput direct{};
        direct.body_frame = input.query_response.body_frame;
        direct.body_transform = input.body_transform;
        direct.body_accumulator = *input.body_accumulator_after_primary_application;
        direct.reference_point = input.aux_reference_point;
        direct.records = input.aux_records;
        const auto direct_result = execute_fun_00766510_aux_contact_pair(direct);
        for (std::size_t i = 0; i < 3u; ++i) {
            require_close(result.body_accumulator.angular[i],
                          direct_result.body_accumulator.angular[i], 0.0,
                          "direct aux angular parity", max_error);
            require_close(result.body_accumulator.linear[i],
                          direct_result.body_accumulator.linear[i], 0.0,
                          "direct aux linear parity", max_error);
        }

        bool missing_rejected = false;
        try {
            auto missing = base_input();
            missing.body_accumulator_after_primary_application.reset();
            (void)execute_fun_00766510_partial_contact_chain(missing);
        } catch (const std::invalid_argument&) {
            missing_rejected = true;
        }
        if (!missing_rejected) {
            throw std::runtime_error("missing primary-application state was accepted");
        }

        bool non_finite_rejected = false;
        try {
            auto invalid = base_input();
            invalid.body_accumulator_after_primary_application->angular[0] =
                std::numeric_limits<double>::infinity();
            (void)execute_fun_00766510_partial_contact_chain(invalid);
        } catch (const std::invalid_argument&) {
            non_finite_rejected = true;
        }
        if (!non_finite_rejected) {
            throw std::runtime_error("non-finite barrier state was accepted");
        }

        std::cout
            << "{\"format\":\"" << kNativeContactResponseOrchestrationFormat << "\","
            << "\"ready\":true,"
            << "\"function\":\"FUN_00766510\","
            << "\"query_response_before_barrier_proven\":true,"
            << "\"primary_application_external_required\":true,"
            << "\"missing_primary_state_rejected\":true,"
            << "\"non_finite_primary_state_rejected\":true,"
            << "\"aux_pair_after_barrier_proven\":true,"
            << "\"shared_body_frame_proven\":true,"
            << "\"invented_primary_application\":false,"
            << "\"full_fun_00766510_ported\":false,"
            << "\"runtime_scheduling_proven\":false,"
            << "\"max_absolute_error\":" << max_error << "}\n";
        return 0;
    } catch (const std::exception& exc) {
        std::cerr << exc.what() << '\n';
        return 1;
    }
}
