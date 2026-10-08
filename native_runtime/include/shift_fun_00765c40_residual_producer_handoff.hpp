#pragma once

#include "shift_fun_007584f0_persistent_write_stage.hpp"
#include "shift_fun_00765c40_bounded_state_tail.hpp"
#include "shift_fun_00765c40_contact_array_sweep_stage.hpp"
#include "shift_fun_00765c40_contact_body_accumulation.hpp"
#include "shift_fun_00765c40_optional_body_accumulator_sweep.hpp"
#include "shift_fun_00765c40_wheel_pair_refresh_stage.hpp"
#include "shift_fun_00765c40_wheel_plane_refresh_stage.hpp"

#include <cstddef>
#include <cstdint>

namespace shift::runtime::physics {

inline constexpr const char* kFun00765c40ResidualProducerHandoffFormat =
    "SHIFT.Fun00765c40ResidualProducerHandoff/1";

// Pure-data handoff for source-computed values that the composed residual
// executor still cannot derive natively.  This deliberately does not contain:
// - current BODY bytes / selected world position (native-owned),
// - query cache or selected +0x38e8 fallback (native-owned),
// - lower scene-query behavior (explicit external seam),
// - wheel-job queue execution / +0x738 reads (separate scheduling seam),
// - initial BODY accumulator state (persistent native BODY state).
//
// Values remain opaque exact-width payloads where their producer arithmetic is
// unresolved.  Grouping them here does not promote formulas or semantic names.
struct Fun00765c40ResidualProducerHandoff {
    Fun00765c40WheelPlaneRefreshComputedInputs wheel_plane{};
    std::uint64_t wheel_state_source_bits = 0u;
    Fun007584f0ComputedInputs persistent_write{};
    Fun00765c40WheelPairComputedInputs wheel_pair{};
    Fun00765c40ContactArrayComputedInputs contact_array{};
    Fun00765c40ContactBodyAccumulationEntries contact_body_entries{};
    Fun00765c40BoundedStateTailComputedInputs bounded_state_tail{};
    Fun00765c40OptionalBodyAccumulatorSweepInput optional_body_sweep{};
};

inline constexpr std::size_t kFun00765c40ResidualProducerHandoffFamilyCount = 8u;

static_assert(kFun00765c40ResidualProducerHandoffFamilyCount == 8u);

}  // namespace shift::runtime::physics
