#pragma once

#include "shift_fun_007bf790_caster_record_materialization.hpp"

#include <cstddef>
#include <cstdint>
#include <cstring>
#include <stdexcept>

namespace shift::runtime::physics {

inline constexpr const char* kFun007bf790VehicleLoadDataCasterBindingFormat =
    "SHIFT.Fun007bf790VehicleLoadDataCasterBinding/1";

inline constexpr std::size_t kVehicleLoadDataOwnerPointerOffset = 0x66b4u;
inline constexpr std::size_t kVehicleLoadDataAllocationSize = 0x3848u;
inline constexpr std::size_t kVehicleLoadDataCasterMinimumSize =
    kFun007bf790RightCasterSettingOffset + sizeof(double);

struct Fun007bf790VehicleLoadDataSnapshotView {
    const std::uint8_t* bytes = nullptr;
    std::size_t size = 0u;
    std::int32_t left_prior_count = 0;
    std::int32_t right_prior_count = 0;
};

inline double read_fun_007bf790_vehicle_load_data_f64_le(
    const Fun007bf790VehicleLoadDataSnapshotView& view,
    std::size_t offset) {
    if (view.bytes == nullptr || offset > view.size ||
        view.size - offset < sizeof(double)) {
        throw std::out_of_range(
            "FUN_007bf790 VehicleLoadData caster read outside snapshot");
    }

    std::uint64_t bits = 0u;
    for (std::size_t lane = 0; lane < sizeof(double); ++lane) {
        bits |= static_cast<std::uint64_t>(view.bytes[offset + lane])
                << (lane * 8u);
    }

    double value = 0.0;
    static_assert(sizeof(value) == sizeof(bits));
    std::memcpy(&value, &bits, sizeof(value));
    return value;
}

inline Fun007bf790CasterPairInput
materialize_fun_007bf790_caster_input_from_vehicle_load_data(
    const Fun007bf790VehicleLoadDataSnapshotView& view) {
    if (view.size < kVehicleLoadDataCasterMinimumSize) {
        throw std::out_of_range(
            "FUN_007bf790 VehicleLoadData snapshot too small for caster fields");
    }

    Fun007bf790CasterPairInput input{};
    input.left.range = {
        read_fun_007bf790_vehicle_load_data_f64_le(
            view, kFun007bf790LeftCasterRangeOffset + 0x00u),
        read_fun_007bf790_vehicle_load_data_f64_le(
            view, kFun007bf790LeftCasterRangeOffset + 0x08u),
        read_fun_007bf790_vehicle_load_data_f64_le(
            view, kFun007bf790LeftCasterRangeOffset + 0x10u),
    };
    input.left.setting = read_fun_007bf790_vehicle_load_data_f64_le(
        view, kFun007bf790LeftCasterSettingOffset);
    input.left.prior_count = view.left_prior_count;

    input.right.range = {
        read_fun_007bf790_vehicle_load_data_f64_le(
            view, kFun007bf790RightCasterRangeOffset + 0x00u),
        read_fun_007bf790_vehicle_load_data_f64_le(
            view, kFun007bf790RightCasterRangeOffset + 0x08u),
        read_fun_007bf790_vehicle_load_data_f64_le(
            view, kFun007bf790RightCasterRangeOffset + 0x10u),
    };
    input.right.setting = read_fun_007bf790_vehicle_load_data_f64_le(
        view, kFun007bf790RightCasterSettingOffset);
    input.right.prior_count = view.right_prior_count;

    validate_fun_007bf790_caster_config(input.left);
    validate_fun_007bf790_caster_config(input.right);
    return input;
}

inline Fun007bf790CasterPairResult
materialize_fun_007bf790_caster_records_from_vehicle_load_data(
    const Fun007bf790VehicleLoadDataSnapshotView& view) {
    return materialize_fun_007bf790_caster_records(
        materialize_fun_007bf790_caster_input_from_vehicle_load_data(view));
}

static_assert(kVehicleLoadDataOwnerPointerOffset == 0x66b4u);
static_assert(kVehicleLoadDataAllocationSize == 0x3848u);
static_assert(kVehicleLoadDataCasterMinimumSize == 0x03e8u);

}  // namespace shift::runtime::physics
