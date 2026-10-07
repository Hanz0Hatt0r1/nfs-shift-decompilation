# Single-process S6 Phase 731: own FUN_007675f0 distance-filter cap from
# FUN_00770e80 param_2 / HDVehicle+0xa0, shared by both recovered passes.

add_executable(shift_runtime_fun_007675f0_outer_channel_b_ownership_check
  ${CMAKE_CURRENT_SOURCE_DIR}/tests/fun_007675f0_outer_channel_b_ownership_check.cpp)
target_include_directories(
  shift_runtime_fun_007675f0_outer_channel_b_ownership_check PRIVATE
  ${CMAKE_CURRENT_SOURCE_DIR}/include
  ${CMAKE_CURRENT_SOURCE_DIR}/src
  ${CMAKE_CURRENT_SOURCE_DIR}/tests)
target_link_libraries(
  shift_runtime_fun_007675f0_outer_channel_b_ownership_check PRIVATE
  shift_runtime_physics)
target_compile_options(
  shift_runtime_fun_007675f0_outer_channel_b_ownership_check PRIVATE
  -Wall -Wextra -Wpedantic)

if(BUILD_TESTING)
  add_test(
    NAME shift_runtime_fun_007675f0_outer_channel_b_ownership
    COMMAND shift_runtime_fun_007675f0_outer_channel_b_ownership_check)
endif()
