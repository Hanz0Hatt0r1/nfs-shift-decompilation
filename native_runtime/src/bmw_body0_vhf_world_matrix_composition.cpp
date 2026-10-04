#include "shift_bmw_body0_vhf_world_matrix_composition.hpp"

#include <array>
#include <cmath>
#include <limits>
#include <stdexcept>
#include <string>

namespace shift::runtime::physics {
namespace {

using MatrixD = std::array<double, 16>;
using shift::runtime::render::VehicleWorldMatrix;

constexpr double kAffineTolerance = 1.0e-6;
constexpr double kSingularTolerance = 1.0e-12;
constexpr std::uint32_t kRetailBmwChassisBodyIndex = 0u;

MatrixD to_double(const VehicleWorldMatrix& matrix) {
    MatrixD out{};
    for (std::size_t index = 0u; index < out.size(); ++index) {
        const double value = static_cast<double>(matrix[index]);
        if (!std::isfinite(value)) {
            throw std::invalid_argument("world matrix contains non-finite value");
        }
        out[index] = value;
    }
    return out;
}

double determinant3(const MatrixD& matrix) {
    const double a = matrix[0], b = matrix[1], c = matrix[2];
    const double d = matrix[4], e = matrix[5], f = matrix[6];
    const double g = matrix[8], h = matrix[9], i = matrix[10];
    return a * (e * i - f * h) -
           b * (d * i - f * g) +
           c * (d * h - e * g);
}

void validate_row_affine(const MatrixD& matrix, const char* label) {
    for (double value : matrix) {
        if (!std::isfinite(value)) {
            throw std::invalid_argument(std::string(label) + " contains non-finite value");
        }
    }
    if (std::fabs(matrix[3]) > kAffineTolerance ||
        std::fabs(matrix[7]) > kAffineTolerance ||
        std::fabs(matrix[11]) > kAffineTolerance ||
        std::fabs(matrix[15] - 1.0) > kAffineTolerance) {
        throw std::invalid_argument(std::string(label) + " is not D3D row-vector affine");
    }
    const double determinant = determinant3(matrix);
    if (!std::isfinite(determinant) ||
        std::fabs(determinant) <= kSingularTolerance) {
        throw std::invalid_argument(std::string(label) + " linear block is singular");
    }
}

MatrixD multiply4(const MatrixD& lhs, const MatrixD& rhs) {
    MatrixD out{};
    for (std::size_t row = 0u; row < 4u; ++row) {
        for (std::size_t column = 0u; column < 4u; ++column) {
            double sum = 0.0;
            for (std::size_t k = 0u; k < 4u; ++k) {
                sum += lhs[row * 4u + k] * rhs[k * 4u + column];
            }
            out[row * 4u + column] = sum;
        }
    }
    return out;
}

MatrixD inverse_affine_row(const MatrixD& matrix) {
    validate_row_affine(matrix, "BODY0 bind matrix");
    const double a = matrix[0], b = matrix[1], c = matrix[2];
    const double d = matrix[4], e = matrix[5], f = matrix[6];
    const double g = matrix[8], h = matrix[9], i = matrix[10];
    const double det = determinant3(matrix);
    const double inv_det = 1.0 / det;

    MatrixD out{
        (e * i - f * h) * inv_det,
        (c * h - b * i) * inv_det,
        (b * f - c * e) * inv_det,
        0.0,
        (f * g - d * i) * inv_det,
        (a * i - c * g) * inv_det,
        (c * d - a * f) * inv_det,
        0.0,
        (d * h - e * g) * inv_det,
        (b * g - a * h) * inv_det,
        (a * e - b * d) * inv_det,
        0.0,
        0.0,
        0.0,
        0.0,
        1.0,
    };

    const double tx = matrix[12];
    const double ty = matrix[13];
    const double tz = matrix[14];
    out[12] = -(tx * out[0] + ty * out[4] + tz * out[8]);
    out[13] = -(tx * out[1] + ty * out[5] + tz * out[9]);
    out[14] = -(tx * out[2] + ty * out[6] + tz * out[10]);
    validate_row_affine(out, "inverse BODY0 bind matrix");
    return out;
}

MatrixD body0_runtime_row_matrix(const SelectedVehicleBodyPose& pose) {
    if (pose.body_index != kRetailBmwChassisBodyIndex) {
        throw std::invalid_argument("Phase 704 requires selected retail BMW chassis BODY 0");
    }
    for (double value : pose.origin) {
        if (!std::isfinite(value)) {
            throw std::invalid_argument("BODY0 origin contains non-finite value");
        }
    }
    for (float value : pose.basis) {
        if (!std::isfinite(value)) {
            throw std::invalid_argument("BODY0 basis contains non-finite value");
        }
    }

    const auto& b = pose.basis;
    const auto& o = pose.origin;
    MatrixD out{
        static_cast<double>(b[0]), static_cast<double>(b[3]), static_cast<double>(b[6]), 0.0,
        static_cast<double>(b[1]), static_cast<double>(b[4]), static_cast<double>(b[7]), 0.0,
        static_cast<double>(b[2]), static_cast<double>(b[5]), static_cast<double>(b[8]), 0.0,
        o[0], o[1], o[2], 1.0,
    };
    validate_row_affine(out, "BODY0 runtime pose matrix");
    return out;
}

VehicleWorldMatrix narrow_to_phase646(const MatrixD& matrix) {
    validate_row_affine(matrix, "composed BMW vehicle world matrix");
    VehicleWorldMatrix out{};
    for (std::size_t index = 0u; index < out.size(); ++index) {
        if (std::fabs(matrix[index]) >
            static_cast<double>(std::numeric_limits<float>::max())) {
            throw std::overflow_error("composed BMW world matrix exceeds Phase 646 float32 domain");
        }
        out[index] = static_cast<float>(matrix[index]);
        if (!std::isfinite(out[index])) {
            throw std::overflow_error("composed BMW world matrix narrowed to non-finite float32");
        }
    }
    validate_row_affine(to_double(out), "Phase 646 BMW vehicle world matrix");
    return out;
}

}  // namespace

BmwBody0VhfWorldMatrixCompositionResult
compose_bmw_body0_pose_to_vehicle_world_matrix(
    const SelectedVehicleBodyPose& body0_pose,
    const ProvenBmwVhfBindFrame& vhf_bind,
    const ProvenBmwBody0BindFrame& body0_bind) {

    if (!vhf_bind.proven) {
        throw std::invalid_argument("Phase 704 requires proven Phase 645 BMW VHF bind frame");
    }
    if (!body0_bind.ready || !body0_bind.evidence_proven_static) {
        throw std::invalid_argument("Phase 704 requires proven-static BMW BODY0 bind-frame proof");
    }
    if (body0_bind.body_index != kRetailBmwChassisBodyIndex) {
        throw std::invalid_argument("BODY0 bind-frame proof does not identify retail BMW chassis BODY 0");
    }
    if (body0_bind.identity_matrix_assumed) {
        throw std::invalid_argument("BODY0 bind-frame proof was produced by an identity-matrix assumption");
    }

    const MatrixD vhf = to_double(vhf_bind.body_meb_to_vhf_vehicle_root);
    validate_row_affine(vhf, "Phase 645 VHF bind matrix");
    const MatrixD body_bind = to_double(body0_bind.body0_local_to_vhf_vehicle_root);
    const MatrixD body_bind_inverse = inverse_affine_row(body_bind);
    const MatrixD body_runtime = body0_runtime_row_matrix(body0_pose);

    const MatrixD composed = multiply4(
        multiply4(vhf, body_bind_inverse),
        body_runtime);

    BmwBody0VhfWorldMatrixCompositionResult result{};
    result.body0_runtime_row = narrow_to_phase646(body_runtime);
    result.vehicle_world_matrix = narrow_to_phase646(composed);
    return result;
}

}  // namespace shift::runtime::physics
