#include "shift_fun_00766510_direct_accumulator_surface.hpp"

#include <iostream>
#include <stdexcept>

namespace {

using namespace shift::runtime::physics;

void require(bool condition, const char* message) {
    if (!condition) {
        throw std::runtime_error(message);
    }
}

}  // namespace

int main() {
    try {
        require(kFun00766510CallerAccumulatorOffsets[0] == 0x40a0u &&
                    kFun00766510CallerAccumulatorOffsets[1] == 0x40a8u &&
                    kFun00766510CallerAccumulatorOffsets[2] == 0x40b0u,
                "caller accumulator offsets drift");
        require(kFun00766510DirectAccumulatorSites.size() == 4u,
                "direct accumulator site count drift");
        require(kFun00766510DirectAccumulatorSites[0].source_line == 759558u &&
                    kFun00766510DirectAccumulatorSites[0].conditional,
                "early direct accumulator site drift");
        require(kFun00766510DirectAccumulatorSites[1].source_line == 759621u &&
                    kFun00766510DirectAccumulatorSites[1].conditional,
                "optional direct accumulator site drift");
        require(kFun00766510DirectAccumulatorSites[2].source_line == 759692u &&
                    !kFun00766510DirectAccumulatorSites[2].conditional,
                "primary direct accumulator site drift");
        require(kFun00766510DirectAccumulatorSites[3].source_line == 759732u &&
                    kFun00766510DirectAccumulatorSites[3].conditional,
                "later direct accumulator site drift");

        BodyAccumulatorVector3d accumulator{1.0, 2.0, 3.0};
        apply_fun_00766510_direct_accumulator_delta(
            accumulator,
            BodyAccumulatorVector3d{4.0, -1.0, 2.0});
        require(accumulator[0] == 5.0 &&
                    accumulator[1] == 1.0 &&
                    accumulator[2] == 5.0,
                "single direct accumulator delta application drift");

        const auto cross = execute_fun_00753650_cross_product(
            BodyAccumulatorVector3d{1.0, 0.0, 0.0},
            BodyAccumulatorVector3d{0.0, 2.0, 0.0});
        require(cross[0] == 0.0 && cross[1] == 0.0 && cross[2] == 2.0,
                "FUN_00753650 primitive witness drift");
        apply_fun_00766510_direct_accumulator_delta(accumulator, cross);
        require(accumulator[2] == 7.0,
                "cross-product direct accumulator handoff drift");

        std::cout
            << "{\"format\":\"" << kFun00766510DirectAccumulatorSurfaceFormat << "\","
            << "\"ready\":true,"
            << "\"direct_site_count\":4,"
            << "\"whole_accumulator_closed\":false,"
            << "\"contact_response_provider_removed\":false}\n";
        return 0;
    } catch (const std::exception& exc) {
        std::cerr << exc.what() << '\n';
        return 1;
    }
}
