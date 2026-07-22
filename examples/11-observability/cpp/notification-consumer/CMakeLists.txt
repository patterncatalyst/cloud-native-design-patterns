cmake_minimum_required(VERSION 3.25)
project(notification-consumer CXX)

set(CMAKE_CXX_STANDARD 23)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

find_package(modern-cpp-kafka CONFIG REQUIRED)

add_executable(notification-consumer src/main.cpp)
target_link_libraries(notification-consumer PRIVATE modern-cpp-kafka::modern-cpp-kafka pq)
