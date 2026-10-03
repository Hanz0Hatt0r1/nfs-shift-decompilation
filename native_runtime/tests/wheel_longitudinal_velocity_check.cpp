#include "shift_wheel_longitudinal_velocity.hpp"

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

shift::runtime::physics::WheelLongitudinalInput make_input(
    std::size_t wheel_index,
    double longitudinal_component) {

    using namespace shift::runtime::physics;
    WheelLongitudinalInput input{};
    input.wheel_index = wheel_index;
    input.shared_velocity = {
        10.0 + static_cast<double>(wheel_index),
        -3.0,
        4.0,
    };
    input.local_velocity = {
        longitudinal_component,
        99.0,
        -7.0,
    };
    input.reconstructed_world_velocity = {3.0, -1.0, 0.5};
    return input;
}

}  // namespace

int main() {
    using namespace shift::runtime::physics;

    try {
        double max_error = 0.0;

        if (kWheelLongitudinalBaseOffset != 0x400u ||
            kWheelLongitudinalStride != 0xa80u ||
            kWheelLongitudinalCount != 4u ||
            kWheelLongitudinalVelocityOffset != 0x48u ||
            kWheelLongitudinalPoseOffset != 0xd4u ||
            kWheelLongitudinalPairAverageFlagOffset != 0x3ee0u ||
            kWheelLongitudinalPairAverageModeOffset != 0x3eb8u) {
            throw std::runtime_error("wheel longitudinal source layout mismatch");
        }

        const auto single = execute_fun_00755f80_precomputed_handoff(
            make_input(1u, -2.5));
        if (single.wheel_index != 1u ||
            single.wheel_object_offset != 0xe80u) {
            throw std::runtime_error("FUN_00755f80 wheel offset mismatch");
        }
        require_close(
            single.longitudinal_component,
            -2.5,
            0.0,
            "FUN_00755f80 longitudinal extraction",
            max_error);
        const std::array<double, 3> expected_after = {8.0, -2.0, 3.5};
        for (std::size_t component = 0; component < expected_after.size(); ++component) {
            require_close(
                single.shared_velocity_after[component],
                expected_after[component],
                0.0,
                "FUN_00755f80 reconstructed subtraction",
                max_error);
        }

        const std::array<WheelLongitudinalInput, kWheelLongitudinalCount> inputs = {
            make_input(0u, 2.0),
            make_input(1u, 4.0),
            make_input(2u, 6.0),
            make_input(3u, 10.0),
        };

        const auto unchanged = execute_fun_00763570_precomputed_batch(
            inputs,
            false,
            0,
            true);
        const std::array<double, 4> expected_components = {2.0, 4.0, 6.0, 10.0};
        for (std::size_t wheel = 0; wheel < expected_components.size(); ++wheel) {
            require_close(
                unchanged.reported_components[wheel],
                expected_components[wheel],
                0.0,
                "FUN_00763570 ordered component storage",
                max_error);
            if (unchanged.observations[wheel].wheel_index != wheel) {
                throw std::runtime_error("FUN_00763570 observation ordering mismatch");
            }
        }

        const auto averaged = execute_fun_00763570_precomputed_batch(
            inputs,
            true,
            0,
            true);
        require_close(
            averaged.reported_components[2],
            8.0,
            0.0,
            "FUN_00763570 rear pair average wheel 2",
            max_error);
        require_close(
            averaged.reported_components[3],
            8.0,
            0.0,
            "FUN_00763570 rear pair average wheel 3",
            max_error);

        const auto mode_blocked = execute_fun_00763570_precomputed_batch(
            inputs,
            true,
            1,
            true);
        require_close(
            mode_blocked.reported_components[2],
            6.0,
            0.0,
            "FUN_00763570 mode gate wheel 2",
            max_error);
        require_close(
            mode_blocked.reported_components[3],
            10.0,
            0.0,
            "FUN_00763570 mode gate wheel 3",
            max_error);

        const auto config_blocked = execute_fun_00763570_precomputed_batch(
            inputs,
            true,
            0,
            false);
        require_close(
            config_blocked.reported_components[2],
            6.0,
            0.0,
            "FUN_00763570 config gate wheel 2",
            max_error);
        require_close(
            config_blocked.reported_components[3],
            10.0,
            0.0,
            "FUN_00763570 config gate wheel 3",
            max_error);

        bool out_of_order_rejected = false;
        try {
            auto reordered = inputs;
            std::swap(reordered[0], reordered[1]);
            (void)execute_fun_00763570_precomputed_batch(
                reordered,
                false,
                0,
                false);
        } catch (const std::invalid_argument&) {
            out_of_order_rejected = true;
        }
        if (!out_of_order_rejected) {
            throw std::runtime_error("FUN_00763570 accepted reordered wheel inputs");
        }

        bool duplicate_rejected = false;
        try {
            auto duplicate = inputs;
            duplicate[3].wheel_index = 2u;
            (void)execute_fun_00763570_precomputed_batch(
                duplicate,
                false,
                0,
                false);
        } catch (const std::invalid_argument&) {
            duplicate_rejected = true;
        }
        if (!duplicate_rejected) {
            throw std::runtime_error("FUN_00763570 accepted duplicate wheel index");
        }

        bool out_of_range_rejected = false;
        try {
            auto invalid = make_input(4u, 1.0);
            (void)execute_fun_00755f80_precomputed_handoff(invalid);
        } catch (const std::invalid_argument&) {
            out_of_range_rejected = true;
        }
        if (!out_of_range_rejected) {
            throw std::runtime_error("FUN_00755f80 accepted out-of-range wheel index");
        }

        bool non_finite_rejected = false;
        try {
            auto invalid = make_input(0u, 1.0);
            invalid.local_velocity[0] = std::numeric_limits<double>::infinity();
            (void)execute_fun_00755f80_precomputed_handoff(invalid);
        } catch (const std::invalid_argument&) {
            non_finite_rejected = true;
        }
        if (!non_finite_rejected) {
            throw std::runtime_error("FUN_00755f80 accepted non-finite input");
        }

        bool overflow_rejected = false;
        try {
            const WheelLongitudinalVector3d maximum = {
                std::numeric_limits<double>::max(),
                0.0,
                0.0,
            };
            const WheelLongitudinalVector3d negative_maximum = {
                -std::numeric_limits<double>::max(),
                0.0,
                0.0,
            };
            (void)apply_fun_00755f80_reconstructed_subtraction(
                maximum,
                negative_maximum);
        } catch (const std::invalid_argument&) {
            overflow_rejected = true;
        }
        if (!overflow_rejected) {
            throw std::runtime_error("FUN_00755f80 accepted non-finite subtraction result");
        }

        std::cout
            << "{\"format\":\"" << kNativeWheelLongitudinalVelocityFormat << "\","
            << "\"ready\":true,"
            << "\"function\":\"" << kWheelLongitudinalFunction << "\","
            << "\"caller\":\"" << kWheelLongitudinalCallerFunction << "\","
            << "\"wheel_count\":" << kWheelLongitudinalCount << ","
            << "\"wheel_stride\":" << kWheelLongitudinalStride << ","
            << "\"single_wheel_handoff_proven\":true,"
            << "\"retail_wheel_order_proven\":true,"
            << "\"rear_pair_average_proven\":true,"
            << "\"transform_fun_007af010_external\":true,"
            << "\"runtime_scheduling_proven\":false,"
            << "\"max_error\":" << max_error << "}\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
