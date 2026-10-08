#include "shift_fun_007af040_column_transform.hpp"

#include <cstdint>
#include <cstring>
#include <iostream>
#include <limits>
#include <stdexcept>

namespace {

using namespace shift::runtime::physics;

void require(bool condition, const char* message) {
    if (!condition) throw std::runtime_error(message);
}

std::uint32_t f32_bits(double value) {
    const float narrowed = static_cast<float>(value);
    std::uint32_t bits = 0u;
    std::memcpy(&bits, &narrowed, sizeof(bits));
    return bits;
}

}  // namespace

int main() {
    try {
        ConstraintRefreshFrame3f matrix = {
            11.0f, 3.1415927f, 12.0f,
            13.0f, -2.7182817f, 14.0f,
            15.0f, 0.33333334f, 16.0f,
        };
        const auto result = execute_fun_007af040_column_transform(
            matrix, 1.00000006);
        require(f32_bits(result[0]) == 0x40490fddu,
                "FUN_007af040 X source-f32 product drift");
        require(f32_bits(result[1]) == 0xc02df855u,
                "FUN_007af040 Y source-f32 product drift");
        require(f32_bits(result[2]) == 0x3eaaaaacu,
                "FUN_007af040 Z source-f32 product drift");

        bool nonfinite_rejected = false;
        try {
            (void)execute_fun_007af040_column_transform(
                matrix, std::numeric_limits<double>::infinity());
        } catch (const std::invalid_argument&) {
            nonfinite_rejected = true;
        }
        require(nonfinite_rejected, "FUN_007af040 accepted non-finite scalar");

        std::cout
            << "{\"format\":\"" << kFun007af040ColumnTransformFormat << "\","
            << "\"ready\":true,"
            << "\"matrix_column_offsets\":[\"0x04\",\"0x10\",\"0x1c\"],"
            << "\"scalar_f64_to_f32_narrowing\":true,"
            << "\"product_f32_then_f64_widening\":true}\n";
        return 0;
    } catch (const std::exception& exc) {
        std::cerr << exc.what() << '\n';
        return 1;
    }
}
