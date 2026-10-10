#include "shift_fun_007bf790_caster_record_materialization.hpp"
#include "shift_fun_00769640_trig_source_writer.hpp"

#include <cmath>
#include <cstdint>
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

}  // namespace

int main() {
    try {
        require(kFun007bf790LeftCasterRangeOffset == 0x01e8u &&
                    kFun007bf790LeftCasterSettingOffset == 0x03d8u &&
                    kFun007bf790RightCasterRangeOffset == 0x0200u &&
                    kFun007bf790RightCasterSettingOffset == 0x03e0u,
                "FUN_007bf790 caster config source offsets drift");
        require(kFun007bf790LeftCasterRecordRelativeOffset == 0x1188u &&
                    kFun007bf790RightCasterRecordRelativeOffset == 0x11d8u,
                "FUN_007bf790 caster record offsets drift");
        require(kFun00901310IntegerConversionBoundary == 0x00901310u,
                "FUN_00901310 integer conversion boundary drift");

        std::vector<double> conversion_inputs;
        const auto integer_conversion = [&conversion_inputs](double value) {
            conversion_inputs.push_back(value);
            if (!std::isfinite(value) || std::floor(value) != value) {
                throw std::invalid_argument(
                    "test conversion witness accepts integer-valued doubles only");
            }
            return static_cast<std::int32_t>(value);
        };

        const double left_slope_degrees =
            0.125 / kFun007bf790CasterDegreesToRadians;
        const Fun007bf790CasterPairInput input{
            {{0.0, left_slope_degrees, 5.0}, 2.0, 91},
            {{1.0, 2.0, 4.0}, 9.0, 73},
        };
        const auto records = materialize_fun_007bf790_caster_records(
            input, integer_conversion);

        require(conversion_inputs == std::vector<double>{5.0, 2.0, 4.0, 9.0},
                "FUN_007bf790 conversion call order drift");
        require(records.left.count == 5 && records.left.coefficient == 2,
                "FUN_007bf790 left caster count/coefficient drift");
        require(records.left.base_value == 0.0 &&
                    records.left.slope_value == 0.125,
                "FUN_007bf790 left caster degree scaling drift");
        require(records.right.count == 4 && records.right.coefficient == 3,
                "FUN_007bf790 right caster clamp drift");
        require(records.right.base_value ==
                    1.0 * kFun007bf790CasterDegreesToRadians &&
                    records.right.slope_value ==
                    2.0 * kFun007bf790CasterDegreesToRadians,
                "FUN_007bf790 right caster degree scaling drift");

        const double trig_source = execute_fun_00769640_trig_source_writer(
            fun_007bf790_caster_record_to_trig_writer_input(records.left));
        require(trig_source == 0.25,
                "FUN_007bf790 caster record to FUN_00769640 handoff drift");

        conversion_inputs.clear();
        const auto zero_range = materialize_fun_007c5a20_caster_record(
            {{0.0, 0.0, 0.0}, 8.0, 3}, integer_conversion);
        require(conversion_inputs == std::vector<double>{8.0},
                "FUN_007c5a20 zero-range conversion behavior drift");
        require(zero_range.count == 3 && zero_range.coefficient == 2,
                "FUN_007c5a20 zero-range prior-count preservation drift");
        require(zero_range.base_value == 0.0 && zero_range.slope_value == 0.0,
                "FUN_007c5a20 zero-range scaling branch drift");

        conversion_inputs.clear();
        const auto negative_setting = materialize_fun_007c5a20_caster_record(
            {{1.0, 1.0, 3.0}, -2.0, 0}, integer_conversion);
        require(negative_setting.coefficient == 0,
                "FUN_007c5a20 negative setting clamp drift");

        bool rejected_non_finite = false;
        try {
            (void)materialize_fun_007c5a20_caster_record(
                {{1.0, std::numeric_limits<double>::infinity(), 3.0}, 1.0, 0},
                integer_conversion);
        } catch (const std::invalid_argument&) {
            rejected_non_finite = true;
        }
        require(rejected_non_finite,
                "FUN_007c5a20 non-finite caster input failed open");

        std::cout
            << "{\"format\":\""
            << kFun007bf790CasterRecordMaterializationFormat << "\","
            << "\"ready\":true,"
            << "\"left_record_relative_offset\":4488,"
            << "\"right_record_relative_offset\":4568,"
            << "\"integer_conversion_boundary_internalized\":false,"
            << "\"caster_record_materialization_internalized\":true,"
            << "\"caster_config_source_acquisition_internalized\":false}\n";
        return 0;
    } catch (const std::exception& exc) {
        std::cerr << exc.what() << '\n';
        return 1;
    }
}
