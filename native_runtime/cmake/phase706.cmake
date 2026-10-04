target_sources(shift_runtime_physics PRIVATE
  ${CMAKE_CURRENT_SOURCE_DIR}/src/persistent_bmw_vehicle_world_transform.cpp)

add_executable(shift_runtime_persistent_bmw_vehicle_world_transform_check
  ${CMAKE_CURRENT_SOURCE_DIR}/tests/persistent_bmw_vehicle_world_transform_check.cpp)
target_include_directories(shift_runtime_persistent_bmw_vehicle_world_transform_check PRIVATE
  ${CMAKE_CURRENT_SOURCE_DIR}/src
  ${CMAKE_CURRENT_SOURCE_DIR}/tests)
target_link_libraries(shift_runtime_persistent_bmw_vehicle_world_transform_check PRIVATE
  shift_runtime_physics)
target_compile_options(shift_runtime_persistent_bmw_vehicle_world_transform_check PRIVATE
  -Wall -Wextra -Wpedantic)

if(BUILD_TESTING)
  add_test(
    NAME shift_runtime_persistent_bmw_vehicle_world_transform
    COMMAND shift_runtime_persistent_bmw_vehicle_world_transform_check)
endif()

include(${CMAKE_CURRENT_LIST_DIR}/phase648.cmake)
