#pragma once

#include "shift_body_accumulator_primitives.hpp"
#include "shift_fun_00765c40_contact_array_sweep_stage.hpp"

#include <array>
#include <cstddef>
#include <cstdint>

namespace shift::runtime::physics {

inline constexpr const char* kFun00765c40ContactBodyAccumulationFormat =
    "SHIFT.Fun00765c40ContactBodyAccumulation/1";
inline constexpr std::uintptr_t kFun00765c40ContactBodyAccumulatorCallSite =
    0x00766365u;

struct Fun00765c40ContactBodyAccumulationEntry {
    bool apply = false;
    BodyAccumulatorVector3d point_or_lever_arm{};
    BodyAccumulatorVector3d contribution{};
};

using Fun00765c40ContactBodyAccumulationEntries =
    std::array<Fun00765c40ContactBodyAccumulationEntry,
               kFun00765c40ContactArraySlotCount>;

struct Fun00765c40ContactBodyAccumulationResult {
    BodyAccumulatorState body{};
    std::size_t applied_entry_count = 0u;
};

// The retail call surface proves that the twelve-slot contact sweep can call
// FUN_007baa70 on selected BODY0 at 0x00766365. The exact per-slot predicate
// and producer arithmetic for the two vec3 arguments are not promoted by the
// current proof. Preserve both as explicit source-side inputs while executing
// the already-proven BODY mutation natively and in slot order.
inline Fun00765c40ContactBodyAccumulationResult
execute_fun_00765c40_contact_body_accumulation(
    const BodyAccumulatorState& initial_body,
    const Fun00765c40ContactBodyAccumulationEntries& entries) {
    Fun00765c40ContactBodyAccumulationResult result{};
    result.body = initial_body;
    for (const auto& entry : entries) {
        if (!entry.apply) {
            continue;
        }
        apply_fun_007baa70_body_accumulator(
            result.body,
            entry.point_or_lever_arm,
            entry.contribution);
        ++result.applied_entry_count;
    }
    return result;
}

static_assert(kFun00765c40ContactArraySlotCount == 12u);
static_assert(kFun00765c40ContactBodyAccumulatorCallSite == 0x00766365u);

}  // namespace shift::runtime::physics
