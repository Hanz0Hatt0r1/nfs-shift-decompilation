# Single-process S6 Phase 735: derive FUN_007675f0 base/alignment scalar
# intermediates from current BODY0 state and probe-derived planar direction.

add_executable(shift_runtime_fun_007675f0_body_owned_scalars_check
  ${CMAKE_CURRENT_SOURCE_DIR}/tests/fun_007675f0_body_owned_scalars_check.cpp)
target_include_directories(
  shift_runtime_fun_007675f0_body_owned_scalars_check PRIVATE
  ${CMAKE_CURRENT_SOURCE_DIR}/include
  ${CMAKE_CURRENT_SOURCE_DIR}/src
  ${CMAKE_CURRENT_SOURCE_DIR}/tests)
target_link_libraries(
  shift_runtime_fun_007675f0_body_owned_scalars_check PRIVATE
  shift_runtime_physics)
target_compile_options(
  shift_runtime_fun_007675f0_body_owned_scalars_check PRIVATE
  -Wall -Wextra -Wpedantic)

if(BUILD_TESTING)
  add_test(
    NAME shift_runtime_fun_007675f0_body_owned_scalars
    COMMAND shift_runtime_fun_007675f0_body_owned_scalars_check)
endif()
