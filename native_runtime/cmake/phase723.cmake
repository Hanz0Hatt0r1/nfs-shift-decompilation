# Single-process S6 Phase 723: prove HDVehicle+0xe0 belongs to FUN_007560c0
# vehicle setup and remove it from the later per-pass motion-read input.

add_executable(shift_runtime_fun_007560c0_motion_read_gate_setup_check
  ${CMAKE_CURRENT_SOURCE_DIR}/tests/fun_007560c0_motion_read_gate_setup_check.cpp)
target_include_directories(
  shift_runtime_fun_007560c0_motion_read_gate_setup_check PRIVATE
  ${CMAKE_CURRENT_SOURCE_DIR}/include
  ${CMAKE_CURRENT_SOURCE_DIR}/src)
target_link_libraries(
  shift_runtime_fun_007560c0_motion_read_gate_setup_check PRIVATE
  shift_runtime_physics)
target_compile_options(
  shift_runtime_fun_007560c0_motion_read_gate_setup_check PRIVATE
  -Wall -Wextra -Wpedantic)

if(BUILD_TESTING)
  add_test(
    NAME shift_runtime_fun_007560c0_motion_read_gate_setup
    COMMAND shift_runtime_fun_007560c0_motion_read_gate_setup_check)
endif()
