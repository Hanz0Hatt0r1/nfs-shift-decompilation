# Single-process S6 Phase 740: make HDVehicle+0x38dc query-cache lifetime
# session-owned while leaving collision-provider behavior external.

add_executable(shift_runtime_fun_00765c40_query_cache_lifetime_check
  ${CMAKE_CURRENT_SOURCE_DIR}/tests/fun_00765c40_query_cache_lifetime_check.cpp)
target_include_directories(
  shift_runtime_fun_00765c40_query_cache_lifetime_check PRIVATE
  ${CMAKE_CURRENT_SOURCE_DIR}/include
  ${CMAKE_CURRENT_SOURCE_DIR}/src
  ${CMAKE_CURRENT_SOURCE_DIR}/tests)
target_link_libraries(
  shift_runtime_fun_00765c40_query_cache_lifetime_check PRIVATE
  shift_runtime_physics)
target_compile_options(
  shift_runtime_fun_00765c40_query_cache_lifetime_check PRIVATE
  -Wall -Wextra -Wpedantic)

if(BUILD_TESTING)
  add_test(
    NAME shift_runtime_fun_00765c40_query_cache_lifetime
    COMMAND shift_runtime_fun_00765c40_query_cache_lifetime_check)
endif()

include(${CMAKE_CURRENT_LIST_DIR}/phase741.cmake)
