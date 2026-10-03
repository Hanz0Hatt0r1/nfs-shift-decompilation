# Incremental native physics registrations added after the main runtime target.
# Keeping recent phases here avoids repeatedly rewriting the large top-level file.

target_sources(shift_runtime_physics PRIVATE
  ${CMAKE_CURRENT_SOURCE_DIR}/src/wheel_force_aggregate.cpp)

add_executable(shift_runtime_wheel_force_aggregate_check
  ${CMAKE_CURRENT_SOURCE_DIR}/tests/wheel_force_aggregate_check.cpp)
target_link_libraries(shift_runtime_wheel_force_aggregate_check PRIVATE
  shift_runtime_physics)
target_compile_options(shift_runtime_wheel_force_aggregate_check PRIVATE
  -Wall -Wextra -Wpedantic)

if(BUILD_TESTING)
  add_test(
    NAME shift_runtime_wheel_force_aggregate
    COMMAND shift_runtime_wheel_force_aggregate_check)
endif()
