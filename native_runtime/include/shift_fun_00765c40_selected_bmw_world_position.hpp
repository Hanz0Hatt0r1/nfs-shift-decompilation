#pragma once

#include "shift_body_record_adapter.hpp"
#include "shift_fun_007618f0_local_sample_producer.hpp"
#include "shift_fun_007618f0_selected_bmw_source.hpp"
#include "shift_fun_007618f0_wheel_body_origin_ownership.hpp"
#include "shift_fun_00765c40_world_position_transform.hpp"

#include <algorithm>
#include <stdexcept>
#include <vector>

namespace shift::runtime::physics {

inline constexpr const char* kFun00765c40SelectedBmwWorldPositionFormat =
    "SHIFT.Fun00765c40SelectedBMWWorldPosition/1";

struct Fun00765c40SelectedBmwWorldPositionResult {
    Fun007618f0WheelBodyOriginOwnershipResult wheel_ownership{};
    Fun007618f0LocalSampleProducerResult local_sample{};
    Fun00765c40WorldPositionTransformResult world_transform{};
};

inline BodyRecordBytes fun_00765c40_selected_bmw_body0_record(
    const std::vector<std::uint8_t>& current_body_bytes) {
    if (current_body_bytes.size() < kBodyRecordSize) {
        throw std::invalid_argument(
            "FUN_00765c40 selected BMW world-position join requires BODY0");
    }
    BodyRecordBytes body0{};
    std::copy_n(current_body_bytes.begin(), kBodyRecordSize, body0.begin());
    return body0;
}

// Selected-session composition of already source-backed stages:
//   Phase737: current persistent BMW BODY3/BODY4 origins
//   Phase738: exact selected VehicleLoadData +0x338/+0x918 inputs
//   Phase728: FUN_007618f0 local HDVehicle+0x3938 sample
//   Phase727: current BODY0 basis/origin -> FUN_00765c40 world position
// The caller must pass the authoritative per-pass BODY byte vector. The existing
// FUN_00770e80 current_body_observer publishes that vector before each pass, so
// pass 1 naturally observes the first half-step result.
inline Fun00765c40SelectedBmwWorldPositionResult
execute_fun_00765c40_selected_bmw_world_position(
    const std::vector<std::uint8_t>& current_body_bytes) {
    const auto selected_source = selected_bmw_m3_e36_fun_007618f0_source();

    Fun007618f0RemainingSourceInput remaining{};
    remaining.source_scalar_0338 = selected_source.source_scalar_0338;
    remaining.source_vec_0918 = selected_source.source_vec_0918;

    Fun00765c40SelectedBmwWorldPositionResult result{};
    result.wheel_ownership =
        compose_fun_007618f0_input_from_current_bmw_wheel_bodies(
            current_body_bytes,
            remaining);
    result.local_sample = execute_fun_007618f0_local_sample_producer(
        result.wheel_ownership.producer_input);
    const BodyRecordBytes body0 =
        fun_00765c40_selected_bmw_body0_record(current_body_bytes);
    result.world_transform = execute_fun_00765c40_world_position_transform(
        body0,
        result.local_sample.local_sample_3938);
    return result;
}

}  // namespace shift::runtime::physics
