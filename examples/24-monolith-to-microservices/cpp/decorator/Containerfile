FROM registry.access.redhat.com/ubi9/ubi:9.5 AS builder

RUN rm -f /etc/yum.repos.d/redhat.repo 2>/dev/null || true

RUN dnf install -y --quiet --setopt=install_weak_deps=False \
        gcc-toolset-14 cmake ninja-build git python3-pip \
        perl-FindBin perl-IPC-Cmd perl-Data-Dumper perl-Pod-Html \
        perl-Pod-Usage perl-File-Compare perl-File-Copy perl-File-Path \
        perl-Time-Piece perl-Getopt-Long perl-Digest-SHA \
        perl-threads perl-threads-shared perl-Thread-Queue \
        perl-Term-ANSIColor which \
    && dnf clean all && rm -rf /var/cache/dnf/*

ENV PATH="/opt/rh/gcc-toolset-14/root/usr/bin:${PATH}"
ENV LD_LIBRARY_PATH="/opt/rh/gcc-toolset-14/root/usr/lib64"
ENV CMAKE_POLICY_VERSION_MINIMUM=3.5

RUN pip3 install --no-cache-dir "conan~=2.0"
RUN conan profile detect --force && \
    sed -i 's|^compiler.cppstd=.*|compiler.cppstd=gnu17|' /root/.conan2/profiles/default

WORKDIR /src
COPY conanfile.py ./
RUN conan install . --build=missing -of=build -s build_type=Release

COPY CMakeLists.txt ./
COPY src/ src/

RUN source /opt/rh/gcc-toolset-14/enable && \
    cd build && \
    cmake .. -G Ninja \
        -DCMAKE_BUILD_TYPE=Release \
        -DCMAKE_TOOLCHAIN_FILE=conan_toolchain.cmake \
        -DCMAKE_CXX_STANDARD=23 && \
    ninja

FROM registry.access.redhat.com/ubi9/ubi-minimal:9.5 AS runtime

RUN microdnf install -y --setopt=install_weak_deps=0 libstdc++ curl-minimal && \
    microdnf clean all && rm -rf /var/cache/yum

COPY --from=builder /src/build/decorator /usr/local/bin/decorator

EXPOSE 8080
ENTRYPOINT ["/usr/local/bin/decorator"]
