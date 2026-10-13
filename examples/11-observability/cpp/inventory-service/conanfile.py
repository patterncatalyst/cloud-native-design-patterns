"""11-observability/cpp/inventory-service: Conan 2 recipe.

Exact pins from ConanCenter (the only remote); static libraries, built with GCC 15 / C++23.
Traces and metrics use opentelemetry-cpp (OTLP/HTTP).
"""

from conan import ConanFile


class Cndp11ObservabilityCppInventoryServiceConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    default_options = {
        "*/*:shared": False,
    }

    def requirements(self):
        self.requires("grpc/1.84.0")
        self.requires("protobuf/6.33.5")
        self.requires("opentelemetry-cpp/1.26.0")
        self.requires("spdlog/1.17.0")
        # opentelemetry-cpp pins nlohmann_json 3.11.3; take the newest release.
        self.requires("nlohmann_json/3.12.0", override=True)
        self.requires("fmt/12.2.0", override=True)  # spdlog pins fmt 12.1.0
