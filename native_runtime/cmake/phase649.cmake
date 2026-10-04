# Process 3 Phase 649: consume the freshness-checked Phase 706 persistent
# vehicle transform through the already-merged Phase 647 Vulkan upload primitive.

target_sources(shift_runtime_physics PRIVATE
  ${CMAKE_CURRENT_SOURCE_DIR}/src/persistent_vehicle_vulkan_upload.cpp)

add_executable(shift_runtime_persistent_vehicle_vulkan_upload_check
  ${CMAKE_CURRENT_SOURCE_DIR}/tests/persistent_vehicle_vulkan_upload_check.cpp)
target_include_directories(
  shift_runtime_persistent_vehicle_vulkan_upload_check PRIVATE
  ${CMAKE_CURRENT_SOURCE_DIR}/src
  ${CMAKE_CURRENT_SOURCE_DIR}/tests)
target_link_libraries(
  shift_runtime_persistent_vehicle_vulkan_upload_check PRIVATE
  shift_runtime_physics
  Vulkan::Vulkan)
target_compile_options(
  shift_runtime_persistent_vehicle_vulkan_upload_check PRIVATE
  -Wall -Wextra -Wpedantic)

if(BUILD_TESTING)
  add_test(
    NAME shift_runtime_persistent_vehicle_vulkan_upload
    COMMAND shift_runtime_persistent_vehicle_vulkan_upload_check)
endif()
