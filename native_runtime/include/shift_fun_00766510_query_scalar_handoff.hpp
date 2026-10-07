#pragma once

#include "shift_fun_00765c40_query_input_boundary.hpp"
#include "shift_wheel_contact_response.hpp"

#include <cmath>
#include <stdexcept>

namespace shift::runtime::physics {

inline constexpr const char* kFun00766510QueryScalarHandoffFormat =
    "SHIFT.Fun00766510QueryScalarHandoff/1";

// Source-backed handoff between FUN_00765c40 and the first scalar stage of
// FUN_00766510. No physical name/unit is inferred for either caller field.
struct Fun00766510QueryScalarHandoff {
    CollisionQueryOutput query_output{};
    double query_scalar = 0.0;          // HDVehicle+0x38e0 after FUN_00765c40
    double query_limit = 0.0;           // HDVehicle+0x38e8
    double clamped_query_scalar = 0.0;  // first FUN_00766510 clamp result
};

inline Fun00766510QueryScalarHandoff
execute_fun_00765c40_to_00766510_query_scalar_handoff(
    const Fun00765c40QueryInputBoundary& query_input,
    const CollisionQueryOutput& query_output) {
    validate_fun_00765c40_query_input_boundary(query_input);

    Fun00766510QueryScalarHandoff result{};
    result.query_output = query_output;
    result.query_scalar =
        project_fun_00765c40_query_input_scalar(query_input, query_output);
    result.query_limit = query_input.miss_fallback;
    result.clamped_query_scalar =
        clamp_fun_00766510_query_scalar(result.query_scalar, result.query_limit);

    if (!std::isfinite(result.query_scalar) ||
        !std::isfinite(result.query_limit) ||
        !std::isfinite(result.clamped_query_scalar)) {
        throw std::invalid_argument(
            "FUN_00765c40/FUN_00766510 query scalar handoff must remain finite");
    }
    return result;
}

}  // namespace shift::runtime::physics
