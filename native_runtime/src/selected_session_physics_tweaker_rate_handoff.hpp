#pragma once

#include "runtime_loop_policy.hpp"

#include <cstddef>
#include <cstdint>
#include <stdexcept>
#include <string_view>

namespace shift::runtime {

inline constexpr const char* kSelectedSessionPhysicsTweakerRateFormat =
    "SHIFT.SelectedSessionPhysicsTweakerRate/1";
inline constexpr const char* kSelectedSessionPhysicsTweakerRateReadyStatus =
    "selected-session-physics-tweaker-rate-ready";
inline constexpr const char* kSelectedSessionPhysicsTweakerArchiveFilename =
    "PHYSICSBOOTFLOW.bff";
inline constexpr const char* kSelectedSessionPhysicsTweakerArchiveSha256 =
    "f4205984343987d7879fcd65f6b2527848a6fd16e9830d6ccca70b7e5db4254a";
inline constexpr std::uint32_t kSelectedSessionPhysicsTweakerEntryIndex = 49u;
inline constexpr const char* kSelectedSessionPhysicsTweakerEntryPath =
    "vehicles/physics/physicstweaker.xml";
inline constexpr std::uint32_t kSelectedSessionPhysicsTweakerCompressionType = 2u;
inline constexpr std::uint32_t kSelectedSessionPhysicsTweakerCompressedSize = 2452u;
inline constexpr std::uint32_t kSelectedSessionPhysicsTweakerUncompressedSize = 21762u;
inline constexpr const char* kSelectedSessionPhysicsTweakerDecodedSha256 =
    "6cdd05f0512d367c8ce240cb13dd22fe10fb3e21da95185ea8f79e1ca67ca62f";
inline constexpr const char* kSelectedSessionPhysicsTweakerProperty = "tick rate";
inline constexpr const char* kSelectedSessionPhysicsTweakerRuntimeRateGlobal =
    "DAT_00c130d2";
inline constexpr const char* kSelectedSessionPhysicsManagerRateOffset = "0x388";

struct SelectedSessionPhysicsTweakerRateHandoff {
    const char* format = nullptr;
    bool ready = false;
    const char* status = nullptr;

    const char* archive_filename = nullptr;
    const char* archive_sha256 = nullptr;
    std::uint32_t entry_index = 0u;
    const char* entry_path = nullptr;
    std::uint32_t compression_type = 0u;
    std::uint32_t compressed_size = 0u;
    std::uint32_t uncompressed_size = 0u;
    const char* decoded_sha256 = nullptr;

    const char* verification_mode = nullptr;
    bool archive_sha256_verified_this_run = false;
    bool decoded_sha256_verified_this_run = false;

    const char* property = nullptr;
    std::uint32_t rate_hz = 0u;
    const char* runtime_rate_global = nullptr;
    const char* cphysics_manager_rate_offset = nullptr;

    bool outer_scheduler_cadence_admitted = false;
    bool inner_fixed_step_1_over_rate_proven = false;
    bool loaded_inner_physics_rate_admitted = false;
    bool retail_inner_substep_execution_admitted = true;

    bool constructor_default_180_used_as_selected_session_value = true;
    bool community_or_modded_value_used = true;
    bool host_1_60_used_as_inner_rate = true;
    bool worker_poll_10ms_used_as_inner_rate = true;
};

inline bool selected_rate_handoff_string_equals(
    const char* actual,
    std::string_view expected) noexcept {
    return actual != nullptr && std::string_view(actual) == expected;
}

inline double admit_selected_session_physics_tweaker_rate(
    RetailOuterSchedulerContract& scheduler,
    const SelectedSessionPhysicsTweakerRateHandoff& handoff) {

    if (!selected_rate_handoff_string_equals(
            handoff.format, kSelectedSessionPhysicsTweakerRateFormat)) {
        throw std::invalid_argument(
            "selected-session PhysicsTweaker handoff format mismatch");
    }
    if (!handoff.ready ||
        !selected_rate_handoff_string_equals(
            handoff.status, kSelectedSessionPhysicsTweakerRateReadyStatus)) {
        throw std::invalid_argument(
            "selected-session PhysicsTweaker handoff is not ready");
    }

    if (!selected_rate_handoff_string_equals(
            handoff.archive_filename,
            kSelectedSessionPhysicsTweakerArchiveFilename) ||
        !selected_rate_handoff_string_equals(
            handoff.archive_sha256,
            kSelectedSessionPhysicsTweakerArchiveSha256) ||
        handoff.entry_index != kSelectedSessionPhysicsTweakerEntryIndex ||
        !selected_rate_handoff_string_equals(
            handoff.entry_path,
            kSelectedSessionPhysicsTweakerEntryPath) ||
        handoff.compression_type != kSelectedSessionPhysicsTweakerCompressionType ||
        handoff.compressed_size != kSelectedSessionPhysicsTweakerCompressedSize ||
        handoff.uncompressed_size != kSelectedSessionPhysicsTweakerUncompressedSize ||
        !selected_rate_handoff_string_equals(
            handoff.decoded_sha256,
            kSelectedSessionPhysicsTweakerDecodedSha256)) {
        throw std::invalid_argument(
            "selected-session PhysicsTweaker resource identity drift");
    }

    const bool exact_retail_bff = selected_rate_handoff_string_equals(
        handoff.verification_mode, "exact-retail-bff");
    const bool exact_decoded_entry = selected_rate_handoff_string_equals(
        handoff.verification_mode, "exact-decoded-entry");
    const bool exact_extracted_entry_manifest = selected_rate_handoff_string_equals(
        handoff.verification_mode, "exact-extracted-entry-manifest");
    if (!exact_retail_bff &&
        !exact_decoded_entry &&
        !exact_extracted_entry_manifest) {
        throw std::invalid_argument(
            "selected-session PhysicsTweaker verification mode is unsupported");
    }
    // All admitted paths are cryptographically anchored by the decoded payload.
    // The extracted-tree adapter additionally verifies the exact entry metadata
    // from the successful Type-2 extraction manifest before it emits this mode.
    if (!handoff.decoded_sha256_verified_this_run) {
        throw std::invalid_argument(
            "selected-session PhysicsTweaker decoded SHA-256 was not verified");
    }
    if (exact_retail_bff && !handoff.archive_sha256_verified_this_run) {
        throw std::invalid_argument(
            "exact-retail-bff handoff did not verify the archive SHA-256");
    }

    if (!selected_rate_handoff_string_equals(
            handoff.property, kSelectedSessionPhysicsTweakerProperty) ||
        !selected_rate_handoff_string_equals(
            handoff.runtime_rate_global,
            kSelectedSessionPhysicsTweakerRuntimeRateGlobal) ||
        !selected_rate_handoff_string_equals(
            handoff.cphysics_manager_rate_offset,
            kSelectedSessionPhysicsManagerRateOffset)) {
        throw std::invalid_argument(
            "selected-session PhysicsTweaker recovered rate provenance drift");
    }
    if (handoff.rate_hz == 0u || handoff.rate_hz > 0xffffu) {
        throw std::invalid_argument(
            "selected-session PhysicsTweaker rate is outside recovered uint16 domain");
    }

    if (!handoff.outer_scheduler_cadence_admitted ||
        !handoff.inner_fixed_step_1_over_rate_proven ||
        !handoff.loaded_inner_physics_rate_admitted ||
        handoff.retail_inner_substep_execution_admitted) {
        throw std::invalid_argument(
            "selected-session PhysicsTweaker cadence/runtime handoff state mismatch");
    }
    if (handoff.constructor_default_180_used_as_selected_session_value ||
        handoff.community_or_modded_value_used ||
        handoff.host_1_60_used_as_inner_rate ||
        handoff.worker_poll_10ms_used_as_inner_rate) {
        throw std::invalid_argument(
            "selected-session PhysicsTweaker handoff used a forbidden substitute");
    }

    scheduler.admit_loaded_inner_rate(static_cast<double>(handoff.rate_hz));
    return scheduler.loaded_inner_rate_hz;
}

}  // namespace shift::runtime
