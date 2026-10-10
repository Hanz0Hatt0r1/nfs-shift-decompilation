#include "shift_fun_007bf790_vehicle_load_owner_snapshot_identity.hpp"

#include <cmath>
#include <cstdint>
#include <cstring>
#include <iostream>
#include <stdexcept>
#include <vector>

using namespace shift::runtime::physics;

namespace {
void require(bool condition, const char* message) {
    if (!condition) throw std::runtime_error(message);
}

void write_f64_le(std::vector<std::uint8_t>& bytes,
                  std::size_t offset, double value) {
    std::uint64_t bits = 0u;
    static_assert(sizeof(bits) == sizeof(value));
    std::memcpy(&bits, &value, sizeof(bits));
    for (std::size_t i = 0; i < 8u; ++i) {
        bytes[offset + i] = static_cast<std::uint8_t>(bits >> (8u * i));
    }
}
}  // namespace

int main() {
    try {
        std::vector<std::uint8_t> vehicle(
            kVehicleLoadDataOwnerPointerOffset + 4u, 0u);
        std::vector<std::uint8_t> load(kVehicleLoadDataCasterMinimumSize, 0u);
        constexpr std::uint32_t address = 0x11223344u;
        for (std::size_t i = 0; i < 4u; ++i) {
            vehicle[kVehicleLoadDataOwnerPointerOffset + i] =
                static_cast<std::uint8_t>(address >> (8u * i));
        }
        write_f64_le(load, kFun007bf790LeftCasterRangeOffset, 10.0);
        write_f64_le(load, kFun007bf790LeftCasterRangeOffset + 8u, 2.0);
        write_f64_le(load, kFun007bf790LeftCasterRangeOffset + 16u, 3.0);
        write_f64_le(load, kFun007bf790LeftCasterSettingOffset, 1.0);
        write_f64_le(load, kFun007bf790RightCasterRangeOffset, 20.0);
        write_f64_le(load, kFun007bf790RightCasterRangeOffset + 8u, 4.0);
        write_f64_le(load, kFun007bf790RightCasterRangeOffset + 16u, 5.0);
        write_f64_le(load, kFun007bf790RightCasterSettingOffset, 2.0);

        Fun007bf790VehicleLoadOwnerSnapshotInput input{};
        input.hdvehicle_bytes = vehicle.data();
        input.hdvehicle_size = vehicle.size();
        input.supplied_load_data_address = address;
        input.load_data = {load.data(), load.size(), 9, 11};
        require(validate_fun_007bf790_vehicle_load_owner_snapshot(input) ==
                    address,
                "owner pointer identity read drift");
        const auto result =
            materialize_fun_007bf790_owner_checked_caster_records(input);
        require(result.left.count == 3 && result.left.coefficient == 1,
                "left caster materialization drift");
        require(result.right.count == 5 && result.right.coefficient == 2,
                "right caster materialization drift");
        require(std::abs(result.left.base_value -
                    10.0 * kFun007bf790CasterDegreesToRadians) < 1e-12,
                "left caster angle scaling drift");

        bool mismatched = false;
        try {
            auto bad = input;
            bad.supplied_load_data_address = 0x44332211u;
            (void)materialize_fun_007bf790_owner_checked_caster_records(bad);
        } catch (const std::invalid_argument&) {
            mismatched = true;
        }
        require(mismatched, "owner pointer mismatch failed open");

        bool short_vehicle = false;
        try {
            auto bad = input;
            bad.hdvehicle_size -= 1u;
            (void)validate_fun_007bf790_vehicle_load_owner_snapshot(bad);
        } catch (const std::out_of_range&) {
            short_vehicle = true;
        }
        require(short_vehicle, "short HDVehicle snapshot failed open");

        bool short_load = false;
        try {
            auto bad = input;
            bad.load_data.size -= 1u;
            (void)materialize_fun_007bf790_owner_checked_caster_input(bad);
        } catch (const std::out_of_range&) {
            short_load = true;
        }
        require(short_load, "short VehicleLoadData snapshot failed open");

        bool zero_pointer = false;
        try {
            auto bad = input;
            bad.supplied_load_data_address = 0u;
            (void)validate_fun_007bf790_vehicle_load_owner_snapshot(bad);
        } catch (const std::invalid_argument&) {
            zero_pointer = true;
        }
        require(zero_pointer, "zero pointer identity failed open");

        bool null_vehicle = false;
        try {
            auto bad = input;
            bad.hdvehicle_bytes = nullptr;
            (void)validate_fun_007bf790_vehicle_load_owner_snapshot(bad);
        } catch (const std::out_of_range&) {
            null_vehicle = true;
        }
        require(null_vehicle, "null HDVehicle snapshot failed open");

        std::cout
            << "{\"format\":\""
            << kFun007bf790VehicleLoadOwnerSnapshotIdentityFormat
            << "\",\"ready\":true,\"owner_pointer_identity_checked\":true,"
               "\"left_right_caster_materialized\":true,"
               "\"snapshot_lifetime_owned\":false,"
               "\"external_provider_count\":7}\n";
        return 0;
    } catch (const std::exception& e) {
        std::cerr << e.what() << '\n';
        return 1;
    }
}
