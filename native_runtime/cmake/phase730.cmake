# Single-process S6 Phase 730: move FUN_007675f0 HDVehicle+0x4080
# previous-distance state from per-pass provider data into persistent session state.

add_executable(shift_runtime_fun_007675f0_distance_state_ownership_check
  ${CMAKE_CURRENT_SOURCE_DIR}/tests/fun_007675f0_distance_state_ownership_check.cpp)
target_include_directories(
  shift_runtime_fun_007675f0_distance_state_ownership_check PRIVATE
  ${CMAKE_CURRENT_SOURCE_DIR}/include
  ${CMAKE_CURRENT_SOURCE_DIR}/src
  ${CMAKE_CURRENT_SOURCE_DIR}/tests)
target_link_libraries(
  shift_runtime_fun_007675f0_distance_state_ownership_check PRIVATE
  shift_runtime_physics)
target_compile_options(
  shift_runtime_fun_007675f0_distance_state_ownership_check PRIVATE
  -Wall -Wextra -Wpedantic)

if(BUILD_TESTING)
  add_test(
    NAME shift_runtime_fun_007675f0_distance_state_ownership
    COMMAND shift_runtime_fun_007675f0_distance_state_ownership_check)
endif()

include(${CMAKE_CURRENT_LIST_DIR}/phase731.cmake)
