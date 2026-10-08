#pragma once

#include "shift_fun_00765c40_residual_pass_contract.hpp"

#include <cstdint>
#include <optional>

namespace shift::runtime::physics {

inline constexpr const char* kFun00765c40BoundedStateTailFormat =
    "SHIFT.Fun00765c40BoundedStateTail/1";

// P1.2 proves the four destinations and exact store widths/sites, but the
// branch predicate and three computed payloads are not yet closed strongly
// enough to reconstruct them. The caller therefore states whether the proven
// write block executed and, only then, supplies its source-computed payloads.
struct Fun00765c40BoundedStateTailComputedInputs {
    bool write_block_executed = false;
    std::uint64_t state_3668_bits = 0u;
    std::uint64_t state_3670_bits = 0u;
    std::uint32_t state_3678_bits = 0u;
};

struct Fun00765c40BoundedStateTailCommit {
    std::uint8_t flag_3660 = 1u;
    std::uint64_t state_3668_bits = 0u;
    std::uint64_t state_3670_bits = 0u;
    std::uint32_t state_3678_bits = 0u;
};

inline std::optional<Fun00765c40BoundedStateTailCommit>
materialize_fun_00765c40_bounded_state_tail(
    const Fun00765c40BoundedStateTailComputedInputs& computed) {
    if (!computed.write_block_executed) {
        return std::nullopt;
    }
    return Fun00765c40BoundedStateTailCommit{
        1u,
        computed.state_3668_bits,
        computed.state_3670_bits,
        computed.state_3678_bits,
    };
}

static_assert(kFun00765c40ContactNegativeFlagOffset == 0x3660u);
static_assert(kFun00765c40PeakStateOffset == 0x3668u);
static_assert(kFun00765c40PeakAuxOffset == 0x3670u);
static_assert(kFun00765c40PeakTagOffset == 0x3678u);

}  // namespace shift::runtime::physics
