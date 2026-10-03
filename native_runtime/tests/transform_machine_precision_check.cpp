#include "shift_constraint_sample_refresh.hpp"

#include <array>
#include <cmath>
#include <iostream>
#include <limits>
#include <stdexcept>

namespace {

using namespace shift::runtime::physics;

void require_exact(double actual, double expected, const char* label) {
    if (!std::isfinite(actual) || actual != expected) {
        throw std::runtime_error(label);
    }
}

}  // namespace

int main() {
    using namespace shift::runtime::physics;
    try {
        const ConstraintRefreshFrame3f identity = {
            1.0f, 0.0f, 0.0f,
            0.0f, 1.0f, 0.0f,
            0.0f, 0.0f, 1.0f,
        };

        // This value is distinct in binary64 but rounds to exactly 1.0 in
        // binary32.  Retail uses QWORD vector operands, so both matrix helpers
        // must preserve it under an identity transform.
        const double perturbation = 1.0 + 0x1p-30;
        const auto forward = transform_fun_007aefb0_refresh(
            identity,
            {perturbation, -2.0, 3.25});
        require_exact(forward[0], perturbation, "FUN_007aefb0 lost binary64 input precision");
        require_exact(forward[1], -2.0, "FUN_007aefb0 identity y mismatch");
        require_exact(forward[2], 3.25, "FUN_007aefb0 identity z mismatch");

        const auto transpose = transform_fun_007af0a0_refresh(
            identity,
            {-perturbation, 2.0, -3.0});
        require_exact(transpose[0], -perturbation, "FUN_007af0a0 lost binary64 input precision");
        require_exact(transpose[1], 2.0, "FUN_007af0a0 identity y mismatch");
        require_exact(transpose[2], -3.0, "FUN_007af0a0 identity z mismatch");

        const auto column = transform_fun_007af010_refresh(identity, perturbation);
        require_exact(column[0], perturbation, "FUN_007af010 lost QWORD scalar precision");
        require_exact(column[1], 0.0, "FUN_007af010 column y mismatch");
        require_exact(column[2], 0.0, "FUN_007af010 column z mismatch");

        // Retail aefb0 component 0 executes m01*y, then m00*x, then m02*z.
        // The reversed source-expression order would lose the trailing +1 at
        // this magnitude under x87 extended precision.
        ConstraintRefreshFrame3f forward_order = {
            1.0f, 1.0f, 1.0f,
            0.0f, 0.0f, 0.0f,
            0.0f, 0.0f, 0.0f,
        };
        const auto forward_cancel = transform_fun_007aefb0_refresh(
            forward_order,
            {1.0e20, -1.0e20, 1.0});
        require_exact(forward_cancel[0], 1.0, "FUN_007aefb0 machine add order mismatch");

        // Retail af0a0 component 0 executes m10*y, then m00*x, then m20*z.
        ConstraintRefreshFrame3f transpose_order = {
            1.0f, 0.0f, 0.0f,
            1.0f, 0.0f, 0.0f,
            1.0f, 0.0f, 0.0f,
        };
        const auto transpose_cancel = transform_fun_007af0a0_refresh(
            transpose_order,
            {1.0e20, -1.0e20, 1.0});
        require_exact(transpose_cancel[0], 1.0, "FUN_007af0a0 machine add order mismatch");

        bool nonfinite_scalar_rejected = false;
        try {
            (void)transform_fun_007af010_refresh(
                identity,
                std::numeric_limits<double>::infinity());
        } catch (const std::invalid_argument&) {
            nonfinite_scalar_rejected = true;
        }
        if (!nonfinite_scalar_rejected) {
            throw std::runtime_error("FUN_007af010 accepted non-finite scalar");
        }

        std::cout
            << "{\"format\":\"SHIFT.NativeTransformMachinePrecision/1\","
            << "\"ready\":true,"
            << "\"qword_vector_operands_preserved\":true,"
            << "\"qword_scalar_operand_preserved\":true,"
            << "\"retail_add_order_preserved\":true,"
            << "\"fun_007aefb0_sha256\":\"76c52235cce08d3ec131d43e1b62cda623ac8528944e44f902846a0a71b14f29\","
            << "\"fun_007af010_sha256\":\"f3256201dee28b97260576ee14c522e236a44d1808516ed8e42efd2e2e2e8324\","
            << "\"fun_007af0a0_sha256\":\"8cd039935dbbe493db7742f7af1859d9abcc7d9c40f212c3f2fa331e992c52cc\","
            << "\"ambient_x87_control_word_proven\":false}\n";
        return 0;
    } catch (const std::exception& exc) {
        std::cerr << exc.what() << '\n';
        return 1;
    }
}
