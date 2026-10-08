# Single-process S6 Phase 751: consume the Process 1 optional-response ownership
# contract by internalizing the setup-owned block, exact runtime gate, and the
# +0x3bd0 persistent mutable writer surface without inventing mutator arithmetic.

add_executable(shift_runtime_fun_00766510_optional_response_branch_check
  ${CMAKE_CURRENT_SOURCE_DIR}/tests/fun_00766510_optional_response_branch_check.cpp)
target_include_directories(
  shift_runtime_fun_00766510_optional_response_branch_check PRIVATE
  ${CMAKE_CURRENT_SOURCE_DIR}/include
  ${CMAKE_CURRENT_SOURCE_DIR}/src
  ${CMAKE_CURRENT_SOURCE_DIR}/tests)
target_link_libraries(
  shift_runtime_fun_00766510_optional_response_branch_check PRIVATE
  shift_runtime_physics)
target_compile_options(
  shift_runtime_fun_00766510_optional_response_branch_check PRIVATE
  -Wall -Wextra -Wpedantic)

if(BUILD_TESTING)
  add_test(
    NAME shift_runtime_fun_00766510_optional_response_branch
    COMMAND shift_runtime_fun_00766510_optional_response_branch_check)
endif()
