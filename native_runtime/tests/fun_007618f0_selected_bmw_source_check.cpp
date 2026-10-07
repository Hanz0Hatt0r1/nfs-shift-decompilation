#include "shift_fun_007618f0_selected_bmw_source.hpp"

#include <bit>
#include <cstdint>
#include <iostream>
#include <stdexcept>

using namespace shift::runtime::physics;

namespace {

void require(bool condition, const char* message) {
    if (!condition) {
        throw std::runtime_error(message);
    }
}

}  // namespace

int main() {
    try {
        require(kBmwM3E36CgHeightF32Bits == 0x3e8f5c29u,
                "BMW CGHeight f32 bits drift");
        require(kSelectedNormalCgHeightScaleF32Bits == 0x3f19999au,
                "selected normal CGHeight scale bits drift");
        require(kSelectedDerivedCgHeightF64Bits == 0x3fc5810634bc6a80ull,
                "selected derived CGHeight f64 bits drift");
        require(kIncorrectF32ProductThenWidenF64Bits == 0x3fc5810640000000ull,
                "precision witness drift");
        require(kSelectedDerivedCgHeightF64Bits !=
                    kIncorrectF32ProductThenWidenF64Bits,
                "retail x87 path collapsed to host f32-product path");

        const float cg_height = std::bit_cast<float>(kBmwM3E36CgHeightF32Bits);
        const float scale = std::bit_cast<float>(kSelectedNormalCgHeightScaleF32Bits);
        const double source_order_product =
            static_cast<double>(cg_height) * static_cast<double>(scale);
        require(std::bit_cast<std::uint64_t>(source_order_product) ==
                    kSelectedDerivedCgHeightF64Bits,
                "binary32 operand product does not match retail qword store");

        const auto selected = selected_bmw_m3_e36_fun_007618f0_source();
        require(std::bit_cast<std::uint64_t>(selected.source_scalar_0338) ==
                    kSelectedDerivedCgHeightF64Bits,
                "selected +0x338 source scalar drift");
        require(std::bit_cast<std::uint64_t>(selected.source_vec_0918[0]) ==
                    kBmwM3E36FwCenterXF64Bits,
                "selected FWCenter X drift");
        require(std::bit_cast<std::uint64_t>(selected.source_vec_0918[1]) ==
                    kBmwM3E36FwCenterYF64Bits,
                "selected FWCenter Y drift");
        require(std::bit_cast<std::uint64_t>(selected.source_vec_0918[2]) ==
                    kBmwM3E36FwCenterZF64Bits,
                "selected FWCenter Z drift");

        std::cout
            << "{\"format\":\"" << kFun007618f0SelectedBmwSourceFormat << "\","
            << "\"ready\":true,"
            << "\"vehicle_load_data_owner\":true,"
            << "\"derived_cg_height_bits\":\"0x3fc5810634bc6a80\","
            << "\"naive_f32_widen_bits\":\"0x3fc5810640000000\","
            << "\"fwcenter\":[0.0,-0.1,-0.5]}\n";
        return 0;
    } catch (const std::exception& exc) {
        std::cerr << exc.what() << '\n';
        return 1;
    }
}
