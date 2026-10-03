#include "shift_wheel_spring_gap_batch.hpp"

namespace shift::runtime::physics {

WheelSpringGapBatchResult execute_fun_00758b50_spring_gap_batch(
    const std::array<WheelSpringGapBatchSlotInput, kWheelKinematicsCount>& inputs) {

    WheelSpringGapBatchResult result{};
    for (std::size_t wheel = 0u; wheel < kWheelKinematicsCount; ++wheel) {
        const auto& slot = inputs[wheel];

        // Retail FUN_00758b50 applies the block+0xf8 gate before constructing
        // the relative vector or entering FUN_00755950. Preserve that ordering:
        // downstream slot payload is not consumed for skipped wheels.
        if (slot.kinematic.skip_flag_nonzero) {
            continue;
        }

        const WheelKinematicObservation observation =
            prepare_fun_00758b50_wheel_kinematics(wheel, slot.kinematic);

        WheelSpringGapJoinInput spring_input{};
        spring_input.kinematic = observation;
        spring_input.spring_type = slot.spring_type;
        spring_input.lower_boundary = slot.lower_boundary;
        spring_input.upper_boundary = slot.upper_boundary;
        spring_input.current_gap_before = slot.current_gap_before;

        const WheelSpringGapJoinResult spring_result =
            execute_fun_00755950_spring_gap_join(spring_input);

        result.processed[wheel] = true;
        result.kinematics[wheel] = observation;
        result.spring_results[wheel] = spring_result;
        result.processed_order[result.processed_count] = wheel;
        ++result.processed_count;
    }
    return result;
}

}  // namespace shift::runtime::physics
