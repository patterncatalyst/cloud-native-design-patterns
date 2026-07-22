cmake_minimum_required(VERSION 3.25)
project(decorator CXX)

set(CMAKE_CXX_STANDARD 23)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

set(CMAKE_CXX_LINK_EXECUTABLE
    "<CMAKE_CXX_COMPILER> <FLAGS> <CMAKE_CXX_LINK_FLAGS> <LINK_FLAGS> <OBJECTS> -o <TARGET> -Wl,--start-group <LINK_LIBRARIES> -Wl,--end-group")

find_package(Threads REQUIRED)
find_package(Drogon CONFIG REQUIRED)
find_package(hiredis CONFIG REQUIRED)
find_package(modern-cpp-kafka CONFIG REQUIRED)

find_library(REDIS_PLUS_PLUS_LIB NAMES redis++_static redis++ REQUIRED)
find_path(REDIS_PLUS_PLUS_INCLUDE_DIR sw/redis++/redis++.h REQUIRED)

add_executable(decorator src/main.cpp)
target_include_directories(decorator PRIVATE ${REDIS_PLUS_PLUS_INCLUDE_DIR})
target_link_libraries(decorator PRIVATE
    Drogon::Drogon
    ${REDIS_PLUS_PLUS_LIB}
    hiredis::hiredis
    modern-cpp-kafka::modern-cpp-kafka
    Threads::Threads)
