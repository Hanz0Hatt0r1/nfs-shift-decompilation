#include "shift_fun_00769ef0_param3.hpp"

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

std::uint32_t f32_bits(float value) {
    std::uint32_t bits = 0u;
    std::memcpy(&bits, &value, sizeof(bits));
    return bits;
}

std::uint64_t f64_bits(double value) {
    std::uint64_t bits = 0u;
    std::memcpy(&bits, &value, sizeof(bits));
    return bits;
}

void put_f64(std::vector<std::uint8_t>& bytes, std::size_t offset, double value) {
    std::uint64_t bits = f64_bits(value);
    for (std::size_t byte = 0u; byte < sizeof(bits); ++byte) {
        bytes[offset + byte] = static_cast<std::uint8_t>(
            (bits >> (byte * 8u)) & 0xffu);
    }
}

}  // namespace

int main() {
    try {
        require(kFun00769ef0Body0Field120Offset == 0x120u,
                "FUN_00769ef0 BODY0 source offset drift");
        require(f64_bits(kFun00769ef0Param3Gravity) == 0x40239eb851eb851full,
                "FUN_00769ef0 PC f64 9.81 bits drift");

        std::vector<std::uint8_t> body(kBodyRecordSize, 0u);
        put_f64(body, kFun00769ef0Body0Field120Offset, 2.0);
        require(derive_fun_00769ef0_body0_field_120(body) == 2.0,
                "BODY0 +0x120 source read mismatch");

        const Fun00765c40LoadTerms half_terms{
            kFun00769ef0Param3Gravity,
            0.0,
            0.0,
            0.0,
        };
        const auto half = execute_fun_00769ef0_param_3(half_terms, 2.0);
        require(half.param_3 == 0.5f,
                "FUN_00769ef0 param_3 half-scale mismatch");

        const Fun00765c40LoadTerms negative_terms{-1.0, 0.0, 0.0, 0.0};
        require(execute_fun_00769ef0_param_3(negative_terms, 2.0).param_3 == 0.0f,
                "FUN_00769ef0 lower clamp mismatch");

        const Fun00765c40LoadTerms high_terms{1000.0, 0.0, 0.0, 0.0};
        require(execute_fun_00769ef0_param_3(high_terms, 2.0).param_3 == 1.0f,
                "FUN_00769ef0 upper clamp mismatch");

        // Precision witness: this input rounds differently if the old
        // 9.810000419616699 (float32-origin) value is used instead of PC retail
        // f64 bits 0x40239eb851eb851f.
        const Fun00765c40LoadTerms witness_terms{
            2050.5842755333088,
            0.0,
            0.0,
            0.0,
        };
        const auto witness = execute_fun_00769ef0_param_3(
            witness_terms,
            231.76745665616602);
        require(f32_bits(witness.param_3) == 0x3f66e29eu,
                "FUN_00769ef0 exact f64 gravity precision witness mismatch");

        bool zero_rejected = false;
        try {
            (void)execute_fun_00769ef0_param_3(half_terms, 0.0);
        } catch (const std::invalid_argument&) {
            zero_rejected = true;
        }
        require(zero_rejected, "zero BODY0 +0x120 failed open");

        bool nonfinite_rejected = false;
        try {
            const Fun00765c40LoadTerms bad{
                std::numeric_limits<double>::quiet_NaN(), 0.0, 0.0, 0.0};
            (void)execute_fun_00769ef0_param_3(bad, 2.0);
        } catch (const std::invalid_argument&) {
            nonfinite_rejected = true;
        }
        require(nonfinite_rejected, "non-finite load term failed open");

        std::cout
            << "{\"format\":\"" << kFun00769ef0Param3Format << "\","
            << "\"ready\":true,"
            << "\"body_field_offset\":\"BODY0+0x120\","
            << "\"gravity_bits\":\"0x40239eb851eb851f\","
            << "\"load_term_count\":4,"
            << "\"f32_spill_before_clamp\":true,"
            << "\"precision_witness_locked\":true,"
            << "\"zero_denominator_fail_closed\":true}\n";
        return 0;
    } catch (const std::exception& exc) {
        std::cerr << exc.what() << '\n';
        return 1;
    }
}
