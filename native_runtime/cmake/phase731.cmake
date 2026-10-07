# Single-process S6 Phase 731: move FUN_007675f0 HDVehicle+0xa0
# distance-filter cap from per-pass provider data into immutable session setup.

add_executable(shift_runtime_fun_007675f0_distance_filter_cap_ownership_check
  ${CMAKE_CURRENT_SOURCE_DIR}/tests/fun_007675f0_distance_filter_cap_ownership_check.cpp)
target_include_directories(
  shift_runtime_fun_007675f0_distance_filter_cap_ownership_check PRIVATE
  ${CMAKE_CURRENT_SOURCE_DIR}/include
  ${CMAKE_CURRENT_SOURCE_DIR}/src
  ${CMAKE_CURRENT_SOURCE_DIR}/tests)
target_link_libraries(
  shift_runtime_fun_007675f0_distance_filter_cap_ownership_check PRIVATE
  shift_runtime_physics)
target_compile_options(
  shift_runtime_fun_007675f0_distance_filter_cap_ownership_check PRIVATE
  -Wall -Wextra -Wpedantic)

if(BUILD_TESTING)
  add_test(
    NAME shift_runtime_fun_007675f0_distance_filter_cap_ownership
    COMMAND shift_runtime_fun_007675f0_distance_filter_cap_ownership_check)
endif()
