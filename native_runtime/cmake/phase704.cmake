target_sources(shift_runtime_physics PRIVATE
  ${CMAKE_CURRENT_SOURCE_DIR}/src/bmw_body0_bind_frame_admission.cpp
  ${CMAKE_CURRENT_SOURCE_DIR}/src/bmw_body0_vhf_world_matrix_composition.cpp)

add_executable(shift_runtime_bmw_body0_bind_frame_admission_check
  ${CMAKE_CURRENT_SOURCE_DIR}/tests/bmw_body0_bind_frame_admission_check.cpp)
target_link_libraries(shift_runtime_bmw_body0_bind_frame_admission_check PRIVATE
  shift_runtime_physics)
target_compile_options(shift_runtime_bmw_body0_bind_frame_admission_check PRIVATE
  -Wall -Wextra -Wpedantic)

add_executable(shift_runtime_bmw_body0_vhf_world_matrix_composition_check
  ${CMAKE_CURRENT_SOURCE_DIR}/tests/bmw_body0_vhf_world_matrix_composition_check.cpp
  ${CMAKE_CURRENT_SOURCE_DIR}/src/vehicle_world_transform_transport.cpp)
target_include_directories(shift_runtime_bmw_body0_vhf_world_matrix_composition_check PRIVATE
  ${CMAKE_CURRENT_SOURCE_DIR}/src
  ${CMAKE_CURRENT_SOURCE_DIR}/tests)
target_link_libraries(shift_runtime_bmw_body0_vhf_world_matrix_composition_check PRIVATE
  shift_runtime_physics)
target_compile_options(shift_runtime_bmw_body0_vhf_world_matrix_composition_check PRIVATE
  -Wall -Wextra -Wpedantic)

if(BUILD_TESTING)
  add_test(
    NAME shift_runtime_bmw_body0_bind_frame_admission
    COMMAND shift_runtime_bmw_body0_bind_frame_admission_check)
  add_test(
    NAME shift_runtime_bmw_body0_vhf_world_matrix_composition
    COMMAND shift_runtime_bmw_body0_vhf_world_matrix_composition_check)
endif()

include(${CMAKE_CURRENT_LIST_DIR}/phase705.cmake)
