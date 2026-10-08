#pragma once

#include "shift_contact_outer_kernel.hpp"

#include <array>
#include <cstddef>
#include <cstdint>

namespace shift::runtime::physics {

inline constexpr const char* kFun007584f0InterpolationCallSeamFormat =
    "SHIFT.Fun007584f0InterpolationCallSeam/2";

inline constexpr std::uintptr_t kFun007584f0InterpolationHelper = 0x00783a30u;
inline constexpr std::uintptr_t kFun007584f0InterpolationCallSite = 0x007587efu;
inline constexpr std::uintptr_t kFun007584f0InterpolationStoreSite = 0x007587f4u;
inline constexpr std::size_t kFun007584f0InterpolationArgumentCount = 4u;
inline constexpr std::size_t kFun007584f0InterpolationDestinationOffset = 0x3420u;

struct Fun007584f0InterpolationArguments {
    // The caller-side semantic names remain unproven here, so preserve the
    // source argument order. The callee formula itself is already recovered by
    // the Phase 379/662 FUN_00783a30 contract.
    std::array<float, kFun007584f0InterpolationArgumentCount> values{};
};

struct Fun007584f0InterpolationCallResult {
    float value = 0.0f;
    std::size_t helper_call_count = 0u;
    std::size_t destination_offset = kFun007584f0InterpolationDestinationOffset;
};

inline Fun007584f0InterpolationCallResult
execute_fun_007584f0_interpolation_native(
    const Fun007584f0InterpolationArguments& arguments) {
    const double result = execute_fun_00783a30_distance_filter(
        static_cast<double>(arguments.values[0]),
        static_cast<double>(arguments.values[1]),
        static_cast<double>(arguments.values[2]),
        static_cast<double>(arguments.values[3]));

    return {
        static_cast<float>(result),
        1u,
        kFun007584f0InterpolationDestinationOffset,
    };
}

static_assert(kFun007584f0InterpolationHelper == 0x00783a30u);
static_assert(kFun007584f0InterpolationCallSite == 0x007587efu);
static_assert(kFun007584f0InterpolationStoreSite == 0x007587f4u);
static_assert(kFun007584f0InterpolationArgumentCount == 4u);
static_assert(kFun007584f0InterpolationDestinationOffset == 0x3420u);

}  // namespace shift::runtime::physics
