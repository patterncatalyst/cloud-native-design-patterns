cmake_minimum_required(VERSION 3.25)
project(shipping-consumer CXX)

set(CMAKE_CXX_STANDARD 23)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

find_package(modern-cpp-kafka CONFIG REQUIRED)
find_package(jsoncpp CONFIG REQUIRED)

add_executable(shipping-consumer src/main.cpp)
target_link_libraries(shipping-consumer PRIVATE modern-cpp-kafka::modern-cpp-kafka jsoncpp_lib pq)
