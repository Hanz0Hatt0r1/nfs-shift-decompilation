#include "shift_wheel_query_response_join.hpp"

#include <cmath>
#include <stdexcept>
#include <string>

namespace shift::runtime::physics {
namespace {

void require_finite(double value, const char* label) {
    if (!std::isfinite(value)) {
        throw std::invalid_argument(std::string(label) + " must be finite");
    }
}

}  // namespace

WheelQueryResponseJoinResult execute_fun_00765c40_to_00766510_response_join(
    const WheelQueryResponseJoinInput& input) {

    require_finite(input.original_world_y, "FUN_00765c40 original world Y");
    require_finite(
        input.fallback_and_query_limit,
        "FUN_00765c40/FUN_00766510 +0x38e8 value");

    WheelQueryResponseJoinResult result{};
    result.caller_query_scalar =
        project_fun_00765c40_query_scalar(
            input.original_world_y,
            input.query_output,
            input.fallback_and_query_limit);
    result.query_limit = input.fallback_and_query_limit;

    result.response =
        evaluate_fun_00766510_contact_response_from_body_source(
            result.caller_query_scalar,
            result.query_limit,
            input.depth_slope,
            input.base_offset,
            input.directional_curve,
            input.response_table,
            input.tangent_x,
            input.tangent_z,
            input.body_frame,
            input.body_source_vector);

    if (result.response.query_scalar_input != result.caller_query_scalar) {
        throw std::runtime_error(
            "FUN_00765c40 -> FUN_00766510 query-scalar join mismatch");
    }
    return result;
}

}  // namespace shift::runtime::physics
