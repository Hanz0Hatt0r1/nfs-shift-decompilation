#include "shift_fun_00769640_trig_source_writer.hpp"
#include "shift_fun_007c5a20_trig_record_materializer.hpp"

#include <cmath>
#include <iostream>
#include <limits>
#include <stdexcept>

namespace {

using namespace shift::runtime::physics;

void require(bool condition, const char* message) {
    if (!condition) {
        throw std::runtime_error(message);
    }
}

bool nearly_equal(double left, double right, double epsilon = 1e-15) {
    return std::abs(left - right) <= epsilon;
}

}  // namespace

int main() {
    try {
        require(kFun007c5a20MaterializerStart == 0x007c5a20u &&
                    kFun007c5a20MaterializerEnd == 0x007c5ab8u,
                "FUN_007c5a20 materializer machine span drift");
        require(kFun007bf790SelectedCallsStart == 0x007bf983u &&
                    kFun007bf790SelectedCallsEnd == 0x007bf9d3u,
                "FUN_007bf790 selected-call span drift");
        require(kFun007bf790SourceVectorOffsets ==
                    std::array<std::size_t, 2>{0x11d0u, 0x11e8u},
                "FUN_007bf790 selected source-vector offsets drift");
        require(kFun007bf790SelectorOffsets ==
                    std::array<std::size_t, 2>{0x13c0u, 0x13c8u},
                "FUN_007bf790 selected selector offsets drift");
        require(kFun007bf790DestinationRecordOffsets ==
                    std::array<std::size_t, 2>{0x1188u, 0x11d8u},
                "FUN_007bf790 selected destination-record offsets drift");

        const auto materialized = materialize_fun_007c5a20_trig_record({
            {10.0, 20.0, 4.0},
            2.9,
            99,
        });
        require(materialized.count == 4,
                "FUN_007c5a20 nonzero source must refresh count");
        require(materialized.current_index == 2,
                "FUN_007c5a20 selector truncation drift");
        require(nearly_equal(
                    materialized.base_value,
                    10.0 * kFun007c5a20SelectedTrigScale),
                "FUN_007c5a20 selected base scaling drift");
        require(nearly_equal(
                    materialized.slope_value,
                    20.0 * kFun007c5a20SelectedTrigScale),
                "FUN_007c5a20 selected slope scaling drift");

        const auto high_selector = materialize_fun_007c5a20_trig_record({
            {1.0, 2.0, 4.0},
            99.0,
            0,
        });
        require(high_selector.current_index == 3,
                "FUN_007c5a20 upper selector clamp drift");

        const auto negative_selector = materialize_fun_007c5a20_trig_record({
            {1.0, 2.0, 4.0},
            -3.0,
            0,
        });
        require(negative_selector.current_index == 0,
                "FUN_007c5a20 negative selector clamp drift");

        const auto zero_source = materialize_fun_007c5a20_trig_record({
            {0.0, 0.0, 0.0},
            3.0,
            5,
        });
        require(zero_source.count == 5,
                "FUN_007c5a20 zero source must preserve previous count");
        require(zero_source.current_index == 3,
                "FUN_007c5a20 zero-source selector clamp drift");
        require(zero_source.base_value == 0.0 && zero_source.slope_value == 0.0,
                "FUN_007c5a20 zero source copy drift");

        const double writer_output = execute_fun_00769640_trig_source_writer({
            materialized.base_value,
            materialized.slope_value,
            materialized.current_index,
        });
        require(nearly_equal(
                    writer_output,
                    50.0 * kFun007c5a20SelectedTrigScale),
                "FUN_007c5a20 materializer to FUN_00769640 writer handoff drift");

        bool rejected_non_finite = false;
        try {
            (void)materialize_fun_007c5a20_trig_record({
                {std::numeric_limits<double>::infinity(), 0.0, 1.0},
                0.0,
                0,
            });
        } catch (const std::invalid_argument&) {
            rejected_non_finite = true;
        }
        require(rejected_non_finite,
                "FUN_007c5a20 non-finite selected source failed open");

        std::cout
            << "{\"format\":\"" << kFun007c5a20TrigRecordMaterializerFormat
            << "\",\"ready\":true,"
            << "\"selected_record_count\":2,"
            << "\"range_copy_and_scale_internalized\":true,"
            << "\"count_and_selector_clamp_internalized\":true,"
            << "\"zero_source_previous_count_preserved\":true,"
            << "\"load_object_source_acquisition_internalized\":false,"
            << "\"external_provider_count\":7}\n";
        return 0;
    } catch (const std::exception& exc) {
        std::cerr << exc.what() << '\n';
        return 1;
    }
}
