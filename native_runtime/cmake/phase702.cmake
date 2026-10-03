target_sources(shift_runtime_physics PRIVATE
  ${CMAKE_CURRENT_SOURCE_DIR}/src/bmw_wheel_spindle_body_topology.cpp)

add_executable(shift_runtime_bmw_wheel_spindle_body_topology_check
  ${CMAKE_CURRENT_SOURCE_DIR}/tests/bmw_wheel_spindle_body_topology_check.cpp)
target_include_directories(shift_runtime_bmw_wheel_spindle_body_topology_check PRIVATE
  ${CMAKE_CURRENT_SOURCE_DIR}/src)
target_link_libraries(shift_runtime_bmw_wheel_spindle_body_topology_check PRIVATE
  shift_runtime_physics)
target_compile_options(shift_runtime_bmw_wheel_spindle_body_topology_check PRIVATE
  -Wall -Wextra -Wpedantic)

if(BUILD_TESTING)
  add_test(
    NAME shift_runtime_bmw_wheel_spindle_body_topology
    COMMAND shift_runtime_bmw_wheel_spindle_body_topology_check)
endif()

include(${CMAKE_CURRENT_LIST_DIR}/phase703.cmake)
