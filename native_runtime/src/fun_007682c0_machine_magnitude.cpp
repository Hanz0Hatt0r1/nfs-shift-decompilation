#include "shift_fun_007682c0_machine_magnitude.hpp"

#include <cmath>
#include <cstdint>
#include <stdexcept>

namespace shift::runtime::physics {
namespace {

constexpr std::uint16_t kRetailX87ControlWord = 0x027fu;

void require_finite(double value, const char* label) {
    if (!std::isfinite(value)) {
        throw std::invalid_argument(label);
    }
}

#if defined(__i386__) || defined(__x86_64__)

struct ScopedRetailX87ControlWord {
    std::uint16_t saved = 0u;

    ScopedRetailX87ControlWord() {
        __asm__ __volatile__("fnstcw %0" : "=m"(saved));
        __asm__ __volatile__("fldcw %0" :: "m"(kRetailX87ControlWord));
    }

    ~ScopedRetailX87ControlWord() {
        __asm__ __volatile__("fldcw %0" :: "m"(saved));
    }
};

float speed3d_x87(double x, double y, double z) {
    ScopedRetailX87ControlWord control{};
    float result = 0.0f;

    // Equivalent PC retail arithmetic domain for 0x007682e2..0x00768305:
    // x^2 + y^2 is accumulated first, then z^2, FSQRT, f32 store.
    __asm__ __volatile__(
        "fldl %[x]\n\t"
        "fmul %%st(0), %%st(0)\n\t"
        "fldl %[y]\n\t"
        "fmul %%st(0), %%st(0)\n\t"
        "faddp %%st, %%st(1)\n\t"
        "fldl %[z]\n\t"
        "fmul %%st(0), %%st(0)\n\t"
        "faddp %%st, %%st(1)\n\t"
        "fsqrt\n\t"
        "fstps %[out]\n\t"
        : [out] "=m"(result)
        : [x] "m"(x), [y] "m"(y), [z] "m"(z));
    return result;
}

float planar_speed_x87(double x, double z) {
    ScopedRetailX87ControlWord control{};
    float x32 = 0.0f;
    float z32 = 0.0f;
    float squared32 = 0.0f;
    float result = 0.0f;

    // FUN_0075ada0 first narrows both BODY f64 lanes to f32.
    __asm__ __volatile__(
        "fldl %[x]\n\t"
        "fstps %[x32]\n\t"
        "fldl %[z]\n\t"
        "fstps %[z32]\n\t"
        : [x32] "=m"(x32), [z32] "=m"(z32)
        : [x] "m"(x), [z] "m"(z));

    // It then stores the squared magnitude to f32 before invoking __CIsqrt,
    // reloads that f32 value, executes FSQRT and stores the result to f32.
    __asm__ __volatile__(
        "flds %[x32]\n\t"
        "fmul %%st(0), %%st(0)\n\t"
        "flds %[z32]\n\t"
        "fmul %%st(0), %%st(0)\n\t"
        "faddp %%st, %%st(1)\n\t"
        "fstps %[sq]\n\t"
        "flds %[sq]\n\t"
        "fsqrt\n\t"
        "fstps %[out]\n\t"
        : [sq] "=m"(squared32), [out] "=m"(result)
        : [x32] "m"(x32), [z32] "m"(z32));
    return result;
}

float speed_factor_x87(float speed) {
    ScopedRetailX87ControlWord control{};
    constexpr double kFive = 5.0;
    constexpr double kFifteen = 15.0;
    float factor = 0.0f;
    __asm__ __volatile__(
        "flds %[speed]\n\t"
        "fsubl %[five]\n\t"
        "fdivl %[fifteen]\n\t"
        "fstps %[out]\n\t"
        : [out] "=m"(factor)
        : [speed] "m"(speed), [five] "m"(kFive), [fifteen] "m"(kFifteen));
    return factor;
}

#else

float speed3d_x87(double, double, double) {
    throw std::runtime_error(
        "FUN_007682c0 PC x87 magnitude requires an x86/x86_64 host");
}

float planar_speed_x87(double, double) {
    throw std::runtime_error(
        "FUN_0075ada0 PC x87 magnitude requires an x86/x86_64 host");
}

float speed_factor_x87(float) {
    throw std::runtime_error(
        "FUN_007682c0 PC x87 speed factor requires an x86/x86_64 host");
}

#endif

}  // namespace

float fun_007682c0_pc_x87_speed3d_f32(
    double motion_x,
    double motion_y,
    double motion_z) {
    require_finite(motion_x, "FUN_007682c0 motion_x must be finite");
    require_finite(motion_y, "FUN_007682c0 motion_y must be finite");
    require_finite(motion_z, "FUN_007682c0 motion_z must be finite");

    const float result = speed3d_x87(motion_x, motion_y, motion_z);
    if (!std::isfinite(static_cast<double>(result))) {
        throw std::overflow_error("FUN_007682c0 x87 speed magnitude overflowed f32");
    }
    return result;
}

float fun_0075ada0_pc_x87_planar_speed_f32(
    double motion_x,
    double motion_z) {
    require_finite(motion_x, "FUN_0075ada0 motion_x must be finite");
    require_finite(motion_z, "FUN_0075ada0 motion_z must be finite");

    const float result = planar_speed_x87(motion_x, motion_z);
    if (!std::isfinite(static_cast<double>(result))) {
        throw std::overflow_error("FUN_0075ada0 x87 planar magnitude overflowed f32");
    }
    return result;
}

Fun007682c0MachineMagnitudeResult
fun_007682c0_pc_machine_magnitude(
    double motion_x,
    double motion_y,
    double motion_z) {
    Fun007682c0MachineMagnitudeResult result{};
    result.speed_3d = fun_007682c0_pc_x87_speed3d_f32(
        motion_x, motion_y, motion_z);
    if (result.speed_3d < 5.0f) {
        return result;
    }

    result.speed_gate_open = true;
    float factor = speed_factor_x87(result.speed_3d);
    if (!std::isfinite(static_cast<double>(factor))) {
        throw std::overflow_error("FUN_007682c0 x87 speed factor is non-finite");
    }
    if (factor < 0.0f) {
        factor = 0.0f;
    } else if (factor >= 1.0f) {
        factor = 1.0f;
    }
    result.speed_factor = factor;
    return result;
}

}  // namespace shift::runtime::physics
