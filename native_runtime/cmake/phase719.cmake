# Single-process S6 Phase 719: internalize the PC FUN_00770e80-derived
# HDVehicle+0x4084/+0x408c state. The pair is initialized to zero, shared by
# both current passes, and refreshed only after the complete outer update.

add_executable(shift_runtime_fun_007682c0_projection_state_check
  ${CMAKE_CURRENT_SOURCE_DIR}/tests/fun_007682c0_projection_state_check.cpp)
target_include_directories(
  shift_runtime_fun_007682c0_projection_state_check PRIVATE
  ${CMAKE_CURRENT_SOURCE_DIR}/include
  ${CMAKE_CURRENT_SOURCE_DIR}/src)
target_link_libraries(
  shift_runtime_fun_007682c0_projection_state_check PRIVATE
  shift_runtime_physics)
target_compile_options(
  shift_runtime_fun_007682c0_projection_state_check PRIVATE
  -Wall -Wextra -Wpedantic)

if(BUILD_TESTING)
  add_test(
    NAME shift_runtime_fun_007682c0_projection_state
    COMMAND shift_runtime_fun_007682c0_projection_state_check)
endif()

include(${CMAKE_CURRENT_LIST_DIR}/phase720.cmake)
