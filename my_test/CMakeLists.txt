cmake_minimum_required(VERSION 3.4)
project(estimate_external_force CXX)

set(CMAKE_CXX_STANDARD 14)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# 如果 libfranka 没有安装到系统路径，请手动指定 Franka_DIR：
# cmake .. -DFranka_DIR=/path/to/libfranka/build
find_package(Franka REQUIRED)
find_package(Eigen3 REQUIRED)

add_executable(estimate_external_force estimate_external_force.cpp)
target_link_libraries(estimate_external_force Franka::Franka Eigen3::Eigen)

add_executable(payload_identification payload_identification.cpp)
target_link_libraries(payload_identification Franka::Franka Eigen3::Eigen)
