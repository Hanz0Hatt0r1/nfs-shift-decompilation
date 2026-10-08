#pragma once

#include "shift_fun_00765c40_residual_pass_contract.hpp"

#include <array>
#include <cstddef>
#include <cstdint>

namespace shift::runtime::physics {

inline constexpr const char* kFun00765c40WheelPlaneRefreshStageFormat =
    "SHIFT.Fun00765c40WheelPlaneRefreshStage/1";
inline constexpr std::size_t kFun00765c40WheelPlaneRefreshCount = 4u;
inline constexpr std::size_t kFun00765c40WheelPlaneRefreshBaseOffset = 0x0a70u;
inline constexpr std::size_t kFun00765c40WheelPlaneRefreshStride = 0x0a80u;

inline constexpr std::array<std::size_t, kFun00765c40WheelPlaneRefreshCount>
make_fun_00765c40_wheel_plane_refresh_offsets() {
    std::array<std::size_t, kFun00765c40WheelPlaneRefreshCount> offsets{};
    for (std::size_t wheel = 0; wheel < offsets.size(); ++wheel) {
        offsets[wheel] = kFun00765c40WheelPlaneRefreshBaseOffset +
                         wheel * kFun00765c40WheelPlaneRefreshStride;
    }
    return offsets;
}

inline constexpr auto kFun00765c40WheelPlaneRefreshOffsets =
    make_fun_00765c40_wheel_plane_refresh_offsets();

// The machine body proves four qword stores at the recovered wheel-relative
// destinations, but current ownership does not prove the source arithmetic.
// Keep the source values opaque and exact-width while making the destination
// geometry and retail ordering native-owned.
using Fun00765c40WheelPlaneRefreshComputedInputs =
    std::array<std::uint64_t, kFun00765c40WheelPlaneRefreshCount>;

struct Fun00765c40WheelPlaneRefreshState {
    std::array<std::uint64_t, kFun00765c40WheelPlaneRefreshCount>
        qword_bits{};
};

inline Fun00765c40WheelPlaneRefreshState
materialize_fun_00765c40_wheel_plane_refresh_stage(
    const Fun00765c40WheelPlaneRefreshComputedInputs& computed) {
    return {computed};
}

inline constexpr bool fun_00765c40_wheel_plane_refresh_is_first_stage() {
    return kFun00765c40ResidualStageOrder.front() ==
           Fun00765c40ResidualStage::WheelPlaneStateRefresh;
}

static_assert(fun_00765c40_wheel_plane_refresh_is_first_stage());
static_assert(kFun00765c40WheelPlaneRefreshOffsets[0] == 0x0a70u);
static_assert(kFun00765c40WheelPlaneRefreshOffsets[1] == 0x14f0u);
static_assert(kFun00765c40WheelPlaneRefreshOffsets[2] == 0x1f70u);
static_assert(kFun00765c40WheelPlaneRefreshOffsets[3] == 0x29f0u);

}  // namespace shift::runtime::physics
