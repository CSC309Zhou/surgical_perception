cmake_minimum_required(VERSION 3.16)
project(surgical_perception)

find_package(ament_cmake REQUIRED)
find_package(ament_cmake_python REQUIRED)
find_package(Python3 REQUIRED COMPONENTS Interpreter)
find_package(rosidl_default_generators REQUIRED)
find_package(sensor_msgs REQUIRED)
find_package(std_msgs REQUIRED)

rosidl_generate_interfaces(${PROJECT_NAME}
  "msg/InstrumentInstance.msg"
  "msg/InstrumentArray.msg"
  DEPENDENCIES sensor_msgs std_msgs)

# 消息生成器安装 surgical_perception；推理模块使用独立名称，避免覆盖生成文件。
ament_get_python_install_dir(PYTHON_INSTALL_DIR)
install(DIRECTORY surgical_perception_runtime
  DESTINATION "${PYTHON_INSTALL_DIR}"
  PATTERN "__pycache__" EXCLUDE)
configure_file(cmake/perception_node.in perception_node @ONLY)
install(PROGRAMS "${CMAKE_CURRENT_BINARY_DIR}/perception_node"
  DESTINATION lib/${PROJECT_NAME})
install(DIRECTORY launch config weights DESTINATION share/${PROJECT_NAME})
install(FILES README.md VALIDATION.md UBUNTU_RUN.md LICENSE requirements.txt requirements-test.txt
  DESTINATION share/${PROJECT_NAME})

option(BUILD_TESTING "Build package tests" ON)
if(BUILD_TESTING)
  find_package(ament_cmake_pytest REQUIRED)
  ament_has_pytest(HAS_PYTEST)
  if(NOT HAS_PYTEST)
    message(FATAL_ERROR "Install requirements-test.txt in the selected Python environment")
  endif()
  ament_add_pytest_test(runtime test/test_runtime.py
    APPEND_ENV PYTHONPATH=${CMAKE_CURRENT_SOURCE_DIR})
  ament_add_pytest_test(messages test/test_messages.py
    TIMEOUT 300
    APPEND_ENV PYTHONPATH=${CMAKE_CURRENT_SOURCE_DIR})
endif()
ament_export_dependencies(rosidl_default_runtime)
ament_package()
