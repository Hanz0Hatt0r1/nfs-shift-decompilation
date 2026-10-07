#include "shift_body_record_adapter.hpp"
#include "shift_fun_007594e0_steering.hpp"

#include <array>
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
    for (std::size_t byte = 0u; byte < 4u; ++byte) {
        bytes[offset + byte] =
            static_cast<std::uint8_t>((value >> (byte * 8u)) & 0xffu);
    }
}

void put_u64_le(
    std::vector<std::uint8_t>& bytes,
    std::size_t offset,
    std::uint64_t value) {
    for (std::size_t byte = 0u; byte < 8u; ++byte) {
        bytes[offset + byte] =
            static_cast<std::uint8_t>((value >> (byte * 8u)) & 0xffu);
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

std::uint32_t bits_of(float value) {
    std::uint32_t bits = 0u;
    std::memcpy(&bits, &value, sizeof(bits));
    return bits;
}

std::vector<std::uint8_t> make_body(
    double vx,
    double vy,
    double vz,
    const std::array<float, 9>& basis) {
    std::vector<std::uint8_t> bytes(kBodyRecordSize, 0u);
    put_f64(bytes, 0x78u, vx);
    put_f64(bytes, 0x80u, vy);
    put_f64(bytes, 0x88u, vz);
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
        const auto identity_result =
            execute_fun_007594e0_steering(make_body(4.0, 5.0, 6.0, identity));
        require(identity_result.local_velocity_x == 4.0 &&
                    identity_result.local_velocity_z == 6.0,
                "Phase 720 identity basis transform mismatch");
        require(identity_result.planar_squared == 52.0,
                "Phase 720 planar square sum mismatch");
        require(identity_result.angle_gate_open && identity_result.x87_fpatan_used,
                "Phase 720 angle gate did not open");
        require(bits_of(identity_result.steering) == 0xc0236e05u,
                "Phase 720 identity FPATAN f32 bits mismatch");

        const std::array<float, 9> rotate_y_90 = {
            0.0f, 0.0f, 1.0f,
            0.0f, 1.0f, 0.0f,
            -1.0f, 0.0f, 0.0f,
        };
        const auto rotated_result =
            execute_fun_007594e0_steering(make_body(4.0, 5.0, 6.0, rotate_y_90));
        require(rotated_result.local_velocity_x == -6.0 &&
                    rotated_result.local_velocity_z == 4.0,
                "Phase 720 transpose-basis transform mismatch");
        require(bits_of(rotated_result.steering) == 0x400a29c3u,
                "Phase 720 rotated FPATAN f32 bits mismatch");

        const auto gated_result =
            execute_fun_007594e0_steering(make_body(0.1, 9.0, 0.2, identity));
        require(!gated_result.angle_gate_open && !gated_result.x87_fpatan_used,
                "Phase 720 low planar magnitude failed retail gate");
        require(bits_of(gated_result.steering) == 0x00000000u,
                "Phase 720 low planar magnitude did not return +0.0f");

        bool malformed_rejected = false;
        try {
            (void)execute_fun_007594e0_steering(std::vector<std::uint8_t>(16u, 0u));
        } catch (const std::invalid_argument&) {
            malformed_rejected = true;
        }
        require(malformed_rejected, "Phase 720 malformed BODY failed open");

        auto nonfinite = make_body(4.0, 5.0, 6.0, identity);
        put_f64(nonfinite, 0x78u, std::numeric_limits<double>::infinity());
        bool nonfinite_rejected = false;
        try {
            (void)execute_fun_007594e0_steering(nonfinite);
        } catch (const std::invalid_argument&) {
            nonfinite_rejected = true;
        }
        require(nonfinite_rejected, "Phase 720 non-finite BODY failed open");

        std::cout
            << "{\"format\":\"" << kNativeFun007594e0SteeringFormat
            << "\",\"retail_basis_transpose\":true"
            << ",\"retail_planar_gate_0_1\":true"
            << ",\"retail_x87_fpatan\":true"
            << ",\"host_atan2_used\":false"
            << ",\"identity_f32_bits\":\"0xc0236e05\""
            << ",\"rotated_f32_bits\":\"0x400a29c3\"}"
            << std::endl;
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << std::endl;
        return 1;
    }
}
