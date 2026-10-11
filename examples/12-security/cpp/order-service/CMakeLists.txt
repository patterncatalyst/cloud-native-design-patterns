cmake_minimum_required(VERSION 3.31)
project(cndp-12-security LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 23)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

add_compile_options(-Wall -Wextra)
# gcc-toolset-15's libstdc++ is newer than the one in ubi-minimal: link it statically.
add_link_options(-static-libstdc++ -static-libgcc)

set(CMAKE_INTERPROCEDURAL_OPTIMIZATION ON)

# Force --start-group/--end-group around static archives to resolve
# circular dependencies among Drogon's transitive deps (jsoncpp, trantor, etc.)
set(CMAKE_CXX_LINK_EXECUTABLE
    "<CMAKE_CXX_COMPILER> <FLAGS> <CMAKE_CXX_LINK_FLAGS> <LINK_FLAGS> \
     <OBJECTS> -o <TARGET> -Wl,--start-group <LINK_LIBRARIES> -Wl,--end-group")

find_package(Drogon CONFIG REQUIRED)
find_package(spdlog CONFIG REQUIRED)
find_package(jwt-cpp CONFIG REQUIRED)
find_package(nlohmann_json CONFIG REQUIRED)
find_package(Threads REQUIRED)

add_executable(order-service src/main.cpp)
target_include_directories(order-service PRIVATE src)
target_link_libraries(order-service PRIVATE
    Drogon::Drogon spdlog::spdlog jwt-cpp::jwt-cpp nlohmann_json::nlohmann_json Threads::Threads)

enable_testing()
add_executable(valet-test tests/valet_test.cpp)
target_include_directories(valet-test PRIVATE src)
target_link_libraries(valet-test PRIVATE jwt-cpp::jwt-cpp nlohmann_json::nlohmann_json)
add_test(NAME valet COMMAND valet-test)
