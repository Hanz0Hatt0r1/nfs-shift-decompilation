#include "shift_fun_00766510_optional_response_branch.hpp"

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
        require(kFun00766510OptionalGateOffset == 0x3bc8u,
                "optional-response gate offset drift");
        require(kFun00766510OptionalMutableOffset == 0x3bd0u,
                "optional-response mutable offset drift");
        require(kFun00766510OptionalCoefficientOffsets.front() == 0x3bd8u &&
                    kFun00766510OptionalCoefficientOffsets.back() == 0x3c30u,
                "optional-response coefficient block drift");
        require(kFun00766510OptionalDerivedShapeOffsets[0] == 0x3c18u &&
                    kFun00766510OptionalDerivedShapeOffsets[3] == 0x3c38u,
                "optional-response derived-shape offsets drift");
        require(kFun00766510OptionalCurveOffset == 0x3c40u,
                "optional-response curve offset drift");
        require(kFun00766510OptionalApplicationOffsets[0] == 0x3c60u &&
                    kFun00766510OptionalApplicationOffsets[1] == 0x3c68u &&
                    kFun00766510OptionalApplicationOffsets[2] == 0x3c70u,
                "optional-response application offsets drift");

        Fun00766510OptionalResponseSetup setup{};
        setup.gate_enabled = true;
        setup.mutable_initial = 2.5;
        setup.coefficients = {1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0};
        setup.derived_shape = {10.0, 11.0, 12.0, 13.0};
        setup.application_vector = {14.0, 15.0, 16.0};

        auto persistent =
            initialize_fun_00766510_optional_response_persistent_state(setup);
        require(persistent.mutable_value == 2.5,
                "optional-response +0x3bd0 setup witness drift");
        require(persistent.last_write ==
                    Fun00766510OptionalMutableWriteSource::SetupEvaluation,
                "optional-response setup writer witness drift");

        write_fun_00766510_optional_response_mutable_value(
            persistent,
            4.0,
            Fun00766510OptionalMutableWriteSource::Fun00757fa0IncrementResult);
        require(persistent.mutable_value == 4.0,
                "optional-response increment-result handoff drift");

        write_fun_00766510_optional_response_mutable_value(
            persistent,
            3.25,
            Fun00766510OptionalMutableWriteSource::Fun00758170ClampResult);
        require(persistent.mutable_value == 3.25,
                "optional-response clamp-result handoff drift");

        write_fun_00766510_optional_response_mutable_value(
            persistent,
            1.5,
            Fun00766510OptionalMutableWriteSource::Fun00769d60ResetClampResult);
        require(persistent.mutable_value == 1.5,
                "optional-response reset-clamp handoff drift");

        write_fun_00766510_optional_response_mutable_value(
            persistent,
            8.75,
            Fun00766510OptionalMutableWriteSource::Fun0076ed60StateLoad);
        require(persistent.mutable_value == 8.75 &&
                    persistent.last_write ==
                        Fun00766510OptionalMutableWriteSource::Fun0076ed60StateLoad,
                "optional-response state-load handoff drift");

        require(fun_00766510_optional_response_gate_passes(setup, -0.25),
                "optional-response negative gate witness drift");
        require(!fun_00766510_optional_response_gate_passes(setup, 0.0),
                "optional-response zero local_50 must not pass gate");
        setup.gate_enabled = false;
        require(!fun_00766510_optional_response_gate_passes(setup, -0.25),
                "optional-response disabled gate must not pass");

        std::cout
            << "{\"format\":\"" << kFun00766510OptionalResponseBranchFormat << "\","
            << "\"ready\":true,"
            << "\"mutable_offset\":\"0x3bd0\","
            << "\"writer_surface_modeled\":true,"
            << "\"writer_arithmetic_internalized\":false,"
            << "\"contact_response_provider_removed\":false}\n";
        return 0;
    } catch (const std::exception& exc) {
        std::cerr << exc.what() << '\n';
        return 1;
    }
}
