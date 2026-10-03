target_sources(shift_runtime_physics PRIVATE
  ${CMAKE_CURRENT_SOURCE_DIR}/src/bmw_chassis_body_selection_gate.cpp)

add_executable(shift_runtime_bmw_chassis_body_selection_gate_check
  ${CMAKE_CURRENT_SOURCE_DIR}/tests/bmw_chassis_body_selection_gate_check.cpp)
target_include_directories(shift_runtime_bmw_chassis_body_selection_gate_check PRIVATE
  ${CMAKE_CURRENT_SOURCE_DIR}/src
  ${CMAKE_CURRENT_SOURCE_DIR}/tests)
target_link_libraries(shift_runtime_bmw_chassis_body_selection_gate_check PRIVATE
  shift_runtime_physics)
target_compile_options(shift_runtime_bmw_chassis_body_selection_gate_check PRIVATE
  -Wall -Wextra -Wpedantic)

if(BUILD_TESTING)
  add_test(
    NAME shift_runtime_bmw_chassis_body_selection_gate
    COMMAND shift_runtime_bmw_chassis_body_selection_gate_check)
endif()
