#include "shift_wheel_query_response_join.hpp"

#include <algorithm>
#include <cmath>
#include <iostream>
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

shift::runtime::physics::WheelQueryResponseJoinInput base_input() {
    using namespace shift::runtime::physics;

    WheelQueryResponseJoinInput input{};
    input.original_world_y = 10.0;
    input.fallback_and_query_limit = 4.0;
    input.depth_slope = 2.0;
    input.base_offset = 1.0;
    input.directional_curve = {0.0, 0.0, 0.0, 0.0};
    input.tangent_x = 0.0;
    input.tangent_z = 1.0;
    input.body_frame = {
        1.0f, 0.0f, 0.0f,
        0.0f, 1.0f, 0.0f,
        0.0f, 0.0f, 1.0f,
    };
    input.body_source_vector = {-1.0, 2.0, 3.0};

    input.response_table.negative_or_zero = {{
        {{1.0, 0.0, 0.0}},
        {{0.0, 2.0, 0.0}},
        {{0.0, 0.0, 3.0}},
    }};
    input.response_table.positive = {{
        {{4.0, 0.0, 0.0}},
        {{0.0, 5.0, 0.0}},
        {{0.0, 0.0, 6.0}},
    }};
    input.response_table.component_scales = {1.0, 1.0, 1.0};
    return input;
}

shift::runtime::physics::CollisionQueryOutput hit_output(double contact_height) {
    using namespace shift::runtime::physics;

    const auto query = build_fun_00765c40_collision_query_record(
        {0.0, 10.0, 0.0},
        1234u);
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

shift::runtime::physics::CollisionQueryOutput miss_output() {
    using namespace shift::runtime::physics;
    return apply_fun_007b0710_collision_query_result(
        build_fun_00765c40_collision_query_record({0.0, 10.0, 0.0}),
        std::nullopt);
}

}  // namespace

int main() {
    using namespace shift::runtime::physics;
    try {
        double max_error = 0.0;

        if (kWheelQueryScalarOffset != 0x38e0u ||
            kWheelQueryLimitOffset != 0x38e8u ||
            kWheelResponseGainOffset != 0x39d0u) {
            throw std::runtime_error("FUN_00765c40/FUN_00766510 state offsets mismatch");
        }

        auto hit_input = base_input();
        hit_input.query_output = hit_output(7.0);
        const auto hit =
            execute_fun_00765c40_to_00766510_response_join(hit_input);
        require_close(hit.caller_query_scalar, 3.0, 0.0, "hit +0x38e0 mismatch", max_error);
        require_close(hit.query_limit, 4.0, 0.0, "hit +0x38e8 mismatch", max_error);
        require_close(hit.response.query_scalar_input, 3.0, 0.0, "hit response input mismatch", max_error);
        require_close(hit.response.clamped_query_scalar, 3.0, 0.0, "hit clamp mismatch", max_error);
        require_close(hit.response.directional_factor, 1.0, 0.0, "hit directional factor mismatch", max_error);
        require_close(hit.response.response_gain, 7.0, 0.0, "hit response gain mismatch", max_error);

        const double expected_input[3] = {-1.0, 2.0, 3.0};
        const double expected_vector[3] = {1.0, 20.0, 54.0};
        const double expected_aux[3] = {1.0, -4.0, -9.0};
        for (std::size_t component = 0; component < 3u; ++component) {
            require_close(
                hit.response.response_input[component],
                expected_input[component],
                0.0,
                "joined response input mismatch",
                max_error);
            require_close(
                hit.response.response_vector[component],
                expected_vector[component],
                0.0,
                "joined response vector mismatch",
                max_error);
            require_close(
                hit.response.auxiliary_response[component],
                expected_aux[component],
                0.0,
                "joined auxiliary response mismatch",
                max_error);
        }

        auto miss_input = base_input();
        miss_input.query_output = miss_output();
        const auto miss =
            execute_fun_00765c40_to_00766510_response_join(miss_input);
        require_close(miss.caller_query_scalar, 4.0, 0.0, "miss fallback mismatch", max_error);
        require_close(miss.response.clamped_query_scalar, 4.0, 0.0, "miss clamp mismatch", max_error);
        require_close(miss.response.response_gain, 9.0, 0.0, "miss gain mismatch", max_error);

        auto upper_input = base_input();
        upper_input.query_output = hit_output(0.0);
        const auto upper =
            execute_fun_00765c40_to_00766510_response_join(upper_input);
        require_close(upper.caller_query_scalar, 10.0, 0.0, "upper raw scalar mismatch", max_error);
        require_close(upper.response.clamped_query_scalar, 4.0, 0.0, "upper clamp mismatch", max_error);
        require_close(upper.response.response_gain, 9.0, 0.0, "upper gain mismatch", max_error);

        auto lower_input = base_input();
        lower_input.query_output = hit_output(12.0);
        const auto lower =
            execute_fun_00765c40_to_00766510_response_join(lower_input);
        require_close(lower.caller_query_scalar, -2.0, 0.0, "lower raw scalar mismatch", max_error);
        require_close(lower.response.clamped_query_scalar, 0.0, 0.0, "lower clamp mismatch", max_error);
        require_close(lower.response.response_gain, 1.0, 0.0, "lower gain mismatch", max_error);

        std::cout
            << "{\"format\":\"SHIFT.NativeWheelQueryResponseJoin/1\","
            << "\"ready\":true,"
            << "\"producer\":\"FUN_00765c40\","
            << "\"consumer\":\"FUN_00766510\","
            << "\"query_scalar_offset\":\"0x38e0\","
            << "\"query_limit_offset\":\"0x38e8\","
            << "\"response_gain_offset\":\"0x39d0\","
            << "\"hit_join_proven\":true,"
            << "\"miss_fallback_join_proven\":true,"
            << "\"lower_upper_clamp_join_proven\":true,"
            << "\"collision_provider_implemented\":false,"
            << "\"runtime_scheduling_proven\":false,"
            << "\"max_absolute_error\":" << max_error << "}\n";
        return 0;
    } catch (const std::exception& exc) {
        std::cerr << exc.what() << "\n";
        return 1;
    }
}
