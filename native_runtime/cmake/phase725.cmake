# Single-process S6 Phase 725: narrow the session-facing complete FUN_00765c40
# boundary to an exact typed external-pass result without claiming unresolved
# wheel world-position/collision-provider semantics.

add_executable(shift_runtime_fun_00765c40_external_pass_result_check
  ${CMAKE_CURRENT_SOURCE_DIR}/tests/fun_00765c40_external_pass_result_check.cpp)
target_include_directories(
  shift_runtime_fun_00765c40_external_pass_result_check PRIVATE
  ${CMAKE_CURRENT_SOURCE_DIR}/include
  ${CMAKE_CURRENT_SOURCE_DIR}/src)
target_link_libraries(
  shift_runtime_fun_00765c40_external_pass_result_check PRIVATE
  shift_runtime_physics)
target_compile_options(
  shift_runtime_fun_00765c40_external_pass_result_check PRIVATE
  -Wall -Wextra -Wpedantic)

if(BUILD_TESTING)
  add_test(
    NAME shift_runtime_fun_00765c40_external_pass_result
    COMMAND shift_runtime_fun_00765c40_external_pass_result_check)
endif()
