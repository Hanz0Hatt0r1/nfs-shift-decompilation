# Single-process S6 Phase 736: derive FUN_007675f0 projected scalar from the
# first weighted-vector output of the already-native FUN_00759c90 reduction.

add_executable(shift_runtime_fun_007675f0_projected_scalar_ownership_check
  ${CMAKE_CURRENT_SOURCE_DIR}/tests/fun_007675f0_projected_scalar_ownership_check.cpp)
target_include_directories(
  shift_runtime_fun_007675f0_projected_scalar_ownership_check PRIVATE
  ${CMAKE_CURRENT_SOURCE_DIR}/include
  ${CMAKE_CURRENT_SOURCE_DIR}/src
  ${CMAKE_CURRENT_SOURCE_DIR}/tests)
target_link_libraries(
  shift_runtime_fun_007675f0_projected_scalar_ownership_check PRIVATE
  shift_runtime_physics)
target_compile_options(
  shift_runtime_fun_007675f0_projected_scalar_ownership_check PRIVATE
  -Wall -Wextra -Wpedantic)

if(BUILD_TESTING)
  add_test(
    NAME shift_runtime_fun_007675f0_projected_scalar_ownership
    COMMAND shift_runtime_fun_007675f0_projected_scalar_ownership_check)
endif()
