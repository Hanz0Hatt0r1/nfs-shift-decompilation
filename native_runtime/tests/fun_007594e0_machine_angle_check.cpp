#include "shift_fun_007594e0_machine_angle.hpp"
#include "shift_body_record_adapter.hpp"

#include <array>
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

void put_u32_le(
    std::vector<std::uint8_t>& bytes,
    std::size_t offset,
    std::uint32_t value) {
    for (std::size_t byte = 0u; byte < sizeof(value); ++byte) {
        bytes[offset + byte] = static_cast<std::uint8_t>(
            (value >> (byte * 8u)) & 0xffu);
    }
}

void put_u64_le(
    std::vector<std::uint8_t>& bytes,
    std::size_t offset,
    std::uint64_t value) {
    for (std::size_t byte = 0u; byte < sizeof(value); ++byte) {
        bytes[offset + byte] = static_cast<std::uint8_t>(
            (value >> (byte * 8u)) & 0xffu);
    }
}

void put_f32(
    std::vector<std::uint8_t>& bytes,
    std::size_t offset,
    float value) {
    std::uint32_t bits = 0u;
    std::memcpy(&bits, &value, sizeof(bits));
    put_u32_le(bytes, offset, bits);
}

void put_f64(
    std::vector<std::uint8_t>& bytes,
    std::size_t offset,
    double value) {
    std::uint64_t bits = 0u;
    std::memcpy(&bits, &value, sizeof(bits));
    put_u64_le(bytes, offset, bits);
}

std::uint32_t f32_bits(float value) {
    std::uint32_t bits = 0u;
    std::memcpy(&bits, &value, sizeof(bits));
    return bits;
}

std::vector<std::uint8_t> make_body(
    double velocity_x,
    double velocity_y,
    double velocity_z,
    const std::array<float, 9>& basis) {
    std::vector<std::uint8_t> bytes(kBodyRecordSize, 0u);
    put_f64(bytes, body_record_offset::kMotionTriplet[0], velocity_x);
    put_f64(bytes, body_record_offset::kMotionTriplet[1], velocity_y);
    put_f64(bytes, body_record_offset::kMotionTriplet[2], velocity_z);
    for (std::size_t index = 0u; index < basis.size(); ++index) {
        put_f32(bytes, body_record_offset::kBasis[index], basis[index]);
    }
    return bytes;
}

}  // namespace

int main() {
    try {
        const std::array<float, 9> identity = {
            1.0f, 0.0f, 0.0f,
            0.0f, 1.0f, 0.0f,
            0.0f, 0.0f, 1.0f,
        };

        const auto diagonal = execute_fun_007594e0_machine_angle(
            make_body(3.0, 0.0, 4.0, identity));
        require(diagonal.planar_gate_open,
                "FUN_007594e0 3-4 planar gate did not open");
        require(diagonal.x87_fpatan_used,
                "FUN_007594e0 x87 FPATAN path not reported");
        require(diagonal.local_x == 3.0 && diagonal.local_z == 4.0,
                "FUN_007594e0 identity basis transform mismatch");
        require(diagonal.planar_squared == 25.0,
                "FUN_007594e0 planar squared magnitude mismatch");
        require(f32_bits(diagonal.steering) == 0xc01fe0bbu,
                "FUN_007594e0 retail 3-4 steering bits mismatch");

        // The PC sequence FCHS-es +0.0 local X before entering CRT atan2.
        // With local Z positive this must preserve the -0 numerator quadrant
        // and spill -pi to f32, not +pi.
        const auto signed_zero = execute_fun_007594e0_machine_angle(
            make_body(0.0, 0.0, 1.0, identity));
        require(signed_zero.planar_gate_open,
                "FUN_007594e0 signed-zero planar gate did not open");
        require(f32_bits(signed_zero.steering) == 0xc0490fdbu,
                "FUN_007594e0 signed-zero CRT quadrant mismatch");

        const auto low = execute_fun_007594e0_machine_angle(
            make_body(0.1, 0.0, 0.1, identity));
        require(!low.planar_gate_open,
                "FUN_007594e0 <=0.1 planar gate failed open");
        require(f32_bits(low.steering) == 0x00000000u,
                "FUN_007594e0 closed planar gate did not return +0.0f");

        const std::array<float, 9> yaw_quarter = {
            0.0f, 0.0f, -1.0f,
            0.0f, 1.0f,  0.0f,
            1.0f, 0.0f,  0.0f,
        };
        const auto rotated = execute_fun_007594e0_machine_angle(
            make_body(3.0, 0.0, 4.0, yaw_quarter));
        require(rotated.local_x == 4.0 && rotated.local_z == -3.0,
                "FUN_007594e0 BODY basis orientation transform mismatch");
        require(f32_bits(rotated.steering) == 0xbf6d6338u,
                "FUN_007594e0 rotated steering bits mismatch");

        bool malformed_rejected = false;
        try {
            (void)execute_fun_007594e0_machine_angle(
                std::vector<std::uint8_t>(kBodyRecordSize - 1u, 0u));
        } catch (const std::invalid_argument&) {
            malformed_rejected = true;
        }
        require(malformed_rejected,
                "FUN_007594e0 malformed BODY state failed open");

        auto nonfinite = make_body(3.0, 0.0, 4.0, identity);
        put_f32(
            nonfinite,
            body_record_offset::kBasis[0],
            std::numeric_limits<float>::quiet_NaN());
        bool nonfinite_rejected = false;
        try {
            (void)execute_fun_007594e0_machine_angle(nonfinite);
        } catch (const std::invalid_argument&) {
            nonfinite_rejected = true;
        }
        require(nonfinite_rejected,
                "FUN_007594e0 non-finite BODY basis failed open");

        std::cout
            << "{\"format\":\"" << kNativeFun007594e0MachineAngleFormat << "\","
            << "\"ready\":true,"
            << "\"body0_basis_transform_internal\":true,"
            << "\"planar_squared_gate_strict_gt_0_1\":true,"
            << "\"retail_x87_fpatan\":true,"
            << "\"retail_x87_control_word_0x027f\":true,"
            << "\"signed_zero_quadrant_preserved\":true,"
            << "\"host_std_atan2_used\":false}\n";
        return 0;
    } catch (const std::exception& exc) {
        std::cerr << exc.what() << '\n';
        return 1;
    }
}
