# Process 3 Phase 715: attach the Phase 649 freshness-gated persistent vehicle
# transform sink to the existing shift_runtime fixed-step frame attachment. The
# implementation is header-only because the Process 2 publisher and Process 3
# consumer must share one inline process-local handoff state.

add_executable(shift_runtime_persistent_vehicle_runtime_wiring_check
  ${CMAKE_CURRENT_SOURCE_DIR}/tests/persistent_vehicle_runtime_wiring_check.cpp)
target_include_directories(
  shift_runtime_persistent_vehicle_runtime_wiring_check PRIVATE
  ${CMAKE_CURRENT_SOURCE_DIR}/src
  ${CMAKE_CURRENT_SOURCE_DIR}/tests)
target_link_libraries(
  shift_runtime_persistent_vehicle_runtime_wiring_check PRIVATE
  shift_runtime_physics
  Vulkan::Vulkan)
target_compile_options(
  shift_runtime_persistent_vehicle_runtime_wiring_check PRIVATE
  -Wall -Wextra -Wpedantic)

if(BUILD_TESTING)
  add_test(
    NAME shift_runtime_persistent_vehicle_runtime_wiring
    COMMAND shift_runtime_persistent_vehicle_runtime_wiring_check)
endif()
