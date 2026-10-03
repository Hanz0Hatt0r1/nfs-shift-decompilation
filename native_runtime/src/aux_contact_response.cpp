#include "shift_aux_contact_response.hpp"

#include <cmath>
#include <stdexcept>
#include <string>

namespace shift::runtime::physics {
namespace {

template <typename Range>
void require_finite(const Range& values, const char* label) {
    for (const auto value : values) {
        if (!std::isfinite(static_cast<double>(value))) {
            throw std::invalid_argument(
                std::string(label) + " contains non-finite value");
        }
    }
}

void require_finite_value(double value, const char* label) {
    if (!std::isfinite(value)) {
        throw std::invalid_argument(
            std::string(label) + " must be finite");
    }
}

}  // namespace

AuxContactResponseResult execute_fun_00758fc0_aux_contact_response(
    const AuxContactResponseInput& input) {

    require_finite(input.reference_point, "FUN_00758fc0 reference point");
    require_finite(input.record.point, "FUN_00758fc0 record point");
    require_finite_value(input.record.gain, "FUN_00758fc0 gain");
    require_finite_value(input.record.scale, "FUN_00758fc0 scale");

    AuxContactResponseResult result{};
    result.body_accumulator = input.body_accumulator;

    result.transformed_record_point =
        transform_fun_007aefb0_refresh(
            input.body_frame,
            input.record.point);
    result.body_point_output =
        transform_fun_007537b0_body_point(
            input.body_transform,
            result.transformed_record_point);
    result.local_point =
        transform_fun_007af0a0_refresh(
            input.body_frame,
            result.body_point_output);

    for (std::size_t component = 0; component < 3u; ++component) {
        result.relative_point[component] =
            result.local_point[component] - input.reference_point[component];
    }
    require_finite(result.relative_point, "FUN_00758fc0 relative point");

    if (!input.record.active || result.relative_point[2] >= 0.0) {
        return result;
    }

    result.square_negative_z =
        result.relative_point[2] * result.relative_point[2];
    require_finite_value(
        result.square_negative_z,
        "FUN_00758fc0 squared negative z");

    result.directional_multiplier =
        evaluate_fun_00755340_directional_factor(
            input.record.directional_curve,
            result.relative_point[0],
            result.relative_point[2]);

    result.local_response = {
        0.0,
        result.directional_multiplier *
            input.record.gain *
            result.square_negative_z,
        input.record.scale * result.square_negative_z,
    };
    require_finite(result.local_response, "FUN_00758fc0 local response");

    result.transformed_response =
        transform_fun_007aefb0_refresh(
            input.body_frame,
            result.local_response);

    apply_fun_007baa70_body_accumulator(
        result.body_accumulator,
        result.transformed_record_point,
        result.transformed_response);
    result.applied = true;
    return result;
}

AuxContactPairResult execute_fun_00766510_aux_contact_pair(
    const AuxContactPairInput& input) {

    AuxContactPairResult result{};
    result.body_accumulator = input.body_accumulator;

    for (std::size_t record_index = 0;
         record_index < kAuxContactRecordCount;
         ++record_index) {
        AuxContactResponseInput record_input{};
        record_input.body_frame = input.body_frame;
        record_input.body_transform = input.body_transform;
        record_input.body_accumulator = result.body_accumulator;
        record_input.reference_point = input.reference_point;
        record_input.record = input.records[record_index];

        result.records[record_index] =
            execute_fun_00758fc0_aux_contact_response(record_input);
        result.body_accumulator =
            result.records[record_index].body_accumulator;
        if (result.records[record_index].applied) {
            ++result.applied_count;
        }
    }

    return result;
}

}  // namespace shift::runtime::physics
