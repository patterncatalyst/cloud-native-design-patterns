"""examples/12-security/cpp — Conan 2 recipe.

Security patterns demonstration service: sidecar trust, valet keys, per-tenant
bulkhead. In-memory state only; no database.

Dependencies:
- Drogon (REST framework with jsoncpp for JSON)
- spdlog (structured logging)
- OpenSSL (HMAC for valet keys, installed as system package)
"""

from conan import ConanFile


class CloudNative12Conan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    default_options = {
        # Static linkage everywhere for a portable runtime image.
        "*/*:shared": False,
        # OpenSSL FIPS skipped (Digest::SHA on UBI 9 without EPEL).
        "openssl/*:no_fips": True,
    }

    def requirements(self):
        # Drogon REST framework (includes jsoncpp for JSON responses)
        self.requires("drogon/1.9.8")
        # Structured logging
        self.requires("spdlog/1.15.0")
