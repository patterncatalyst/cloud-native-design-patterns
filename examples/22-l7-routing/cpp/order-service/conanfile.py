from conan import ConanFile

class CloudNative22OrderConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"
    default_options = {"*/*:shared": False}

    def requirements(self):
        self.requires("drogon/1.9.8")
