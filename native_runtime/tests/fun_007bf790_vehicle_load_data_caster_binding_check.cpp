#include "shift_fun_007bf790_vehicle_load_data_caster_binding.hpp"

#include <cmath>
#include <cstdint>
#include <cstring>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <vector>

namespace {

using namespace shift::runtime::physics;

void require(bool condition, const char* message) {
    if (!condition) {
        throw std::runtime_error(message);
    }
}

void put_f64_le(std::vector<std::uint8_t>& bytes,
                std::size_t offset,
                double value) {
    std::uint64_t bits = 0u;
    static_assert(sizeof(bits) == sizeof(value));
    std::memcpy(&bits, &value, sizeof(bits));
    for (std::size_t lane = 0; lane < sizeof(bits); ++lane) {
        bytes.at(offset + lane) = static_cast<std::uint8_t>(
            (bits >> (lane * 8u)) & 0xffu);
    }
}

}  // namespace

int main() {
    try {
        require(kVehicleLoadDataOwnerPointerOffset == 0x66b4u,
                "VehicleLoadData owner pointer offset drift");
        require(kVehicleLoadDataAllocationSize == 0x3848u,
                "VehicleLoadData allocation size drift");
        require(kVehicleLoadDataCasterMinimumSize == 0x03e8u,
                "VehicleLoadData caster minimum snapshot size drift");

        std::vector<std::uint8_t> bytes(kVehicleLoadDataCasterMinimumSize, 0u);
        const double left_slope_degrees =
            0.125 / kFun007bf790CasterDegreesToRadians;

        put_f64_le(bytes, 0x01e8u, 0.0);
        put_f64_le(bytes, 0x01f0u, left_slope_degrees);
        put_f64_le(bytes, 0x01f8u, 5.9);
        put_f64_le(bytes, 0x03d8u, 2.9);

        put_f64_le(bytes, 0x0200u, 1.0);
        put_f64_le(bytes, 0x0208u, 2.0);
        put_f64_le(bytes, 0x0210u, 4.8);
        put_f64_le(bytes, 0x03e0u, 9.7);

        const Fun007bf790VehicleLoadDataSnapshotView view{
            bytes.data(), bytes.size(), 91, 73};
        const auto input =
            materialize_fun_007bf790_caster_input_from_vehicle_load_data(view);

        require(input.left.range == Fun007bf790CasterRange{
                    0.0, left_slope_degrees, 5.9},
                "VehicleLoadData left caster range binding drift");
        require(input.left.setting == 2.9 && input.left.prior_count == 91,
                "VehicleLoadData left caster setting/count binding drift");
        require(input.right.range == Fun007bf790CasterRange{1.0, 2.0, 4.8},
                "VehicleLoadData right caster range binding drift");
        require(input.right.setting == 9.7 && input.right.prior_count == 73,
                "VehicleLoadData right caster setting/count binding drift");

        const auto records =
            materialize_fun_007bf790_caster_records_from_vehicle_load_data(view);
        require(records.left.count == 5 && records.left.coefficient == 2,
                "VehicleLoadData left caster downstream materialization drift");
        require(records.left.base_value == 0.0 &&
                    records.left.slope_value == 0.125,
                "VehicleLoadData left caster scaling drift");
        require(records.right.count == 4 && records.right.coefficient == 3,
                "VehicleLoadData right caster downstream clamp drift");

        bool rejected_short_snapshot = false;
        try {
            const Fun007bf790VehicleLoadDataSnapshotView short_view{
                bytes.data(), 0x03e7u, 0, 0};
            (void)materialize_fun_007bf790_caster_input_from_vehicle_load_data(
                short_view);
        } catch (const std::out_of_range&) {
            rejected_short_snapshot = true;
        }
        require(rejected_short_snapshot,
                "VehicleLoadData short caster snapshot failed open");

        bool rejected_null_snapshot = false;
        try {
            const Fun007bf790VehicleLoadDataSnapshotView null_view{
                nullptr, bytes.size(), 0, 0};
            (void)materialize_fun_007bf790_caster_input_from_vehicle_load_data(
                null_view);
        } catch (const std::out_of_range&) {
            rejected_null_snapshot = true;
        }
        require(rejected_null_snapshot,
                "VehicleLoadData null caster snapshot failed open");

        put_f64_le(bytes, 0x0208u, std::numeric_limits<double>::infinity());
        bool rejected_non_finite = false;
        try {
            const Fun007bf790VehicleLoadDataSnapshotView bad_view{
                bytes.data(), bytes.size(), 0, 0};
            (void)materialize_fun_007bf790_caster_input_from_vehicle_load_data(
                bad_view);
        } catch (const std::invalid_argument&) {
            rejected_non_finite = true;
        }
        require(rejected_non_finite,
                "VehicleLoadData non-finite caster source failed open");

        std::cout
            << "{\"format\":\""
            << kFun007bf790VehicleLoadDataCasterBindingFormat << "\","
            << "\"ready\":true,"
            << "\"vehicle_load_data_owner_offset\":26292,"
            << "\"caster_offsets_native_bound\":true,"
            << "\"little_endian_f64_reads_native\":true,"
            << "\"vehicle_load_data_snapshot_lifetime_internalized\":false}\n";
        return 0;
    } catch (const std::exception& exc) {
        std::cerr << exc.what() << '\n';
        return 1;
    }
}
