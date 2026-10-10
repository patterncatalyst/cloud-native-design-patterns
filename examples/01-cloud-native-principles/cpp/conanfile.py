"""examples/01-cloud-native-principles/cpp: Conan 2 recipe.

Drogon REST service with libpq (direct, no libpqxx), spdlog logging and OpenTelemetry
C++ (OTLP over HTTP). Exact pins; ConanCenter is the only remote.
"""

from conan import ConanFile


class CloudNative01Conan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    default_options = {
        # Static linkage everywhere for a portable runtime image.
        "*/*:shared": False,
        # Drogon only needs Boost for pre-C++17 toolchains.
        "drogon/*:with_boost": False,
    }

    def requirements(self):
        self.requires("drogon/1.9.13")
        self.requires("libpq/17.11")
        self.requires("spdlog/1.17.0")
        self.requires("opentelemetry-cpp/1.26.0")
        # opentelemetry-cpp pins nlohmann_json 3.11.3; take the newest release.
        self.requires("nlohmann_json/3.12.0", override=True)
