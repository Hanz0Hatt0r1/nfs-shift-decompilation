#include "shift_fun_00766510_response_config.hpp"

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
        require(kFun00766510ResponseDerivedScaleOffset == 0x3908u,
                "response-config derived scale offset drift");
        require(kFun00766510ResponseSetupScaleOffset == 0x3910u,
                "response-config setup scale offset drift");
        require(kFun00766510ResponseCurveOffset == 0x3918u,
                "response-config curve offset drift");
        require(kFun00766510ResponseTableOffset == 0x3950u &&
                    kFun00766510ResponseTableEntryCount == 6u &&
                    kFun00766510ResponseTableEntryStride == 0x18u,
                "response-config table geometry drift");
        require(kFun00766510ResponseSelectorOffset == 0x3c78u,
                "response-config selector offset drift");
        require(kFun00766510ResponseBaseCoefficientOffset == 0x3740u &&
                    kFun00766510ResponseLinearCoefficientOffset == 0x3748u &&
                    kFun00766510ResponseQuadraticCoefficientOffset == 0x3750u,
                "response-config coefficient offsets drift");

        Fun00766510ResponseConfigSetup setup{};
        setup.setup_scale = 0.75;
        setup.curve = pack_fun_00752f10_curve_parameters(0.0, 1.0, 1.0);
        for (std::size_t entry = 0; entry < setup.response_table.size(); ++entry) {
            setup.response_table[entry] = {
                static_cast<double>(entry * 3u + 0u),
                static_cast<double>(entry * 3u + 1u),
                static_cast<double>(entry * 3u + 2u),
            };
        }
        validate_fun_00766510_response_config_setup(setup);

        const Fun00766510ResponseConfigCoefficients coefficients{
            1.0,
            2.0,
            3.0,
        };
        const auto persistent =
            refresh_fun_00756ac0_response_config_state(coefficients, 2.0);
        require(persistent.selector == 2.0,
                "FUN_00756ac0 selector witness drift");
        require(persistent.derived_scale == 17.0,
                "FUN_00756ac0 +0x3908 witness drift");

        auto mutated = coefficients;
        mutated.base = 9.0;
        const auto refreshed =
            refresh_fun_00756ac0_response_config_state(mutated, 2.0);
        require(refreshed.derived_scale == 25.0,
                "response-config mutable base was incorrectly frozen");

        require(setup.response_table[5][0] == 15.0 &&
                    setup.response_table[5][1] == 16.0 &&
                    setup.response_table[5][2] == 17.0,
                "response-config setup table witness drift");

        std::cout
            << "{\"format\":\"" << kFun00766510ResponseConfigFormat << "\","
            << "\"ready\":true,"
            << "\"table_entry_count\":6,"
            << "\"derived_scale_offset\":\"0x3908\","
            << "\"runtime_response_internalized\":false,"
            << "\"contact_response_provider_removed\":false}\n";
        return 0;
    } catch (const std::exception& exc) {
        std::cerr << exc.what() << '\n';
        return 1;
    }
}
