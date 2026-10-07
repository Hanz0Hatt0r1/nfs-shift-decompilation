#include "shift_fun_00765c40_external_pass_result.hpp"
#include "shift_fun_00765c40_selected_bmw_query_fallback.hpp"

#include <cstdint>
#include <cstring>
#include <iostream>
#include <stdexcept>

namespace {

using namespace shift::runtime::physics;

void require(bool condition, const char* message) {
    if (!condition) {
        throw std::runtime_error(message);
    }
}

std::uint64_t f64_bits(double value) {
    std::uint64_t bits = 0u;
    std::memcpy(&bits, &value, sizeof(bits));
    return bits;
}

}  // namespace

int main() {
    try {
        require(kFun00756bb0CallerCacheOffset == 0x38dcu,
                "FUN_00756bb0 cache offset drift");
        require(kFun00756bb0CallerFallbackOffset == 0x38e8u,
                "FUN_00756bb0 fallback offset drift");
        require(kFun00756bb0FrontWingRecordOffset == 0x6a0u &&
                    kFun00756bb0FWMaxHeightBaseOffset == 0x6a4u &&
                    kFun00756bb0FWMaxHeightEvaluatedOffset == 0x6a8u,
                "FUN_00756bb0 FRONTWING FWMaxHeight offsets drift");
        require(kBmwM3E36FWMaxHeightF32Bits == 0x3dcccccdu,
                "BMW M3 E36 FWMaxHeight f32 bits drift");

        const double fallback =
            selected_bmw_m3_e36_fun_00765c40_query_fallback();
        require(f64_bits(fallback) == kBmwM3E36QueryFallbackF64Bits &&
                    f64_bits(fallback) == 0x3fb99999a0000000ull,
                "BMW M3 E36 +0x38e8 f32-to-f64 widening drift");

        Fun00765c40ExternalPassInput generic{};
        require(!generic.selected_bmw_miss_fallback().has_value(),
                "generic residual request incorrectly claimed BMW setup state");

        Fun00765c40ExternalPassInput selected{};
        selected.world_position = CollisionQueryVector3d{1.0, 2.0, 3.0};
        const auto owned = selected.selected_bmw_miss_fallback();
        require(owned.has_value() && f64_bits(*owned) == 0x3fb99999a0000000ull,
                "selected BMW request did not expose exact native fallback");

        Fun00765c40QueryInputBoundary query{};
        query.world_position = *selected.world_position;
        query.cached_handle = std::nullopt;
        query.miss_fallback = *owned;
        const Fun00765c40ExternalPassResult good{
            Fun00765c40LoadTerms{1.0, 2.0, 3.0, 4.0}, query, std::nullopt};
        validate_fun_00765c40_external_pass_result(selected, good);

        bool mismatch_rejected = false;
        try {
            auto bad = good;
            bad.query_input.miss_fallback = 0.1;
            validate_fun_00765c40_external_pass_result(selected, bad);
        } catch (const std::invalid_argument&) {
            mismatch_rejected = true;
        }
        require(mismatch_rejected,
                "selected BMW provider accepted non-source +0x38e8 value");

        std::cout
            << "{\"format\":\"" << kFun00765c40SelectedBmwQueryFallbackFormat << "\","
            << "\"ready\":true,"
            << "\"fw_max_height_f32_bits\":\"0x3dcccccd\","
            << "\"fallback_f64_bits\":\"0x3fb99999a0000000\","
            << "\"selected_pre_call_owned\":true,"
            << "\"generic_compatibility_path_preserved\":true}\n";
        return 0;
    } catch (const std::exception& exc) {
        std::cerr << exc.what() << '\n';
        return 1;
    }
}
