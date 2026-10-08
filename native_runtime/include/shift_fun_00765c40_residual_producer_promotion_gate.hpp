#pragma once

#include "shift_fun_00765c40_composed_residual_executor.hpp"
#include "shift_fun_00765c40_residual_producer_handoff.hpp"

#include <array>
#include <cstddef>
#include <stdexcept>
#include <string_view>
#include <utility>

namespace shift::runtime::physics {

inline constexpr const char* kFun00765c40ResidualProducerPromotionGateFormat =
    "SHIFT.Fun00765c40ResidualProducerPromotionGate/2";
inline constexpr const char* kFun00765c40HistoricalResidualProducerPromotionGateFormat =
    "SHIFT.Fun00765c40ResidualProducerPromotionGate/1";

// Structural authorization only. A non-empty contract id means the caller has
// independently established a source-backed ownership/equivalence contract for
// that family and names the contract it consumed. The receipt is not itself
// evidence; the named contract remains the authority. Empty ids fail closed.
struct Fun00765c40ResidualProducerProofMask {
    std::array<std::string_view, kFun00765c40ResidualProducerHandoffFamilyCount>
        proof_contract_ids{};
};

inline void set_fun_00765c40_residual_producer_family_proven(
    Fun00765c40ResidualProducerProofMask& proof,
    Fun00765c40ResidualProducerFamily family,
    std::string_view proof_contract_id) {
    if (proof_contract_id.empty()) {
        throw std::invalid_argument(
            "FUN_00765c40 residual producer proof contract id must be non-empty");
    }
    const std::size_t index = fun_00765c40_residual_producer_family_index(family);
    if (index >= proof.proof_contract_ids.size()) {
        throw std::out_of_range("FUN_00765c40 residual producer proof family index out of range");
    }
    proof.proof_contract_ids[index] = proof_contract_id;
}

inline std::string_view fun_00765c40_residual_producer_family_proof_contract(
    const Fun00765c40ResidualProducerProofMask& proof,
    Fun00765c40ResidualProducerFamily family) {
    const std::size_t index = fun_00765c40_residual_producer_family_index(family);
    if (index >= proof.proof_contract_ids.size()) {
        throw std::out_of_range("FUN_00765c40 residual producer proof family index out of range");
    }
    return proof.proof_contract_ids[index];
}

inline bool fun_00765c40_residual_producer_family_is_proven(
    const Fun00765c40ResidualProducerProofMask& proof,
    Fun00765c40ResidualProducerFamily family) {
    return !fun_00765c40_residual_producer_family_proof_contract(proof, family).empty();
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
                "FUN_00765c40 residual producer family present without named independent proof contract");
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
