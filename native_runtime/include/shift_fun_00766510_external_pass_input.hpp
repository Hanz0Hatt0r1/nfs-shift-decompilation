#pragma once

#include "shift_fun_00766510_query_scalar_handoff.hpp"

#include <cmath>
#include <optional>
#include <stdexcept>

namespace shift::runtime::physics {

inline constexpr const char* kFun00766510ExternalPassInputFormat =
    "SHIFT.Fun00766510ExternalPassInput/1";

// Session-facing input to the still-external remainder of FUN_00766510.
// Selected/native query paths carry the source-backed +0x38e0/+0x38e8 clamp
// handoff produced immediately after FUN_00765c40. Generic historical fixtures
// may leave it absent until they opt into the typed collision-output path.
struct Fun00766510ExternalPassInput {
    std::optional<Fun00766510QueryScalarHandoff> query_scalar_handoff{};
};

inline void validate_fun_00766510_external_pass_input(
    const Fun00766510ExternalPassInput& input) {
    if (!input.query_scalar_handoff.has_value()) {
        return;
    }
    const auto& handoff = *input.query_scalar_handoff;
    if (!std::isfinite(handoff.query_scalar) ||
        !std::isfinite(handoff.query_limit) ||
        !std::isfinite(handoff.clamped_query_scalar)) {
        throw std::invalid_argument(
            "FUN_00766510 query-scalar handoff must remain finite");
    }
    const double expected = clamp_fun_00766510_query_scalar(
        handoff.query_scalar,
        handoff.query_limit);
    if (handoff.clamped_query_scalar != expected) {
        throw std::invalid_argument(
            "FUN_00766510 query-scalar handoff clamp drift");
    }
}

}  // namespace shift::runtime::physics
