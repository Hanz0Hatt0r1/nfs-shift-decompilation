#pragma once

#include "shift_fun_00766510_query_scalar_handoff.hpp"
#include "shift_fun_00766510_selected_bmw_application_point.hpp"

#include <cmath>
#include <optional>
#include <stdexcept>

namespace shift::runtime::physics {

inline constexpr const char* kFun00766510ExternalPassInputFormat =
    "SHIFT.Fun00766510ExternalPassInput/1";

// Phase745 pre-call contract for the still-external remainder of FUN_00766510.
// Selected BMW execution must consume the already-native query-scalar handoff
// and the same-pass +0x38f0 application point. Generic historical fixtures do
// not pretend to own those selected-session values and therefore carry neither.
struct Fun00766510ExternalPassInput {
    bool selected_bmw_domain = false;
    std::optional<Fun00766510QueryScalarHandoff> query_scalar_handoff{};
    std::optional<BodyAccumulatorVector3d> primary_application_point{};
};

inline void validate_fun_00766510_external_pass_input(
    const Fun00766510ExternalPassInput& input) {
    if (!input.selected_bmw_domain) {
        if (input.query_scalar_handoff.has_value() ||
            input.primary_application_point.has_value()) {
            throw std::invalid_argument(
                "generic FUN_00766510 compatibility input cannot claim selected BMW ownership");
        }
        return;
    }

    if (!input.query_scalar_handoff.has_value() ||
        !input.primary_application_point.has_value()) {
        throw std::invalid_argument(
            "selected BMW FUN_00766510 input requires query handoff and +0x38f0 application point");
    }

    const auto& handoff = *input.query_scalar_handoff;
    if (!std::isfinite(handoff.query_scalar) ||
        !std::isfinite(handoff.query_limit) ||
        !std::isfinite(handoff.clamped_query_scalar)) {
        throw std::invalid_argument(
            "selected BMW FUN_00766510 query handoff must remain finite");
    }
    for (double value : *input.primary_application_point) {
        if (!std::isfinite(value)) {
            throw std::invalid_argument(
                "selected BMW FUN_00766510 +0x38f0 application point must remain finite");
        }
    }
}

inline Fun00766510ExternalPassInput
build_fun_00766510_selected_bmw_external_pass_input(
    const Fun00765c40QueryInputBoundary& query_input,
    const CollisionQueryOutput& query_output,
    const BodyAccumulatorVector3d& primary_application_point) {
    Fun00766510ExternalPassInput input{};
    input.selected_bmw_domain = true;
    input.query_scalar_handoff =
        execute_fun_00765c40_to_00766510_query_scalar_handoff(
            query_input,
            query_output);
    input.primary_application_point = primary_application_point;
    validate_fun_00766510_external_pass_input(input);
    return input;
}

}  // namespace shift::runtime::physics
