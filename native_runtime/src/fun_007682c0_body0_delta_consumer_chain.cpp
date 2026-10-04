#include "shift_fun_007682c0_body0_delta_consumer_chain.hpp"

#include <cmath>
#include <cstring>
#include <memory>
#include <stdexcept>
#include <utility>

namespace shift::runtime::physics {
namespace {

struct MotionReadNativeBodyPassState {
    std::size_t effect_provider_call_count = 0u;
    std::size_t native_delta_application_count = 0u;
    bool effect_present = false;
    Fun007682c0AccumulatorEffect effect{};
    double accumulator_y_after_application = 0.0;
};

void validate_effect(const Fun007682c0AccumulatorEffect& effect) {
    if (!std::isfinite(effect.accumulator_y_delta)) {
        throw std::invalid_argument(
            "FUN_007682c0 native BODY0 effect contains non-finite accumulator delta");
    }
    if (!effect.gate_open && effect.accumulator_y_delta != 0.0) {
        throw std::invalid_argument(
            "FUN_007682c0 native BODY0 closed gate cannot carry accumulator delta");
    }
}

void require_complete_pass_callbacks(
    const Fun0076d100MotionReadEffectNativeBodyCallbacks& callbacks) {
    if (!callbacks.contact_factor ||
        !callbacks.wheel_update ||
        !callbacks.contact_response ||
        !callbacks.contact_outer_input_provider ||
        !callbacks.motion_read_effect_provider) {
        throw std::invalid_argument(
            "FUN_007682c0 native BODY0 chain requires all eight-provider-session pass boundaries");
    }
}

}  // namespace

double apply_fun_007682c0_body_accumulator_y_delta(
    std::vector<std::uint8_t>& body_bytes,
    std::uint32_t body_index,
    double accumulator_y_delta) {
    if (!std::isfinite(accumulator_y_delta)) {
        throw std::invalid_argument(
            "FUN_007682c0 BODY +0x50 delta must be finite");
    }
    if (body_bytes.empty() || body_bytes.size() % kBodyRecordSize != 0u) {
        throw std::invalid_argument(
            "FUN_007682c0 BODY +0x50 application requires exact 0x170 BODY records");
    }
    const std::size_t body_count = body_bytes.size() / kBodyRecordSize;
    if (body_index >= body_count) {
        throw std::out_of_range(
            "FUN_007682c0 BODY +0x50 selected BODY index is out of range");
    }

    const std::size_t offset =
        static_cast<std::size_t>(body_index) * kBodyRecordSize +
        kFun007682c0AccumulatorYOffset;
    static_assert(kFun007682c0AccumulatorYOffset + sizeof(double) <= kBodyRecordSize);

    double accumulator_y = 0.0;
    std::memcpy(&accumulator_y, body_bytes.data() + offset, sizeof(accumulator_y));
    if (!std::isfinite(accumulator_y)) {
        throw std::invalid_argument(
            "FUN_007682c0 BODY +0x50 existing accumulator must be finite");
    }

    const double updated = accumulator_y + accumulator_y_delta;
    if (!std::isfinite(updated)) {
        throw std::overflow_error(
            "FUN_007682c0 BODY +0x50 accumulator update is non-finite");
    }
    std::memcpy(body_bytes.data() + offset, &updated, sizeof(updated));
    return updated;
}

Fun007682c0Body0DeltaConsumerChainResult
execute_fun_00770e80_motion_read_effect_native_body0_consumer_chain(
    double outer_timestep,
    const std::vector<std::uint8_t>& initial_body_bytes,
    const Fun0076d100MotionReadEffectNativeBodyProvider& physics_pass_provider,
    const Fun00765470MachineScalarHalfStepProvider& half_step_provider,
    const Fun007b8810PostHalfStepCallback& post_half_step,
    const GlobalVehicleBodyOwnerIdentityHandoff& owner_handoff) {
    if (!physics_pass_provider) {
        throw std::invalid_argument(
            "FUN_007682c0 native BODY0 chain requires physics-pass provider");
    }
    if (initial_body_bytes.empty() ||
        initial_body_bytes.size() % kBodyRecordSize != 0u) {
        throw std::invalid_argument(
            "FUN_007682c0 native BODY0 chain requires exact BODY records");
    }

    // Phase 703 is the authoritative retail BODY selection gate.  This call
    // rejects blocked/ambiguous handoffs and requires the BMW chassis BODY 0.
    const VehicleBodyIdentitySelection selection =
        build_vehicle_body_identity_selection_from_global_owner(owner_handoff);
    const std::size_t body_count = initial_body_bytes.size() / kBodyRecordSize;
    if (selection.body_index >= body_count) {
        throw std::out_of_range(
            "FUN_007682c0 native BODY0 chain selected BODY is outside persistent state");
    }

    Fun007682c0Body0DeltaConsumerChainResult result{};
    result.selected_body_index = selection.body_index;
    std::array<std::shared_ptr<MotionReadNativeBodyPassState>, kFun00770e80PassCount>
        states{};

    Fun0076d100ContactOuterProvider adapted_provider =
        [&](std::size_t pass_index) {
            if (pass_index >= kFun00770e80PassCount) {
                throw std::logic_error(
                    "FUN_007682c0 native BODY0 pass index exceeds proven domain");
            }
            if (states[pass_index]) {
                throw std::logic_error(
                    "FUN_007682c0 native BODY0 provider invoked twice for one pass");
            }

            auto typed = physics_pass_provider(pass_index);
            require_complete_pass_callbacks(typed);
            auto state = std::make_shared<MotionReadNativeBodyPassState>();
            states[pass_index] = state;

            Fun0076d100ContactOuterProviderCallbacks callbacks{};
            callbacks.contact_factor = std::move(typed.contact_factor);
            callbacks.wheel_update = std::move(typed.wheel_update);
            callbacks.contact_response = std::move(typed.contact_response);
            callbacks.contact_outer_input_provider =
                std::move(typed.contact_outer_input_provider);
            auto effect_provider = std::move(typed.motion_read_effect_provider);
            callbacks.motion_read_gate =
                [state, effect_provider = std::move(effect_provider)]() mutable {
                    ++state->effect_provider_call_count;
                    const auto effect = effect_provider();
                    validate_effect(effect);
                    state->effect = effect;
                    state->effect_present = true;
                };
            return callbacks;
        };

    Fun0076d100PostAnchorBodyStateMutator post_anchor_mutator =
        [&](std::size_t pass_index,
            std::vector<std::uint8_t>& current_body_bytes) {
            if (pass_index >= kFun00770e80PassCount) {
                throw std::logic_error(
                    "FUN_007682c0 native BODY0 mutation pass exceeds proven domain");
            }
            const auto& state = states[pass_index];
            if (!state ||
                state->effect_provider_call_count != 1u ||
                !state->effect_present) {
                throw std::logic_error(
                    "FUN_007682c0 native BODY0 effect is unavailable at application point");
            }
            if (!state->effect.gate_open) {
                return;
            }
            state->accumulator_y_after_application =
                apply_fun_007682c0_body_accumulator_y_delta(
                    current_body_bytes,
                    selection.body_index,
                    state->effect.accumulator_y_delta);
            ++state->native_delta_application_count;
        };

    result.joined = execute_fun_00770e80_contact_outer_provider_chain(
        outer_timestep,
        initial_body_bytes,
        adapted_provider,
        half_step_provider,
        post_half_step,
        post_anchor_mutator);

    for (std::size_t pass_index = 0u;
         pass_index < kFun00770e80PassCount;
         ++pass_index) {
        const auto& state = states[pass_index];
        if (!state ||
            state->effect_provider_call_count != 1u ||
            !state->effect_present) {
            throw std::logic_error(
                "FUN_007682c0 native BODY0 effect provider cardinality mismatch");
        }
        const std::size_t expected_applications =
            state->effect.gate_open ? 1u : 0u;
        if (state->native_delta_application_count != expected_applications) {
            throw std::logic_error(
                "FUN_007682c0 native BODY0 delta application cardinality mismatch");
        }

        result.motion_read_effects[pass_index] = state->effect;
        result.motion_read_effect_present[pass_index] = true;
        result.motion_read_effect_provider_call_counts[pass_index] =
            state->effect_provider_call_count;
        result.native_delta_application_counts[pass_index] =
            state->native_delta_application_count;
        result.accumulator_y_after_application[pass_index] =
            state->accumulator_y_after_application;
        result.motion_read_effect_provider_call_count +=
            state->effect_provider_call_count;
        result.native_delta_application_count +=
            state->native_delta_application_count;
        if (state->effect.gate_open) {
            ++result.motion_read_gate_open_count;
        }
    }

    return result;
}

}  // namespace shift::runtime::physics
