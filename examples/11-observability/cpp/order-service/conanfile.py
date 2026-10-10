"""11-observability/cpp/order-service: Conan 2 recipe.

Exact pins from ConanCenter (the only remote); static libraries, built with GCC 15 / C++23.
Kafka is librdkafka's C++ API (rdkafka++); traces and metrics use opentelemetry-cpp.
"""

from conan import ConanFile


class Cndp11OrderServiceConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    default_options = {
        "*/*:shared": False,
        "drogon/*:with_boost": False,
    }

    def requirements(self):
        self.requires("drogon/1.9.13")
        self.requires("grpc/1.84.0")
        self.requires("protobuf/6.33.5")
        self.requires("librdkafka/2.14.2")
        self.requires("libpq/17.11")
        self.requires("spdlog/1.17.0")
        self.requires("opentelemetry-cpp/1.26.0")
        # opentelemetry-cpp pins nlohmann_json 3.11.3; take the newest release.
        self.requires("nlohmann_json/3.12.0", override=True)
