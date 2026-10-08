#pragma once

#include "shift_fun_00765c40_composed_residual_executor.hpp"
#include "shift_fun_00765c40_residual_producer_handoff.hpp"

#include <array>
#include <cstddef>
#include <stdexcept>

namespace shift::runtime::physics {

inline constexpr const char* kFun00765c40ResidualProducerPromotionGateFormat =
    "SHIFT.Fun00765c40ResidualProducerPromotionGate/1";

// Structural authorization only. A true bit means the caller has independently
// established source-backed ownership/equivalence for that family. This mask is
// not itself evidence and defaults fail-closed to no authorized families.
struct Fun00765c40ResidualProducerProofMask {
    std::array<bool, kFun00765c40ResidualProducerHandoffFamilyCount>
        independently_proven{};
};

inline void set_fun_00765c40_residual_producer_family_proven(
    Fun00765c40ResidualProducerProofMask& proof,
    Fun00765c40ResidualProducerFamily family,
    bool proven = true) {
    const std::size_t index = fun_00765c40_residual_producer_family_index(family);
    if (index >= proof.independently_proven.size()) {
        throw std::out_of_range("FUN_00765c40 residual producer proof family index out of range");
    }
    proof.independently_proven[index] = proven;
}

inline bool fun_00765c40_residual_producer_family_is_proven(
    const Fun00765c40ResidualProducerProofMask& proof,
    Fun00765c40ResidualProducerFamily family) {
    const std::size_t index = fun_00765c40_residual_producer_family_index(family);
    if (index >= proof.independently_proven.size()) {
        throw std::out_of_range("FUN_00765c40 residual producer proof family index out of range");
    }
    return proof.independently_proven[index];
}

inline void validate_fun_00765c40_residual_producer_promotion(
    const Fun00765c40ResidualProducerHandoff& handoff,
    const Fun00765c40ResidualProducerProofMask& proof) {
    validate_fun_00765c40_residual_producer_handoff_known_invariants(handoff);

    constexpr std::array<Fun00765c40ResidualProducerFamily,
                         kFun00765c40ResidualProducerHandoffFamilyCount>
        families = {
            Fun00765c40ResidualProducerFamily::WheelPlane,
            Fun00765c40ResidualProducerFamily::WheelStateSource,
            Fun00765c40ResidualProducerFamily::PersistentWrite,
            Fun00765c40ResidualProducerFamily::WheelPair,
            Fun00765c40ResidualProducerFamily::ContactArray,
            Fun00765c40ResidualProducerFamily::ContactBody,
            Fun00765c40ResidualProducerFamily::BoundedStateTail,
            Fun00765c40ResidualProducerFamily::OptionalBodySweep,
        };

    for (const auto family : families) {
        if (fun_00765c40_residual_producer_family_is_present(handoff, family) &&
            !fun_00765c40_residual_producer_family_is_proven(proof, family)) {
            throw std::invalid_argument(
                "FUN_00765c40 residual producer family present without independent proof authorization");
        }
    }
}

inline Fun00765c40ComposedResidualInputs
apply_proven_fun_00765c40_residual_producer_handoff(
    Fun00765c40ComposedResidualInputs inputs,
    const Fun00765c40ResidualProducerHandoff& handoff,
    const Fun00765c40ResidualProducerProofMask& proof) {
    validate_fun_00765c40_residual_producer_promotion(handoff, proof);
    return apply_fun_00765c40_residual_producer_handoff(
        std::move(inputs), handoff);
}

static_assert(kFun00765c40ResidualProducerHandoffFamilyCount == 8u);

}  // namespace shift::runtime::physics
