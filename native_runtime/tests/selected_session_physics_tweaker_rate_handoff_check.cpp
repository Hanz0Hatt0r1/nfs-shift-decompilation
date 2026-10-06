#include "selected_session_physics_tweaker_rate_handoff.hpp"

#include <cmath>
#include <iostream>
#include <stdexcept>

namespace {

using namespace shift::runtime;

void require(bool condition, const char* message) {
    if (!condition) {
        throw std::runtime_error(message);
    }
}

RetailOuterSchedulerContract make_scheduler() {
    return make_retail_outer_scheduler_contract(
        true,
        kRetailOuterNominalFrequencyHz,
        kRetailOuterGatePeriodMs,
        kRetailNormalOuterIncrementSeconds,
        kRetailSteadySchedulerInvocationsPerDispatch);
}

SelectedSessionPhysicsTweakerRateHandoff make_fixture_handoff() {
    // 360 Hz is a regression fixture only. It is not promoted as the retail
    // selected-session rate; production admission remains blocked on the exact
    // attached PC PhysicsTweaker payload.
    SelectedSessionPhysicsTweakerRateHandoff handoff{};
    handoff.format = kSelectedSessionPhysicsTweakerRateFormat;
    handoff.ready = true;
    handoff.status = kSelectedSessionPhysicsTweakerRateReadyStatus;
    handoff.archive_filename = kSelectedSessionPhysicsTweakerArchiveFilename;
    handoff.archive_sha256 = kSelectedSessionPhysicsTweakerArchiveSha256;
    handoff.entry_index = kSelectedSessionPhysicsTweakerEntryIndex;
    handoff.entry_path = kSelectedSessionPhysicsTweakerEntryPath;
    handoff.compression_type = kSelectedSessionPhysicsTweakerCompressionType;
    handoff.compressed_size = kSelectedSessionPhysicsTweakerCompressedSize;
    handoff.uncompressed_size = kSelectedSessionPhysicsTweakerUncompressedSize;
    handoff.decoded_sha256 = kSelectedSessionPhysicsTweakerDecodedSha256;
    handoff.verification_mode = "exact-retail-bff";
    handoff.archive_sha256_verified_this_run = true;
    handoff.decoded_sha256_verified_this_run = true;
    handoff.property = kSelectedSessionPhysicsTweakerProperty;
    handoff.rate_hz = 360u;
    handoff.runtime_rate_global = kSelectedSessionPhysicsTweakerRuntimeRateGlobal;
    handoff.cphysics_manager_rate_offset = kSelectedSessionPhysicsManagerRateOffset;
    handoff.outer_scheduler_cadence_admitted = true;
    handoff.inner_fixed_step_1_over_rate_proven = true;
    handoff.loaded_inner_physics_rate_admitted = true;
    handoff.retail_inner_substep_execution_admitted = false;
    handoff.constructor_default_180_used_as_selected_session_value = false;
    handoff.community_or_modded_value_used = false;
    handoff.host_1_60_used_as_inner_rate = false;
    handoff.worker_poll_10ms_used_as_inner_rate = false;
    return handoff;
}

template <typename Mutator>
void require_rejected(Mutator mutate, const char* message) {
    auto scheduler = make_scheduler();
    auto handoff = make_fixture_handoff();
    mutate(handoff);
    bool rejected = false;
    try {
        (void)admit_selected_session_physics_tweaker_rate(scheduler, handoff);
    } catch (const std::invalid_argument&) {
        rejected = true;
    }
    require(rejected && !scheduler.loaded_inner_rate_admitted, message);
}

}  // namespace

int main() {
    try {
        require_rejected(
            [](auto& handoff) { handoff.format = "SHIFT.Wrong/1"; },
            "selected-rate handoff accepted wrong format");
        require_rejected(
            [](auto& handoff) { handoff.decoded_sha256 = "00"; },
            "selected-rate handoff accepted decoded hash drift");
        require_rejected(
            [](auto& handoff) {
                handoff.archive_sha256_verified_this_run = false;
            },
            "selected-rate handoff accepted unverified exact retail archive");
        require_rejected(
            [](auto& handoff) { handoff.decoded_sha256_verified_this_run = false; },
            "selected-rate handoff accepted unverified decoded payload");
        require_rejected(
            [](auto& handoff) { handoff.rate_hz = 65536u; },
            "selected-rate handoff accepted rate outside uint16 domain");
        require_rejected(
            [](auto& handoff) {
                handoff.constructor_default_180_used_as_selected_session_value = true;
            },
            "selected-rate handoff accepted constructor-default substitution");
        require_rejected(
            [](auto& handoff) {
                handoff.retail_inner_substep_execution_admitted = true;
            },
            "selected-rate handoff accepted premature inner-execution claim");

        auto scheduler = make_scheduler();
        const auto handoff = make_fixture_handoff();
        const double admitted =
            admit_selected_session_physics_tweaker_rate(scheduler, handoff);
        require(scheduler.loaded_inner_rate_admitted && admitted == 360.0,
                "selected-rate fixture did not admit through typed handoff");
        require(
            std::abs(scheduler.inner_substep_seconds() - (1.0 / 360.0)) < 1e-15,
            "selected-rate handoff did not drive exact reciprocal scheduler dt");

        auto decoded_only_scheduler = make_scheduler();
        auto decoded_only = make_fixture_handoff();
        decoded_only.verification_mode = "exact-decoded-entry";
        decoded_only.archive_sha256_verified_this_run = false;
        const double decoded_only_rate =
            admit_selected_session_physics_tweaker_rate(
                decoded_only_scheduler, decoded_only);
        require(decoded_only_rate == 360.0,
                "exact decoded-entry handoff was not admitted");

        std::cout
            << "{\"format\":\"SHIFT.SelectedSessionPhysicsTweakerRateNativeHandoffRegression/1\","
            << "\"ready\":true,"
            << "\"typed_handoff_admission_ready\":true,"
            << "\"exact_resource_identity_locked\":true,"
            << "\"decoded_hash_required\":true,"
            << "\"forbidden_substitutes_rejected\":true,"
            << "\"fixture_rate_hz\":360,"
            << "\"fixture_is_retail_selected_session_rate\":false}\n";
        return 0;
    } catch (const std::exception& exc) {
        std::cerr << exc.what() << '\n';
        return 1;
    }
}
