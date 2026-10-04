# Process 3 Phase 648: wire the merged Phase 647 live Vulkan upload primitive
# into shift_runtime without duplicating its upload implementation.

target_sources(shift_runtime_physics PRIVATE
  ${CMAKE_CURRENT_SOURCE_DIR}/src/vehicle_world_transform_transport.cpp
  ${CMAKE_CURRENT_SOURCE_DIR}/src/live_vehicle_vertex_buffer_upload.cpp)

set_property(
  SOURCE ${CMAKE_CURRENT_SOURCE_DIR}/src/shift_runtime.cpp
  APPEND PROPERTY COMPILE_OPTIONS
    -include
    ${CMAKE_CURRENT_SOURCE_DIR}/include/shift_phase648_runtime_injection.hpp)

include(${CMAKE_CURRENT_LIST_DIR}/phase649.cmake)
