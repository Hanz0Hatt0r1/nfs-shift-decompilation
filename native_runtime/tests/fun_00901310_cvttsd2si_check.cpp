#include "shift_fun_007bf790_caster_record_materialization.hpp"
#include "shift_fun_00901310_cvttsd2si.hpp"

#include <cmath>
#include <cstdint>
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

}  // namespace

int main() {
    try {
        require(kFun00901310Entry == 0x00901310u,
                "FUN_00901310 entry drift");
        require(kFun00901310X87SpillSite == 0x00901322u,
                "FUN_00901310 x87 spill site drift");
        require(kFun00901310Cvttsd2siSite == 0x00901325u,
                "FUN_00901310 CVTTSD2SI site drift");

        require(execute_fun_00901310_cvttsd2si(3.9) == 3,
                "FUN_00901310 positive truncation drift");
        require(execute_fun_00901310_cvttsd2si(-3.9) == -3,
                "FUN_00901310 negative truncation drift");
        require(execute_fun_00901310_cvttsd2si(0.0) == 0 &&
                    execute_fun_00901310_cvttsd2si(-0.0) == 0,
                "FUN_00901310 signed-zero conversion drift");
        require(execute_fun_00901310_cvttsd2si(2147483647.9) ==
                    std::numeric_limits<std::int32_t>::max(),
                "FUN_00901310 positive in-range edge drift");
        require(execute_fun_00901310_cvttsd2si(-2147483648.9) ==
                    std::numeric_limits<std::int32_t>::min(),
                "FUN_00901310 negative truncated edge drift");

        require(execute_fun_00901310_cvttsd2si(2147483648.0) ==
                    kFun00901310IntegerIndefinite,
                "FUN_00901310 positive overflow indefinite drift");
        require(execute_fun_00901310_cvttsd2si(-2147483649.0) ==
                    kFun00901310IntegerIndefinite,
                "FUN_00901310 negative overflow indefinite drift");
        require(execute_fun_00901310_cvttsd2si(
                    std::numeric_limits<double>::infinity()) ==
                    kFun00901310IntegerIndefinite &&
                    execute_fun_00901310_cvttsd2si(
                    -std::numeric_limits<double>::infinity()) ==
                    kFun00901310IntegerIndefinite &&
                    execute_fun_00901310_cvttsd2si(
                    std::numeric_limits<double>::quiet_NaN()) ==
                    kFun00901310IntegerIndefinite,
                "FUN_00901310 non-finite integer-indefinite drift");

        const Fun007bf790CasterPairInput caster_input{
            {{0.0,
              0.125 / kFun007bf790CasterDegreesToRadians,
              5.9},
             2.9,
             91},
            {{1.0, 2.0, 4.8}, 9.7, 73},
        };
        const auto records = materialize_fun_007bf790_caster_records(caster_input);
        require(records.left.count == 5 && records.left.coefficient == 2,
                "native FUN_00901310 left caster handoff drift");
        require(records.right.count == 4 && records.right.coefficient == 3,
                "native FUN_00901310 right caster clamp drift");
        require(records.left.slope_value == 0.125,
                "native FUN_00901310 caster scaling handoff drift");

        std::cout
            << "{\"format\":\"" << kFun00901310Cvttsd2siFormat << "\","
            << "\"ready\":true,"
            << "\"eax_value_semantics_internalized\":true,"
            << "\"truncate_toward_zero\":true,"
            << "\"integer_indefinite_internalized\":true,"
            << "\"mxcsr_status_flags_internalized\":false,"
            << "\"caster_callback_required\":false}\n";
        return 0;
    } catch (const std::exception& exc) {
        std::cerr << exc.what() << '\n';
        return 1;
    }
}
