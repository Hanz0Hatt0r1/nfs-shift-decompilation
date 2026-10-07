#pragma once

#include "shift_fun_00765c40_load_terms.hpp"
#include "shift_fun_00765c40_query_input_boundary.hpp"
#include "shift_fun_00765c40_selected_bmw_query_fallback.hpp"

#include <optional>
#include <stdexcept>

namespace shift::runtime::physics {

inline constexpr const char* kFun00765c40ExternalPassResultFormat =
    "SHIFT.Fun00765c40ExternalPassResult/3";
inline constexpr const char* kFun00765c40ExternalPassInputFormat =
    "SHIFT.Fun00765c40ExternalPassInput/2";

// Native-owned inputs supplied before the residual FUN_00765c40 pass executes.
// cached_handle is always session-owned. world_position is present only on the
// selected BMW path closed by Phase739. Its presence is also the selected-session
// identity tag for Phase741: selected_bmw_miss_fallback() then exposes the exact
// source-backed FUN_00756bb0 setup value derived from FRONTWING.FWMaxHeight.
// Generic historical fixtures leave world_position absent and keep their former
// compatibility fallback in the audit witness rather than masquerading as BMW.
struct Fun00765c40ExternalPassInput {
    std::optional<CollisionQueryVector3d> world_position{};
    std::optional<std::uint64_t> cached_handle{};

    std::optional<double> selected_bmw_miss_fallback() const {
        if (!world_position.has_value()) {
            return std::nullopt;
        }
        return selected_bmw_m3_e36_fun_00765c40_query_fallback();
    }
};

// Residual external pass result. query_input remains an auditable witness of
// what the external collision path actually consumed. Phase740 requires cache
// and selected-BMW world position to match the native-owned request. Phase741
// additionally requires selected-BMW +0x38e8 to match its native setup value.
// returned_cache_handle remains the value written by retail FUN_00765c40 back
// to HDVehicle+0x38dc after FUN_007b0710 returns.
struct Fun00765c40ExternalPassResult {
    Fun00765c40LoadTerms load_terms{};
    Fun00765c40QueryInputBoundary query_input{};
    std::optional<std::uint64_t> returned_cache_handle{};
};

inline void validate_fun_00765c40_external_pass_result(
    const Fun00765c40ExternalPassInput& input,
    const Fun00765c40ExternalPassResult& result) {
    validate_fun_00765c40_load_terms(result.load_terms);
    validate_fun_00765c40_query_input_boundary(result.query_input);

    if (result.query_input.cached_handle != input.cached_handle) {
        throw std::invalid_argument(
            "FUN_00765c40 residual provider did not consume native-owned cached handle");
    }
    if (input.world_position.has_value() &&
        result.query_input.world_position != *input.world_position) {
        throw std::invalid_argument(
            "FUN_00765c40 residual provider did not consume native-owned selected BMW world position");
    }
    const auto selected_fallback = input.selected_bmw_miss_fallback();
    if (selected_fallback.has_value() &&
        result.query_input.miss_fallback != *selected_fallback) {
        throw std::invalid_argument(
            "FUN_00765c40 residual provider did not consume native-owned selected BMW +0x38e8 fallback");
    }
}

}  // namespace shift::runtime::physics
