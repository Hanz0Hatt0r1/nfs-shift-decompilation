#pragma once

#include "shift_body_accumulator_primitives.hpp"
#include "shift_fun_00765c40_residual_pass_contract.hpp"

#include <array>
#include <cstddef>
#include <cstdint>

namespace shift::runtime::physics {

inline constexpr const char* kFun00765c40OptionalBodyAccumulatorSweepFormat =
    "SHIFT.Fun00765c40OptionalBodyAccumulatorSweep/1";
inline constexpr std::size_t kFun00765c40OptionalBodyAccumulatorEntryCount = 4u;
inline constexpr std::uintptr_t kFun00765c40OptionalBodyAccumulatorCallSite =
    0x007664f2u;

struct Fun00765c40OptionalBodyAccumulatorEntry {
    BodyAccumulatorVector3d point_or_lever_arm{};
    BodyAccumulatorVector3d contribution{};
};

using Fun00765c40OptionalBodyAccumulatorEntries =
    std::array<Fun00765c40OptionalBodyAccumulatorEntry,
               kFun00765c40OptionalBodyAccumulatorEntryCount>;

// Process 1 proves a four-entry final sweep through FUN_007baa70 at the
// recovered loop call site, but does not promote the enabling predicate or
// the producer arithmetic for either vec3 argument. Keep those values as
// explicit source-side inputs while making the already-proven BODY mutation
// executable natively.
struct Fun00765c40OptionalBodyAccumulatorSweepInput {
    bool enabled = false;
    Fun00765c40OptionalBodyAccumulatorEntries entries{};
};

struct Fun00765c40OptionalBodyAccumulatorSweepResult {
    BodyAccumulatorState body{};
    std::size_t applied_entry_count = 0u;
    bool executed = false;
};

inline Fun00765c40OptionalBodyAccumulatorSweepResult
execute_fun_00765c40_optional_body_accumulator_sweep(
    const BodyAccumulatorState& initial_body,
    const Fun00765c40OptionalBodyAccumulatorSweepInput& input) {
    Fun00765c40OptionalBodyAccumulatorSweepResult result{};
    result.body = initial_body;
    if (!input.enabled) {
        return result;
    }

    for (const auto& entry : input.entries) {
        apply_fun_007baa70_body_accumulator(
            result.body,
            entry.point_or_lever_arm,
            entry.contribution);
        ++result.applied_entry_count;
    }
    result.executed = true;
    return result;
}

inline constexpr bool
fun_00765c40_optional_body_accumulator_is_final_residual_stage() {
    return kFun00765c40ResidualStageOrder.back() ==
           Fun00765c40ResidualStage::OptionalBodyAccumulatorSweep;
}

static_assert(fun_00765c40_optional_body_accumulator_is_final_residual_stage());
static_assert(kFun00765c40OptionalBodyAccumulatorEntryCount == 4u);
static_assert(kFun00765c40OptionalBodyAccumulatorCallSite == 0x007664f2u);

}  // namespace shift::runtime::physics
