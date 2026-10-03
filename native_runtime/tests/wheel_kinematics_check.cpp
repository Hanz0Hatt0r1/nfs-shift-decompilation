#include "shift_wheel_kinematics.hpp"

#include <algorithm>
#include <array>
#include <cmath>
#include <iostream>
#include <limits>
#include <stdexcept>

namespace {

void require_close(
    double actual,
    double expected,
    double tolerance,
    const char* label,
    double& max_error) {

    const double error = std::abs(actual - expected);
    max_error = std::max(max_error, error);
    if (!std::isfinite(actual) || error > tolerance) {
        throw std::runtime_error(label);
    }
}

shift::runtime::physics::WheelKinematicSlotInput make_slot(
    bool skip,
    double x,
    double y,
    double z,
    double reference,
    double projection) {

    shift::runtime::physics::WheelKinematicSlotInput input{};
    input.skip_flag_nonzero = skip;
    input.relative_vector = {x, y, z};
    input.reference_length = reference;
    input.projection_input = projection;
    return input;
}

}  // namespace

int main() {
    using namespace shift::runtime::physics;
    try {
        double max_error = 0.0;

        if (kWheelKinematicsCount != 4u ||
            kWheelKinematicsStateBase != 0x848u ||
            kWheelKinematicsStateStride != 0xa80u ||
            kWheelKinematicsRuntimeBase != 0x400u ||
            kWheelKinematicsRuntimeStride != 0xa80u ||
            kWheelKinematicsSkipFlagOffset != 0xf8u ||
            kWheelKinematicsFinalFlagOffset != 0x11cu ||
            kWheelKinematicsDistanceReferenceOffset != 0x138u ||
            kWheelKinematicsDistanceErrorOffset != 0x128u ||
            kWheelKinematicsProjectionOffset != 0x130u ||
            kWheelKinematicsHelperOutputOffset != 0x148u) {
            throw std::runtime_error("FUN_00758b50 layout constants mismatch");
        }

        const auto single = prepare_fun_00758b50_wheel_kinematics(
            2u,
            make_slot(false, 3.0, 4.0, 12.0, 15.0, -2.0));
        if (single.wheel_state_offset != 0x1d48u ||
            single.wheel_runtime_offset != 0x1900u) {
            throw std::runtime_error("FUN_00758b50 wheel slot offsets mismatch");
        }
        require_close(single.relative_length, 13.0, 0.0, "relative length", max_error);
        require_close(single.relative_unit[0], 3.0 / 13.0, 1e-15, "unit X", max_error);
        require_close(single.relative_unit[1], 4.0 / 13.0, 1e-15, "unit Y", max_error);
        require_close(single.relative_unit[2], 12.0 / 13.0, 1e-15, "unit Z", max_error);
        require_close(single.distance_error, 2.0, 0.0, "distance error", max_error);
        require_close(single.stored_projection_value, 2.0, 0.0, "stored projection", max_error);

        const std::array<WheelKinematicSlotInput, kWheelKinematicsCount> slots = {
            make_slot(false, 3.0, 4.0, 0.0, 7.0, 1.0),
            make_slot(true, 1.0, 0.0, 0.0, 2.0, 2.0),
            make_slot(false, 0.0, 5.0, 12.0, 20.0, -3.0),
            make_slot(false, 8.0, 0.0, 15.0, 18.0, 4.0),
        };
        const auto batch = execute_fun_00758b50_prehelper_batch(slots);
        if (batch.processed_count != 3u ||
            !batch.processed[0] || batch.processed[1] ||
            !batch.processed[2] || !batch.processed[3]) {
            throw std::runtime_error("FUN_00758b50 +0xf8 skip gate mismatch");
        }
        if (batch.observations[3].wheel_state_offset != 0x27c8u ||
            batch.observations[3].wheel_runtime_offset != 0x2380u) {
            throw std::runtime_error("FUN_00758b50 fourth wheel offsets mismatch");
        }

        WheelKinematicsPairInput pair{};
        pair.source_a_left = 10.0;
        pair.source_b_left = 3.0;
        pair.source_a_right = 4.0;
        pair.source_b_right = 1.0;
        pair.scale = 0.5;
        pair.left_destination_before = 5.0;
        pair.right_destination_before = 8.0;
        const auto adjusted = apply_fun_00758b50_pair_delta(pair);
        require_close(adjusted.delta, 2.0, 0.0, "pair delta", max_error);
        require_close(adjusted.left_destination_after, 7.0, 0.0, "pair left", max_error);
        require_close(adjusted.right_destination_after, 6.0, 0.0, "pair right", max_error);

        if (kWheelKinematicsFrontDeltaSources !=
                std::array<std::size_t, 4>{0x928u, 0x938u, 0x13a8u, 0x13b8u} ||
            kWheelKinematicsFrontDestinations !=
                std::array<std::size_t, 2>{0x948u, 0x13c8u} ||
            kWheelKinematicsRearDeltaSources !=
                std::array<std::size_t, 4>{0x1e28u, 0x1e38u, 0x28a8u, 0x28b8u} ||
            kWheelKinematicsRearDestinations !=
                std::array<std::size_t, 2>{0x1e48u, 0x28c8u} ||
            kWheelKinematicsFrontScaleOffset != 0x2e20u ||
            kWheelKinematicsRearScaleOffset != 0x2e28u) {
            throw std::runtime_error("FUN_00758b50 pair topology mismatch");
        }

        if (!fun_00758b50_final_transform_eligible(true, false) ||
            fun_00758b50_final_transform_eligible(false, false) ||
            fun_00758b50_final_transform_eligible(true, true)) {
            throw std::runtime_error("FUN_00758b50 final transform gate mismatch");
        }

        bool zero_vector_rejected = false;
        try {
            (void)prepare_fun_00758b50_wheel_kinematics(
                0u,
                make_slot(false, 0.0, 0.0, 0.0, 1.0, 0.0));
        } catch (const std::invalid_argument&) {
            zero_vector_rejected = true;
        }
        if (!zero_vector_rejected) {
            throw std::runtime_error("FUN_00758b50 accepted zero relative vector");
        }

        bool non_finite_rejected = false;
        try {
            auto invalid = make_slot(false, 1.0, 0.0, 0.0, 1.0, 0.0);
            invalid.projection_input = std::numeric_limits<double>::infinity();
            (void)prepare_fun_00758b50_wheel_kinematics(0u, invalid);
        } catch (const std::invalid_argument&) {
            non_finite_rejected = true;
        }
        if (!non_finite_rejected) {
            throw std::runtime_error("FUN_00758b50 accepted non-finite input");
        }

        bool overflow_rejected = false;
        try {
            auto invalid_pair = pair;
            invalid_pair.source_a_left = std::numeric_limits<double>::max();
            invalid_pair.source_b_left = -std::numeric_limits<double>::max();
            (void)apply_fun_00758b50_pair_delta(invalid_pair);
        } catch (const std::invalid_argument&) {
            overflow_rejected = true;
        }
        if (!overflow_rejected) {
            throw std::runtime_error("FUN_00758b50 accepted non-finite pair result");
        }

        std::cout
            << "{\"format\":\"" << kNativeWheelKinematicsFormat << "\","
            << "\"ready\":true,"
            << "\"function\":\"FUN_00758b50\","
            << "\"caller\":\"FUN_0076d100\","
            << "\"wheel_count\":4,"
            << "\"prehelper_handoff_proven\":true,"
            << "\"skip_gate_proven\":true,"
            << "\"pair_delta_proven\":true,"
            << "\"final_transform_gate_proven\":true,"
            << "\"spring_helper_external\":true,"
            << "\"final_transform_vectors_external\":true,"
            << "\"runtime_scheduling_proven\":false,"
            << "\"max_absolute_error\":" << max_error << "}\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
