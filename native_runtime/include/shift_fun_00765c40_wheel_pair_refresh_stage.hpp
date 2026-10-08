#pragma once

#include "shift_fun_00765c40_residual_pass_contract.hpp"

#include <array>
#include <cstddef>
#include <cstdint>

namespace shift::runtime::physics {

inline constexpr const char* kFun00765c40WheelPairRefreshStageFormat =
    "SHIFT.Fun00765c40WheelPairRefreshStage/1";

inline constexpr std::size_t kFun00765c40WheelPairRefreshWheelCount = 4u;
inline constexpr std::size_t kFun00765c40WheelPairRefreshLaneCount = 2u;
inline constexpr std::size_t kFun00765c40WheelPairRefreshStride = 0x0a80u;
inline constexpr std::array<std::array<std::size_t, 2>, 4>
    kFun00765c40WheelPairRefreshOffsets{{
        {0x0ba0u, 0x0ba8u},
        {0x1620u, 0x1628u},
        {0x20a0u, 0x20a8u},
        {0x2b20u, 0x2b28u},
    }};

// P1.2 closes the exact eight qword destinations, but does not assign physical
// names or prove enough of the preceding x87 arithmetic for Process 2 to
// synthesize the values. Preserve the source-computed qword payloads bit-for-bit
// until that arithmetic is independently internalized.
struct Fun00765c40WheelPairComputedInputs {
    std::array<std::array<std::uint64_t, 2>, 4> qword_bits{};
};

struct Fun00765c40WheelPairRefreshState {
    std::array<std::array<std::uint64_t, 2>, 4> qword_bits{};
};

inline Fun00765c40WheelPairRefreshState
materialize_fun_00765c40_wheel_pair_refresh_stage(
    const Fun00765c40WheelPairComputedInputs& computed) {
    Fun00765c40WheelPairRefreshState state{};
    state.qword_bits = computed.qword_bits;
    return state;
}

inline constexpr bool fun_00765c40_wheel_pair_refresh_follows_positive_count() {
    return kFun00765c40ResidualStageOrder[7] ==
               Fun00765c40ResidualStage::PositiveLoadCountCommit &&
           kFun00765c40ResidualStageOrder[8] ==
               Fun00765c40ResidualStage::WheelPairStateRefresh;
}

static_assert(fun_00765c40_wheel_pair_refresh_follows_positive_count());
static_assert(kFun00765c40WheelPairRefreshOffsets[0][0] == 0x0ba0u);
static_assert(kFun00765c40WheelPairRefreshOffsets[3][1] == 0x2b28u);

}  // namespace shift::runtime::physics
