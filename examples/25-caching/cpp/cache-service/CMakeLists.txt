cmake_minimum_required(VERSION 3.25)
project(cndp-25-caching LANGUAGES CXX)
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS ON)
set(CMAKE_INTERPROCEDURAL_OPTIMIZATION ON)
add_compile_options(-O2 -DNDEBUG)

set(CMAKE_CXX_LINK_EXECUTABLE
    "<CMAKE_CXX_COMPILER> <FLAGS> <CMAKE_CXX_LINK_FLAGS> <LINK_FLAGS> \
     <OBJECTS> -o <TARGET> -Wl,--start-group <LINK_LIBRARIES> -Wl,--end-group")

find_package(Drogon CONFIG REQUIRED)
find_package(hiredis CONFIG REQUIRED)
find_package(Threads REQUIRED)

add_executable(cache-service src/main.cpp)

# redis-plus-plus doesn't provide CMake config, so we need to find it manually
find_library(REDIS_PLUS_PLUS_LIB NAMES redis++_static redis++ REQUIRED)
find_path(REDIS_PLUS_PLUS_INCLUDE_DIR sw/redis++/redis++.h REQUIRED)

target_include_directories(cache-service PRIVATE ${REDIS_PLUS_PLUS_INCLUDE_DIR})
target_link_libraries(cache-service PRIVATE
    Drogon::Drogon ${REDIS_PLUS_PLUS_LIB} hiredis::hiredis Threads::Threads pq)
