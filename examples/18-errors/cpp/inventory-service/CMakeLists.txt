cmake_minimum_required(VERSION 3.25)
project(cndp-18-inventory-service LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 23)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
set(CMAKE_INTERPROCEDURAL_OPTIMIZATION ON)
add_compile_options(-O2 -DNDEBUG)

# Linker workaround for circular static archive deps
set(CMAKE_CXX_LINK_EXECUTABLE
    "<CMAKE_CXX_COMPILER> <FLAGS> <CMAKE_CXX_LINK_FLAGS> <LINK_FLAGS> \
     <OBJECTS> -o <TARGET> -Wl,--start-group <LINK_LIBRARIES> -Wl,--end-group")

find_package(gRPC CONFIG REQUIRED)
find_package(protobuf CONFIG REQUIRED)
find_package(spdlog CONFIG REQUIRED)
find_package(Threads REQUIRED)

# Generate protobuf + gRPC stubs
set(PROTO_FILE ${CMAKE_CURRENT_SOURCE_DIR}/proto/inventory.proto)
set(PROTO_OUT ${CMAKE_CURRENT_BINARY_DIR}/proto)
file(MAKE_DIRECTORY ${PROTO_OUT})

# Find protobuf and grpc tools using Conan-provided targets
set(PROTOC $<TARGET_FILE:protobuf::protoc>)
set(GRPC_CPP_PLUGIN $<TARGET_FILE:gRPC::grpc_cpp_plugin>)

add_custom_command(
    OUTPUT ${PROTO_OUT}/inventory.pb.cc ${PROTO_OUT}/inventory.pb.h
           ${PROTO_OUT}/inventory.grpc.pb.cc ${PROTO_OUT}/inventory.grpc.pb.h
    COMMAND protobuf::protoc
        --proto_path=${CMAKE_CURRENT_SOURCE_DIR}/proto
        --cpp_out=${PROTO_OUT}
        --grpc_out=${PROTO_OUT}
        --plugin=protoc-gen-grpc=$<TARGET_FILE:gRPC::grpc_cpp_plugin>
        ${PROTO_FILE}
    DEPENDS ${PROTO_FILE} protobuf::protoc gRPC::grpc_cpp_plugin
)

add_executable(inventory-service
    src/main.cpp
    ${PROTO_OUT}/inventory.pb.cc
    ${PROTO_OUT}/inventory.grpc.pb.cc)
target_include_directories(inventory-service PRIVATE ${PROTO_OUT})
target_link_libraries(inventory-service PRIVATE
    gRPC::grpc++ protobuf::protobuf spdlog::spdlog Threads::Threads)
