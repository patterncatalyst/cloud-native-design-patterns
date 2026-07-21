# examples/12-security/cpp — Drogon + OpenSSL on UBI 9.
#
# Multi-stage build: UBI 9 builder with GCC 14 toolset, Conan 2, CMake + Ninja.
# OpenSSL installed from UBI's AppStream as a system package (openssl-devel at
# build, openssl-libs at runtime) for HMAC valet key signing.
#
# First build compiles Drogon and its deps (~10-15 min cold cache); warm
# Conan cache makes subsequent builds < 1 minute.

FROM registry.access.redhat.com/ubi9/ubi:9.5 AS builder

# Silence subscription-manager warnings in containerized builds
RUN rm -f /etc/yum.repos.d/redhat.repo 2>/dev/null || true

RUN dnf install -y --quiet --setopt=install_weak_deps=False \
        gcc-toolset-14 \
        cmake ninja-build git python3-pip \
        openssl-devel \
        perl-FindBin perl-IPC-Cmd perl-Data-Dumper perl-Pod-Html \
        perl-Pod-Usage perl-File-Compare perl-File-Copy perl-File-Path \
        perl-Time-Piece perl-Getopt-Long perl-Digest-SHA \
        perl-threads perl-threads-shared perl-Thread-Queue \
        perl-Term-ANSIColor \
        which \
    && dnf clean all \
    && rm -rf /var/cache/dnf/*

ENV PATH="/opt/rh/gcc-toolset-14/root/usr/bin:${PATH}"
ENV LD_LIBRARY_PATH="/opt/rh/gcc-toolset-14/root/usr/lib64"

# CMake 3.25+ policy compatibility
ENV CMAKE_POLICY_VERSION_MINIMUM=3.5

RUN pip3 install --no-cache-dir "conan~=2.0"

RUN conan profile detect --force && \
    sed -i 's|^compiler.cppstd=.*|compiler.cppstd=gnu17|' \
        /root/.conan2/profiles/default

WORKDIR /src

COPY conanfile.py conan.lock ./
RUN if [ -s conan.lock ]; then \
        echo "==> Using committed conan.lock with --lockfile-partial"; \
        conan install . --output-folder=build/conan \
                        -s build_type=Release \
                        --lockfile=conan.lock \
                        --lockfile-partial \
                        --build=missing ; \
    else \
        echo "==> conan.lock is empty placeholder; resolving graph fresh"; \
        rm -f conan.lock ; \
        conan install . --output-folder=build/conan \
                        -s build_type=Release \
                        --build=missing ; \
    fi

COPY src/ ./src/
COPY CMakeLists.txt ./

RUN cmake -S . -B build -G Ninja \
        -DCMAKE_BUILD_TYPE=Release \
        -DCMAKE_TOOLCHAIN_FILE=build/conan/conan_toolchain.cmake \
    && cmake --build build -j"$(nproc)" \
    && strip --strip-all build/order-service

# ════════════════════════════════════════════════════════════════════════
# Runtime — ubi-minimal + libstdc++ + openssl-libs.
# ════════════════════════════════════════════════════════════════════════
FROM registry.access.redhat.com/ubi9/ubi-minimal:9.5 AS runtime

RUN microdnf install -y --setopt=install_weak_deps=0 \
        libstdc++ \
        openssl-libs \
    && microdnf clean all \
    && rm -rf /var/cache/yum

COPY --from=builder /src/build/order-service /usr/local/bin/order-service

USER 1001:1001
EXPOSE 8080

ENV VALET_SECRET=demo-secret-do-not-use-in-prod

ENTRYPOINT ["/usr/local/bin/order-service"]
