# Single-process S6 Phase 728: prove and implement the exact-offset PC retail
# FUN_007618f0 producer for HDVehicle+0x3938 local query sample.
# Storage-owner/lifetime joins remain separate boundaries.

target_sources(shift_runtime_physics PRIVATE
  ${CMAKE_CURRENT_SOURCE_DIR}/src/fun_007618f0_local_sample_producer.cpp)

add_executable(shift_runtime_fun_007618f0_local_sample_producer_check
  ${CMAKE_CURRENT_SOURCE_DIR}/tests/fun_007618f0_local_sample_producer_check.cpp)
target_include_directories(
  shift_runtime_fun_007618f0_local_sample_producer_check PRIVATE
  ${CMAKE_CURRENT_SOURCE_DIR}/include
  ${CMAKE_CURRENT_SOURCE_DIR}/src)
target_link_libraries(
  shift_runtime_fun_007618f0_local_sample_producer_check PRIVATE
  shift_runtime_physics)
target_compile_options(
  shift_runtime_fun_007618f0_local_sample_producer_check PRIVATE
  -Wall -Wextra -Wpedantic)

if(BUILD_TESTING)
  add_test(
    NAME shift_runtime_fun_007618f0_local_sample_producer
    COMMAND shift_runtime_fun_007618f0_local_sample_producer_check)
endif()
