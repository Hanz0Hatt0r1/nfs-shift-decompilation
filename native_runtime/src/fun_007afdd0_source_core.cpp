#include "shift_fun_007afdd0_source_core.hpp"

#include <cmath>
#include <stdexcept>

namespace shift::runtime::physics {
namespace {

void require_finite(float value, const char* label) {
    if (!std::isfinite(value)) {
        throw std::invalid_argument(label);
    }
}

void require_finite(double value, const char* label) {
    if (!std::isfinite(value)) {
        throw std::invalid_argument(label);
    }
}

void require_finite(const ConstraintRefreshFrame3f& values, const char* label) {
    for (float value : values) {
        require_finite(value, label);
    }
}

void require_finite(const ConstraintRefreshVector3d& values, const char* label) {
    for (double value : values) {
        require_finite(value, label);
    }
}

ConstraintRefreshFrame3f build_source_rotation(
    float x,
    float y,
    float z,
    float sine,
    float cosine) {

    // Mirrors the recovered fVar assignment graph from SHIFT.exe.c.  This is a
    // source-shape port, not yet a claim about every retail x87 excess-precision
    // boundary inside these expressions.  Phase 680 remains the machine gate.
    float fVar8 = 1.0f - cosine;
    float fVar9 = fVar8 * y * x;
    float fVar10 = z * x * fVar8;
    fVar8 = fVar8 * y * z;

    const float fVar7 = (1.0f - x * x) * cosine + x * x;
    const float fVar11 = fVar9 - z * sine;
    const float fVar12 = y * sine + fVar10;
    fVar9 = fVar9 + z * sine;
    const float fVar6 = (1.0f - y * y) * cosine + y * y;
    const float fVar13 = fVar8 - sine * x;
    fVar10 = fVar10 - y * sine;
    fVar8 = sine * x + fVar8;
    const float fVar4 = z * z + (1.0f - z * z) * cosine;

    return {
        fVar7, fVar11, fVar12,
        fVar9, fVar6, fVar13,
        fVar10, fVar8, fVar4,
    };
}

ConstraintRefreshFrame3f apply_source_write_order(
    const ConstraintRefreshFrame3f& basis,
    const ConstraintRefreshFrame3f& rotation) {

    const float r00 = rotation[0];
    const float r01 = rotation[1];
    const float r02 = rotation[2];
    const float r10 = rotation[3];
    const float r11 = rotation[4];
    const float r12 = rotation[5];
    const float r20 = rotation[6];
    const float r21 = rotation[7];
    const float r22 = rotation[8];

    ConstraintRefreshFrame3f result = basis;
    for (const auto stripe : std::array<std::array<std::size_t, 3>, 3>{
             std::array<std::size_t, 3>{0u, 3u, 6u},
             std::array<std::size_t, 3>{1u, 4u, 7u},
             std::array<std::size_t, 3>{2u, 5u, 8u},
         }) {
        const std::size_t i0 = stripe[0];
        const std::size_t i1 = stripe[1];
        const std::size_t i2 = stripe[2];
        const float old0 = result[i0];
        const float old1 = result[i1];
        const float old2 = result[i2];

        result[i0] = r02 * old2 + old1 * r01 + old0 * r00;
        result[i1] = r12 * old2 + r10 * old0 + r11 * old1;
        result[i2] = r22 * old2 + r21 * old1 + r20 * old0;
    }
    return result;
}

}  // namespace

Fun007afdd0SourceCoreResult execute_fun_007afdd0_source_core(
    const ConstraintRefreshFrame3f& basis,
    const ConstraintRefreshVector3d& rotation_increment,
    const Fun007afdd0ScalarBoundary& scalars) {

    require_finite(basis, "FUN_007afdd0 basis contains non-finite value");
    require_finite(
        rotation_increment,
        "FUN_007afdd0 rotation increment contains non-finite value");
    require_finite(
        scalars.squared_magnitude_test,
        "FUN_007afdd0 magnitude test is non-finite");

    Fun007afdd0SourceCoreResult result{};
    result.basis = basis;
    result.rotation_coefficients = {
        1.0f, 0.0f, 0.0f,
        0.0f, 1.0f, 0.0f,
        0.0f, 0.0f, 1.0f,
    };

    if (scalars.squared_magnitude_test == 0.0f) {
        return result;
    }

    require_finite(
        scalars.sqrt_magnitude,
        "FUN_007afdd0 sqrt magnitude is non-finite");
    require_finite(scalars.sine, "FUN_007afdd0 sine boundary is non-finite");
    require_finite(scalars.cosine, "FUN_007afdd0 cosine boundary is non-finite");
    if (scalars.sqrt_magnitude == 0.0f) {
        throw std::invalid_argument(
            "FUN_007afdd0 non-zero path requires non-zero sqrt magnitude");
    }

    const float inverse_magnitude = 1.0f / scalars.sqrt_magnitude;
    const float x = inverse_magnitude * static_cast<float>(rotation_increment[0]);
    const float y = static_cast<float>(rotation_increment[1]) * inverse_magnitude;
    const float z = inverse_magnitude * static_cast<float>(rotation_increment[2]);
    result.normalized_axis = {x, y, z};
    result.rotation_coefficients =
        build_source_rotation(x, y, z, scalars.sine, scalars.cosine);
    require_finite(
        result.rotation_coefficients,
        "FUN_007afdd0 rotation coefficients contain non-finite value");
    result.basis = apply_source_write_order(basis, result.rotation_coefficients);
    require_finite(result.basis, "FUN_007afdd0 updated basis contains non-finite value");
    result.applied = true;
    return result;
}

}  // namespace shift::runtime::physics
