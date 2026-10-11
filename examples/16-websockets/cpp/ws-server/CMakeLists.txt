cmake_minimum_required(VERSION 3.31)
project(ws-server CXX)

set(CMAKE_CXX_STANDARD 23)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

add_compile_options(-Wall -Wextra)
# gcc-toolset-15's libstdc++ is newer than the one in ubi-minimal: link it statically.
add_link_options(-static-libstdc++ -static-libgcc)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

set(CMAKE_CXX_LINK_EXECUTABLE
    "<CMAKE_CXX_COMPILER> <FLAGS> <CMAKE_CXX_LINK_FLAGS> <LINK_FLAGS> \
     <OBJECTS> -o <TARGET> -Wl,--start-group <LINK_LIBRARIES> -Wl,--end-group")

find_package(Drogon CONFIG REQUIRED)
find_package(redis++ CONFIG REQUIRED)  # redis-plus-plus (sw/redis++) from Conan; brings hiredis
find_package(Threads REQUIRED)

add_executable(ws-server src/main.cpp)

target_link_libraries(ws-server PRIVATE
    Drogon::Drogon redis++::redis++_static Threads::Threads)
