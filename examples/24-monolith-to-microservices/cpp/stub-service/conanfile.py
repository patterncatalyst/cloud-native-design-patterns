"""24-monolith-to-microservices/cpp/stub-service: Conan 2 recipe.

Exact pins from ConanCenter (the only remote); static libraries, built with GCC 15 / C++23.
"""

from conan import ConanFile


class Cndp24MonolithToMicroservicesCppStubServiceConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    default_options = {
        "*/*:shared": False,
        "drogon/*:with_boost": False,
    }

    def requirements(self):
        self.requires("drogon/1.9.13")
        self.requires("jsoncpp/1.9.8", override=True)  # drogon pins jsoncpp 1.9.5
        self.requires("util-linux-libuuid/2.41.2", override=True)  # drogon pins util-linux-libuuid 2.39.2
