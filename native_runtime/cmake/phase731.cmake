# Single-process S6 Phase 731: move PC retail FUN_007675f0 this+0xa0
# distance-filter cap out of the production per-pass provider payload and into
# explicit one-time session setup state. The upstream initializer/value remains
# unresolved and is not promoted.

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

include(${CMAKE_CURRENT_LIST_DIR}/phase732.cmake)
