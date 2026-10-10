#pragma once

#include "shift_fun_007bf790_vehicle_load_data_caster_binding.hpp"

#include <cstddef>
#include <cstdint>
#include <stdexcept>

namespace shift::runtime::physics {

inline constexpr const char* kFun007bf790VehicleLoadOwnerSnapshotIdentityFormat =
    "SHIFT.Fun007bf790VehicleLoadOwnerSnapshotIdentity/1";
inline constexpr std::size_t kFun007bf790RetailPointerWidth = 4u;

// Two byte images are supplied by the caller. The native runtime owns only
// the pointer-field read and association check; it does not acquire memory,
// dereference a retail address, or prove either snapshot's lifetime.
struct Fun007bf790VehicleLoadOwnerSnapshotInput {
    const std::uint8_t* hdvehicle_bytes = nullptr;
    std::size_t hdvehicle_size = 0u;
    std::uint32_t supplied_load_data_address = 0u;
    Fun007bf790VehicleLoadDataSnapshotView load_data{};
};

inline std::uint32_t validate_fun_007bf790_vehicle_load_owner_snapshot(
    const Fun007bf790VehicleLoadOwnerSnapshotInput& input) {
    if (input.hdvehicle_bytes == nullptr ||
        input.hdvehicle_size < kVehicleLoadDataOwnerPointerOffset ||
        input.hdvehicle_size - kVehicleLoadDataOwnerPointerOffset <
            kFun007bf790RetailPointerWidth) {
        throw std::out_of_range(
            "FUN_007bf790 HDVehicle snapshot lacks +0x66b4 owner field");
    }

    std::uint32_t address = 0u;
    for (std::size_t lane = 0; lane < kFun007bf790RetailPointerWidth; ++lane) {
        address |= static_cast<std::uint32_t>(
            input.hdvehicle_bytes[kVehicleLoadDataOwnerPointerOffset + lane])
            << (8u * lane);
    }
    if (address == 0u || input.supplied_load_data_address == 0u ||
        address != input.supplied_load_data_address) {
        throw std::invalid_argument(
            "FUN_007bf790 VehicleLoadData pointer identity mismatch");
    }
    if (input.load_data.bytes == nullptr ||
        input.load_data.size < kVehicleLoadDataCasterMinimumSize ||
        input.load_data.size > kVehicleLoadDataAllocationSize) {
        throw std::out_of_range(
            "FUN_007bf790 supplied VehicleLoadData image outside allocation");
    }
    return address;
}

inline Fun007bf790CasterPairInput
materialize_fun_007bf790_owner_checked_caster_input(
    const Fun007bf790VehicleLoadOwnerSnapshotInput& input) {
    (void)validate_fun_007bf790_vehicle_load_owner_snapshot(input);
    return materialize_fun_007bf790_caster_input_from_vehicle_load_data(
        input.load_data);
}

inline Fun007bf790CasterPairResult
materialize_fun_007bf790_owner_checked_caster_records(
    const Fun007bf790VehicleLoadOwnerSnapshotInput& input) {
    return materialize_fun_007bf790_caster_records(
        materialize_fun_007bf790_owner_checked_caster_input(input));
}

static_assert(kVehicleLoadDataOwnerPointerOffset == 0x66b4u);
static_assert(kFun007bf790RetailPointerWidth == 4u);
static_assert(kVehicleLoadDataAllocationSize == 0x3848u);

}  // namespace shift::runtime::physics
