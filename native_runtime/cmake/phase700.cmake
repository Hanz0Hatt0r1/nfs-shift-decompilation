target_sources(shift_runtime_physics PRIVATE
  ${CMAKE_CURRENT_SOURCE_DIR}/src/vehicle_body_pose_runtime_handoff.cpp)

add_executable(shift_runtime_vehicle_body_pose_runtime_handoff_check
  ${CMAKE_CURRENT_SOURCE_DIR}/tests/vehicle_body_pose_runtime_handoff_check.cpp)
target_include_directories(shift_runtime_vehicle_body_pose_runtime_handoff_check PRIVATE
  ${CMAKE_CURRENT_SOURCE_DIR}/src
  ${CMAKE_CURRENT_SOURCE_DIR}/tests)
target_link_libraries(shift_runtime_vehicle_body_pose_runtime_handoff_check PRIVATE
  shift_runtime_physics)
target_compile_options(shift_runtime_vehicle_body_pose_runtime_handoff_check PRIVATE
  -Wall -Wextra -Wpedantic)

if(BUILD_TESTING)
  add_test(
    NAME shift_runtime_vehicle_body_pose_runtime_handoff
    COMMAND shift_runtime_vehicle_body_pose_runtime_handoff_check)
endif()
