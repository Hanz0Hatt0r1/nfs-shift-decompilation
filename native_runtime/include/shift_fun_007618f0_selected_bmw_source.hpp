#pragma once

#include "shift_collision_query_contract.hpp"

#include <bit>
#include <cstdint>

namespace shift::runtime::physics {

inline constexpr const char* kFun007618f0SelectedBmwSourceFormat =
    "SHIFT.Fun007618f0SelectedBMWSource/1";

// Retail BMW M3 E36 CDF: CGHeight=0.280. FUN_007bfbe0 evaluates the
// interpolated value and explicitly spills it to f32 before reloading it.
inline constexpr std::uint32_t kBmwM3E36CgHeightF32Bits = 0x3e8f5c29u;

// Selected Silverstone+BMW session: normal physics mode, Player Difficulty=1.
// physicstweaker.xml CGHeight Scale index 1 is 0.6 and the machine reads the
// scale as an f32 DWORD from DAT_00c13130 + difficulty*4.
inline constexpr std::uint32_t kSelectedNormalCgHeightScaleF32Bits = 0x3f19999au;

// PC 0x007bff14..0x007bff5a:
//   FUN_007a6be0
//   fstp dword local
//   fld  dword local
//   fmul dword [normal_scale + difficulty*4]
//   fstp qword [VehicleLoadData+0x338]
// There is no post-multiply f32 spill. Multiplying two binary32 operands has at
// most 48 significant bits, so the product is exact in x87 extended precision
// and remains exact when stored to binary64.
inline constexpr std::uint64_t kSelectedDerivedCgHeightF64Bits =
    0x3fc5810634bc6a80ull;

// A tempting host path that rounds the product back through f32 would instead
// widen to this different binary64 value. Keep it as a regression witness.
inline constexpr std::uint64_t kIncorrectF32ProductThenWidenF64Bits =
    0x3fc5810640000000ull;

// Exact BMW_M3_E36.bff member vehicles\physics\chassis\bmw_m3_e36.cdf:
//   FWCenter=(0.00, -0.100, -0.50)
// FUN_007c0a20 writes the three components to the front-wing subrecord at
// +0x278/+0x280/+0x288, absolute VehicleLoadData +0x918/+0x920/+0x928.
inline constexpr std::uint64_t kBmwM3E36FwCenterXF64Bits = 0x0000000000000000ull;
inline constexpr std::uint64_t kBmwM3E36FwCenterYF64Bits = 0xbfb999999999999aull;
inline constexpr std::uint64_t kBmwM3E36FwCenterZF64Bits = 0xbfe0000000000000ull;

struct Fun007618f0SelectedBmwSource {
    double source_scalar_0338 = 0.0;
    CollisionQueryVector3d source_vec_0918{};
};

inline Fun007618f0SelectedBmwSource selected_bmw_m3_e36_fun_007618f0_source() {
    Fun007618f0SelectedBmwSource result{};
    result.source_scalar_0338 =
        std::bit_cast<double>(kSelectedDerivedCgHeightF64Bits);
    result.source_vec_0918 = {
        std::bit_cast<double>(kBmwM3E36FwCenterXF64Bits),
        std::bit_cast<double>(kBmwM3E36FwCenterYF64Bits),
        std::bit_cast<double>(kBmwM3E36FwCenterZF64Bits),
    };
    return result;
}

}  // namespace shift::runtime::physics
