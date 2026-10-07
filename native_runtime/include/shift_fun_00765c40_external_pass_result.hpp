#pragma once

#include "shift_fun_00765c40_load_terms.hpp"
#include "shift_fun_00765c40_query_input_boundary.hpp"

#include <optional>
#include <stdexcept>

namespace shift::runtime::physics {

inline constexpr const char* kFun00765c40ExternalPassResultFormat =
    "SHIFT.Fun00765c40ExternalPassResult/3";
inline constexpr const char* kFun00765c40ExternalPassInputFormat =
    "SHIFT.Fun00765c40ExternalPassInput/1";

// Native-owned inputs that must be supplied before the residual FUN_00765c40
// pass executes. cached_handle is always session-owned; nullopt is the exact
// source setup seed corresponding to HDVehicle+0x38dc = 0. world_position is
// present for the selected BMW domain closed by Phase739. Generic historical
// fixtures may leave it absent rather than pretending synthetic BODY state is
// the selected BMW session.
struct Fun00765c40ExternalPassInput {
    std::optional<CollisionQueryVector3d> world_position{};
    std::optional<std::uint64_t> cached_handle{};
};

// Residual external pass result. query_input remains as an auditable witness of
// what the external collision path actually consumed. Phase740 requires its
// cached_handle, and selected-BMW world_position when present, to equal the
// native-owned request. returned_cache_handle is the value written by retail
// FUN_00765c40 back to HDVehicle+0x38dc after FUN_007b0710 returns.
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
}

}  // namespace shift::runtime::physics
