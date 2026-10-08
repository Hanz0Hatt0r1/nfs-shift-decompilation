#include "shift_fun_00765c40_residual_producer_promotion_gate.hpp"

#include <array>
#include <cstdint>
#include <iostream>
#include <stdexcept>
#include <string_view>

namespace {
using namespace shift::runtime::physics;

void require(bool condition, const char* message) {
    if (!condition) {
        throw std::runtime_error(message);
    }
}
}  // namespace

int main() {
    try {
        Fun00765c40ComposedResidualInputs base{};
        base.wheel_state_source_bits = 0x1111222233334444ull;
        base.wheel_plane = {0x10u, 0x20u, 0x30u, 0x40u};
        base.persistent_write.positive_branch_values = {1.0, 2.0};
        base.persistent_write.interpolation_result = 3.0f;

        Fun00765c40ResidualProducerHandoff selective{};
        selective.family_presence_explicit = true;
        selective.family_present.fill(false);
        selective.wheel_state_source_bits = 0xaaaabbbbccccddddull;
        set_fun_00765c40_residual_producer_family_present(
            selective,
            Fun00765c40ResidualProducerFamily::WheelStateSource);

        Fun00765c40ResidualProducerProofMask proof{};
        bool unproven_rejected = false;
        try {
            (void)apply_proven_fun_00765c40_residual_producer_handoff(
                base, selective, proof);
        } catch (const std::invalid_argument&) {
            unproven_rejected = true;
        }
        require(unproven_rejected,
                "present residual producer family passed without named independent proof");

        bool empty_contract_rejected = false;
        try {
            set_fun_00765c40_residual_producer_family_proven(
                proof,
                Fun00765c40ResidualProducerFamily::WheelStateSource,
                std::string_view{});
        } catch (const std::invalid_argument&) {
            empty_contract_rejected = true;
        }
        require(empty_contract_rejected,
                "producer proof authorization accepted an empty contract id");

        constexpr std::string_view kWheelStateTestProof =
            "TEST.Fun00765c40WheelStateSourceProof/1";
        set_fun_00765c40_residual_producer_family_proven(
            proof,
            Fun00765c40ResidualProducerFamily::WheelStateSource,
            kWheelStateTestProof);
        require(
            fun_00765c40_residual_producer_family_proof_contract(
                proof,
                Fun00765c40ResidualProducerFamily::WheelStateSource) ==
                kWheelStateTestProof,
            "producer proof receipt lost contract id");
        const auto promoted =
            apply_proven_fun_00765c40_residual_producer_handoff(
                base, selective, proof);
        require(promoted.wheel_state_source_bits ==
                    selective.wheel_state_source_bits,
                "proven selective family did not promote");
        require(promoted.wheel_plane == base.wheel_plane &&
                    promoted.persistent_write.positive_branch_values ==
                        base.persistent_write.positive_branch_values,
                "promotion gate overwrote absent unresolved family");

        Fun00765c40ResidualProducerHandoff legacy{};
        legacy.wheel_state_source_bits = 0x55u;
        legacy.persistent_write.positive_branch_values = {4.0, 5.0};
        legacy.persistent_write.interpolation_result = 6.0f;
        require(!legacy.family_presence_explicit,
                "legacy handoff did not preserve all-family mode");

        bool partial_legacy_proof_rejected = false;
        try {
            (void)apply_proven_fun_00765c40_residual_producer_handoff(
                base, legacy, proof);
        } catch (const std::invalid_argument&) {
            partial_legacy_proof_rejected = true;
        }
        require(partial_legacy_proof_rejected,
                "legacy all-family witness accepted partial proof receipts");

        Fun00765c40ResidualProducerProofMask all_proven{};
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
            set_fun_00765c40_residual_producer_family_proven(
                all_proven,
                family,
                "TEST.Fun00765c40ProducerProof/1");
        }
        const auto legacy_promoted =
            apply_proven_fun_00765c40_residual_producer_handoff(
                base, legacy, all_proven);
        require(legacy_promoted.wheel_state_source_bits == 0x55u &&
                    legacy_promoted.persistent_write.positive_branch_values[1] == 5.0,
                "fully proven legacy witness did not preserve /1 behavior");

        Fun00765c40ResidualProducerHandoff empty_selective{};
        empty_selective.family_presence_explicit = true;
        empty_selective.family_present.fill(false);
        Fun00765c40ResidualProducerProofMask empty_proof{};
        const auto no_op =
            apply_proven_fun_00765c40_residual_producer_handoff(
                base, empty_selective, empty_proof);
        require(no_op.wheel_state_source_bits == base.wheel_state_source_bits &&
                    no_op.wheel_plane == base.wheel_plane,
                "empty selective witness changed composed inputs");

        std::cout
            << "{\"format\":\""
            << kFun00765c40ResidualProducerPromotionGateFormat
            << "\",\"ready\":true,"
               "\"historical_v1_format\":\""
            << kFun00765c40HistoricalResidualProducerPromotionGateFormat
            << "\",\"default_proof_mask_fail_closed\":true,"
               "\"present_family_requires_named_proof\":true,"
               "\"empty_proof_contract_rejected\":true,"
               "\"proof_contract_receipt_preserved\":true,"
               "\"absent_family_preserved\":true,"
               "\"legacy_all_family_requires_all_proofs\":true,"
               "\"external_provider_count_after\":7,"
               "\"complete_fun_00765c40_internalized\":false}\n";
        return 0;
    } catch (const std::exception& exc) {
        std::cerr << exc.what() << '\n';
        return 1;
    }
}
