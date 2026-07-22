cmake_minimum_required(VERSION 3.25)
project(order-service LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 23)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(Drogon REQUIRED)
find_package(modern-cpp-kafka REQUIRED)

add_executable(order-service src/main.cpp)
target_link_libraries(order-service PRIVATE Drogon::Drogon modern-cpp-kafka::modern-cpp-kafka pq)
