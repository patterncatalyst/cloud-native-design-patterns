from conan import ConanFile

class CloudNative27Conan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"
    default_options = {"*/*:shared": False}

    def requirements(self):
        self.requires("drogon/1.9.8")
        self.requires("grpc/1.54.3")
        self.requires("protobuf/3.21.12")
