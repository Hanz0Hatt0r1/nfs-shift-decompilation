#pragma once

#include "shift_fun_00765c40_load_terms.hpp"
#include "shift_fun_00765c40_query_input_boundary.hpp"

namespace shift::runtime::physics {

inline constexpr const char* kFun00765c40ExternalPassResultFormat =
    "SHIFT.Fun00765c40ExternalPassResult/2";

// This is deliberately an external *FUN_00765c40 pass* contract, not a
// "contact-factor" contract. FUN_00758ad0 contact-factor arithmetic is already
// native. Phase 726 additionally requires the external pass to expose the exact
// source-backed FUN_007b0710 query input it consumed; the producer/coordinate
// transform for world_position and the collision-provider implementation remain
// external. The four wheel+0x738 load terms stay the downstream payload consumed
// by FUN_00769ef0/FUN_007682c0.
struct Fun00765c40ExternalPassResult {
    Fun00765c40LoadTerms load_terms{};
    Fun00765c40QueryInputBoundary query_input{};
};

inline void validate_fun_00765c40_external_pass_result(
    const Fun00765c40ExternalPassResult& result) {
    validate_fun_00765c40_load_terms(result.load_terms);
    validate_fun_00765c40_query_input_boundary(result.query_input);
}

}  // namespace shift::runtime::physics
