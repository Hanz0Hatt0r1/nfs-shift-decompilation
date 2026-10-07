#include "shift_fun_00765c40_external_pass_result.hpp"

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
        const Fun00765c40ExternalPassResult valid{
            Fun00765c40LoadTerms{10.0, 20.0, 30.0, 40.0}};
        validate_fun_00765c40_external_pass_result(valid);
        require(valid.load_terms[0] == 10.0 && valid.load_terms[3] == 40.0,
                "FUN_00765c40 external pass result changed typed load terms");

        bool nonfinite_rejected = false;
        try {
            Fun00765c40ExternalPassResult invalid = valid;
            invalid.load_terms[2] = std::numeric_limits<double>::quiet_NaN();
            validate_fun_00765c40_external_pass_result(invalid);
        } catch (const std::invalid_argument&) {
            nonfinite_rejected = true;
        }
        require(nonfinite_rejected,
                "FUN_00765c40 external pass result accepted non-finite load term");

        std::cout
            << "{\"format\":\"" << kFun00765c40ExternalPassResultFormat << "\","
            << "\"ready\":true,"
            << "\"load_term_count\":4,"
            << "\"session_contact_factor_alias_removed\":true,"
            << "\"complete_fun_00765c40_internalized\":false,"
            << "\"world_position_producer_internalized\":false,"
            << "\"collision_provider_internalized\":false}\n";
        return 0;
    } catch (const std::exception& exc) {
        std::cerr << exc.what() << '\n';
        return 1;
    }
}
