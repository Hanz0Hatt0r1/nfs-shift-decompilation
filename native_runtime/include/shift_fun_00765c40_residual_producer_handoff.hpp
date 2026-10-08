#pragma once

#include "shift_fun_007584f0_persistent_write_stage.hpp"
#include "shift_fun_00765c40_bounded_state_tail.hpp"
#include "shift_fun_00765c40_contact_array_sweep_stage.hpp"
#include "shift_fun_00765c40_contact_body_accumulation.hpp"
#include "shift_fun_00765c40_optional_body_accumulator_sweep.hpp"
#include "shift_fun_00765c40_wheel_pair_refresh_stage.hpp"
#include "shift_fun_00765c40_wheel_plane_refresh_stage.hpp"

#include <array>
#include <cstddef>
#include <cstdint>
#include <stdexcept>

namespace shift::runtime::physics {

inline constexpr const char* kFun00765c40ResidualProducerHandoffFormat =
    "SHIFT.Fun00765c40ResidualProducerHandoff/2";
inline constexpr const char* kFun00765c40HistoricalResidualProducerHandoffFormat =
    "SHIFT.Fun00765c40ResidualProducerHandoff/1";
inline constexpr std::size_t kFun00765c40ResidualProducerHandoffFamilyCount = 8u;

enum class Fun00765c40ResidualProducerFamily : std::size_t {
    WheelPlane = 0u,
    WheelStateSource = 1u,
    PersistentWrite = 2u,
    WheelPair = 3u,
    ContactArray = 4u,
    ContactBody = 5u,
    BoundedStateTail = 6u,
    OptionalBodySweep = 7u,
};

// Pure-data handoff for source-computed values that the composed residual
// executor still cannot derive natively.  This deliberately does not contain:
// - current BODY bytes / selected world position (native-owned),
// - query cache or selected +0x38e8 fallback (native-owned),
// - lower scene-query behavior (explicit external seam),
// - wheel-job queue execution / +0x738 reads (separate scheduling seam),
// - initial BODY accumulator state (persistent native BODY state).
//
// The first eight payload fields are the historical /1 prefix. /2 appends an
// explicit per-family presence mode so Process 2 can promote producer families
// independently. Historical /1 values remain source-compatible: when
// family_presence_explicit is false, all eight payload families are treated as
// present exactly as before.
struct Fun00765c40ResidualProducerHandoff {
    Fun00765c40WheelPlaneRefreshComputedInputs wheel_plane{};
    std::uint64_t wheel_state_source_bits = 0u;
    Fun007584f0ComputedInputs persistent_write{};
    Fun00765c40WheelPairComputedInputs wheel_pair{};
    Fun00765c40ContactArrayComputedInputs contact_array{};
    Fun00765c40ContactBodyAccumulationEntries contact_body_entries{};
    Fun00765c40BoundedStateTailComputedInputs bounded_state_tail{};
    Fun00765c40OptionalBodyAccumulatorSweepInput optional_body_sweep{};

    bool family_presence_explicit = false;
    std::array<bool, kFun00765c40ResidualProducerHandoffFamilyCount>
        family_present{};
};

inline constexpr std::size_t fun_00765c40_residual_producer_family_index(
    Fun00765c40ResidualProducerFamily family) {
    return static_cast<std::size_t>(family);
}

inline bool fun_00765c40_residual_producer_family_is_present(
    const Fun00765c40ResidualProducerHandoff& handoff,
    Fun00765c40ResidualProducerFamily family) {
    if (!handoff.family_presence_explicit) {
        return true;
    }
    const std::size_t index = fun_00765c40_residual_producer_family_index(family);
    if (index >= handoff.family_present.size()) {
        throw std::out_of_range("FUN_00765c40 residual producer family index out of range");
    }
    return handoff.family_present[index];
}

inline void set_fun_00765c40_residual_producer_family_present(
    Fun00765c40ResidualProducerHandoff& handoff,
    Fun00765c40ResidualProducerFamily family,
    bool present = true) {
    handoff.family_presence_explicit = true;
    const std::size_t index = fun_00765c40_residual_producer_family_index(family);
    if (index >= handoff.family_present.size()) {
        throw std::out_of_range("FUN_00765c40 residual producer family index out of range");
    }
    handoff.family_present[index] = present;
}

// Validate only invariants already owned by an underlying stage contract, and
// only for families the /2 witness declares present. Most producer fields
// intentionally remain opaque bit patterns or unresolved vectors, so this
// function must not add guessed range/semantic constraints.
inline void validate_fun_00765c40_residual_producer_handoff_known_invariants(
    const Fun00765c40ResidualProducerHandoff& handoff) {
    if (fun_00765c40_residual_producer_family_is_present(
            handoff,
            Fun00765c40ResidualProducerFamily::PersistentWrite)) {
        validate_fun_007584f0_computed_inputs(handoff.persistent_write);
    }
}

static_assert(kFun00765c40ResidualProducerHandoffFamilyCount == 8u);
static_assert(fun_00765c40_residual_producer_family_index(
                  Fun00765c40ResidualProducerFamily::OptionalBodySweep) == 7u);

}  // namespace shift::runtime::physics
