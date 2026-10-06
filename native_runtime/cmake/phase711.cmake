# Process 2 Phase 711: consume the selector-complete Process 1 BMW offset33b
# family without assuming one profile/race-mode default.

target_sources(shift_runtime_physics PRIVATE
  ${CMAKE_CURRENT_SOURCE_DIR}/src/bmw_offset33b_race_mode_selector.cpp)

add_executable(shift_runtime_bmw_offset33b_race_mode_selector_check
  ${CMAKE_CURRENT_SOURCE_DIR}/tests/bmw_offset33b_race_mode_selector_check.cpp)
target_link_libraries(
  shift_runtime_bmw_offset33b_race_mode_selector_check PRIVATE
  shift_runtime_physics)
target_compile_options(
  shift_runtime_bmw_offset33b_race_mode_selector_check PRIVATE
  -Wall -Wextra -Wpedantic)

if(BUILD_TESTING)
  add_test(
    NAME shift_runtime_bmw_offset33b_race_mode_selector
    COMMAND shift_runtime_bmw_offset33b_race_mode_selector_check)
endif()
