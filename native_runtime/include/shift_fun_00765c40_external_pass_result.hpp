#pragma once

#include "shift_fun_00765c40_load_terms.hpp"

namespace shift::runtime::physics {

inline constexpr const char* kFun00765c40ExternalPassResultFormat =
    "SHIFT.Fun00765c40ExternalPassResult/1";

// This is deliberately an external *FUN_00765c40 pass* contract, not a
// "contact-factor" contract. FUN_00758ad0 contact-factor arithmetic is already
// native; the still-unresolved FUN_00765c40 boundary includes collision/world
// position work and other source-visible side effects. The only downstream
// value currently proven and consumed by the selected session is the four
// wheel+0x738 load-term array captured after the anchor returns.
struct Fun00765c40ExternalPassResult {
    Fun00765c40LoadTerms load_terms{};
};

inline void validate_fun_00765c40_external_pass_result(
    const Fun00765c40ExternalPassResult& result) {
    validate_fun_00765c40_load_terms(result.load_terms);
}

}  // namespace shift::runtime::physics
