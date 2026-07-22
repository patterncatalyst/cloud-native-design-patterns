cmake_minimum_required(VERSION 3.25)
project(stream-processor LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 23)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(modern-cpp-kafka REQUIRED)
find_package(jsoncpp REQUIRED)

add_executable(stream-processor src/main.cpp)
target_link_libraries(stream-processor PRIVATE modern-cpp-kafka::modern-cpp-kafka JsonCpp::JsonCpp)
