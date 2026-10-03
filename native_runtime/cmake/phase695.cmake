target_sources(shift_runtime_physics PRIVATE
  ${CMAKE_CURRENT_SOURCE_DIR}/src/persistent_body_pose_snapshot.cpp)

add_executable(shift_runtime_persistent_body_pose_runtime_state_check
  ${CMAKE_CURRENT_SOURCE_DIR}/tests/persistent_body_pose_runtime_state_check.cpp)
target_include_directories(shift_runtime_persistent_body_pose_runtime_state_check PRIVATE
  ${CMAKE_CURRENT_SOURCE_DIR}/src)
target_link_libraries(shift_runtime_persistent_body_pose_runtime_state_check PRIVATE
  shift_runtime_physics)
target_compile_options(shift_runtime_persistent_body_pose_runtime_state_check PRIVATE
  -Wall -Wextra -Wpedantic)

if(BUILD_TESTING)
  add_test(
    NAME shift_runtime_persistent_body_pose_runtime_state
    COMMAND shift_runtime_persistent_body_pose_runtime_state_check)
endif()

include(${CMAKE_CURRENT_LIST_DIR}/phase696.cmake)
