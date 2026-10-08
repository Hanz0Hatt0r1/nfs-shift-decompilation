#include "shift_fun_00765c40_composed_residual_executor.hpp"

#include <cstddef>
#include <cstdint>
#include <iostream>
#include <limits>
#include <stdexcept>

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
        base.wheel_plane = {0xa1u, 0xa2u, 0xa3u, 0xa4u};
        base.current_body_bytes = {0x11u, 0x22u, 0x33u};
        base.cached_query_handle = 0x1234u;
        base.wheel_state_source_bits = 0xaabbccddeeff0011ull;
        base.persistent_write.positive_branch_values = {1.0, 2.0};
        base.persistent_write.interpolation_result = 3.0f;
        base.wheel_pair.qword_bits[0][0] = 0x501u;
        base.contact_array.record_pointer_tokens[0] = 0x601u;
        base.contact_body_entries[0].apply = true;
        base.contact_body_entries[0].contribution = {0.1, 0.2, 0.3};
        base.bounded_state_tail.write_block_executed = true;
        base.bounded_state_tail.state_3668_bits = 0x701u;
        base.optional_body_sweep.enabled = true;
        base.optional_body_sweep.entries[0].contribution = {0.4, 0.5, 0.6};
        base.initial_body.linear = {7.0, 8.0, 9.0};
        base.initial_body.angular = {1.0, 2.0, 3.0};
        base.execute_wheel_job_queue = []() {};
        base.read_load_term = [](std::size_t wheel) {
            return static_cast<double>(wheel + 1u);
        };

        Fun00765c40ResidualProducerHandoff handoff{};
        handoff.wheel_plane = {0x10u, 0x20u, 0x30u, 0x40u};
        handoff.wheel_state_source_bits = 0x1122334455667788ull;
        handoff.persistent_write.positive_branch_values = {10.0, 20.0};
        handoff.persistent_write.interpolation_result = 4.5f;
        handoff.wheel_pair.qword_bits[0][0] = 0x101u;
        handoff.wheel_pair.qword_bits[3][1] = 0x202u;
        handoff.contact_array.record_pointer_tokens[0] = 0x3001u;
        handoff.contact_array.scalar_qword_bits[11] = 0x4002u;
        handoff.contact_body_entries[2].apply = true;
        handoff.contact_body_entries[2].point_or_lever_arm = {1.0, 2.0, 3.0};
        handoff.contact_body_entries[2].contribution = {4.0, 5.0, 6.0};
        handoff.bounded_state_tail.write_block_executed = true;
        handoff.bounded_state_tail.state_3668_bits = 0xaaaau;
        handoff.bounded_state_tail.state_3670_bits = 0xbbbbu;
        handoff.bounded_state_tail.state_3678_bits = 0xccccu;
        handoff.optional_body_sweep.enabled = true;
        handoff.optional_body_sweep.entries[1].point_or_lever_arm = {7.0, 8.0, 9.0};
        handoff.optional_body_sweep.entries[1].contribution = {10.0, 11.0, 12.0};

        require(!handoff.family_presence_explicit,
                "legacy producer handoff unexpectedly entered explicit presence mode");
        validate_fun_00765c40_residual_producer_handoff_known_invariants(handoff);

        const auto bridged =
            apply_fun_00765c40_residual_producer_handoff(base, handoff);

        require(bridged.wheel_plane == handoff.wheel_plane,
                "legacy producer handoff wheel-plane drift");
        require(bridged.wheel_state_source_bits == handoff.wheel_state_source_bits,
                "legacy producer handoff wheel-state source drift");
        require(bridged.persistent_write.positive_branch_values ==
                    handoff.persistent_write.positive_branch_values &&
                    bridged.persistent_write.interpolation_result == 4.5f,
                "legacy producer handoff FUN_007584f0 payload drift");
        require(bridged.wheel_pair.qword_bits == handoff.wheel_pair.qword_bits,
                "legacy producer handoff wheel-pair drift");
        require(bridged.contact_array.record_pointer_tokens ==
                    handoff.contact_array.record_pointer_tokens &&
                    bridged.contact_array.scalar_qword_bits ==
                    handoff.contact_array.scalar_qword_bits,
                "legacy producer handoff contact-array drift");
        require(bridged.contact_body_entries[2].apply &&
                    bridged.contact_body_entries[2].contribution[1] == 5.0,
                "legacy producer handoff contact BODY drift");
        require(bridged.bounded_state_tail.write_block_executed &&
                    bridged.bounded_state_tail.state_3668_bits == 0xaaaau &&
                    bridged.bounded_state_tail.state_3678_bits == 0xccccu,
                "legacy producer handoff bounded-tail drift");
        require(bridged.optional_body_sweep.enabled &&
                    bridged.optional_body_sweep.entries[1].contribution[2] == 12.0,
                "legacy producer handoff optional BODY drift");

        require(bridged.current_body_bytes == base.current_body_bytes,
                "producer handoff overwrote native BODY bytes");
        require(bridged.cached_query_handle == base.cached_query_handle,
                "producer handoff overwrote native query cache");
        require(bridged.initial_body.linear == base.initial_body.linear &&
                    bridged.initial_body.angular == base.initial_body.angular,
                "producer handoff overwrote initial BODY accumulator state");
        require(static_cast<bool>(bridged.execute_wheel_job_queue) &&
                    static_cast<bool>(bridged.read_load_term) &&
                    bridged.read_load_term(3u) == 4.0,
                "producer handoff overwrote wheel-job execution seam");

        auto partial = handoff;
        partial.family_presence_explicit = true;
        partial.family_present.fill(false);
        set_fun_00765c40_residual_producer_family_present(
            partial,
            Fun00765c40ResidualProducerFamily::WheelStateSource);
        partial.persistent_write.positive_branch_values[1] =
            std::numeric_limits<double>::quiet_NaN();
        validate_fun_00765c40_residual_producer_handoff_known_invariants(partial);
        const auto partial_bridged =
            apply_fun_00765c40_residual_producer_handoff(base, partial);
        require(partial_bridged.wheel_state_source_bits ==
                    partial.wheel_state_source_bits,
                "selective producer handoff missed present wheel-state source");
        require(partial_bridged.wheel_plane == base.wheel_plane &&
                    partial_bridged.persistent_write.positive_branch_values ==
                        base.persistent_write.positive_branch_values &&
                    partial_bridged.wheel_pair.qword_bits == base.wheel_pair.qword_bits &&
                    partial_bridged.contact_array.record_pointer_tokens ==
                        base.contact_array.record_pointer_tokens &&
                    partial_bridged.contact_body_entries[0].apply ==
                        base.contact_body_entries[0].apply &&
                    partial_bridged.bounded_state_tail.state_3668_bits ==
                        base.bounded_state_tail.state_3668_bits &&
                    partial_bridged.optional_body_sweep.enabled ==
                        base.optional_body_sweep.enabled,
                "selective producer handoff overwrote an absent family");

        bool nonfinite_persistent_rejected = false;
        try {
            auto invalid = handoff;
            set_fun_00765c40_residual_producer_family_present(
                invalid,
                Fun00765c40ResidualProducerFamily::PersistentWrite);
            invalid.persistent_write.positive_branch_values[1] =
                std::numeric_limits<double>::quiet_NaN();
            validate_fun_00765c40_residual_producer_handoff_known_invariants(invalid);
        } catch (const std::invalid_argument&) {
            nonfinite_persistent_rejected = true;
        }
        require(nonfinite_persistent_rejected,
                "producer handoff accepted non-finite present FUN_007584f0 payload");

        auto opaque_bits = handoff;
        opaque_bits.wheel_state_source_bits = 0xffffffffffffffffull;
        opaque_bits.contact_array.scalar_qword_bits[0] = 0x7ff8000000000000ull;
        validate_fun_00765c40_residual_producer_handoff_known_invariants(opaque_bits);
        require(opaque_bits.wheel_state_source_bits == 0xffffffffffffffffull &&
                    opaque_bits.contact_array.scalar_qword_bits[0] ==
                        0x7ff8000000000000ull,
                "producer handoff validator reinterpreted opaque qword payloads");

        std::cout
            << "{\"format\":\""
            << kFun00765c40ResidualProducerHandoffFormat
            << "\",\"ready\":true,\"payload_families\":"
            << kFun00765c40ResidualProducerHandoffFamilyCount
            << ",\"historical_v1_format\":\""
            << kFun00765c40HistoricalResidualProducerHandoffFormat
            << "\",\"legacy_all_families_present\":true,"
               "\"selective_family_overlay\":true,"
               "\"known_invariants_validate_only_present_families\":true,"
               "\"opaque_bits_preserved\":true,"
               "\"native_state_preserved\":true,"
               "\"wheel_job_execution_external\":true,"
               "\"scene_query_external\":true}\n";
        return 0;
    } catch (const std::exception& exc) {
        std::cerr << exc.what() << '\n';
        return 1;
    }
}
