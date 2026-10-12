# Prerequisites & Setup

Install the tools you need to run the examples on Fedora or RHEL.

Everything runs in containers, so you do not need a local JDK, Python, Go, .NET or C++
toolchain to run an example. You need Docker Engine, a handful of CLI tools, and a Fedora or
RHEL host. Local toolchains are optional and only needed if you want to build or test a
service outside its container.

The instructions here cover Fedora and RHEL (and compatible rebuilds) only.

---

## Container runtime

The examples run on **Docker Engine** with the Compose plugin. Install it from Docker's
own Fedora or RHEL repository.

### Fedora

Remove conflicting packages first. Fedora and distribution-provided Docker or Moby
packages conflict with Docker's own. `dnf` reports if none are installed.

```bash
sudo dnf remove docker docker-client docker-client-latest docker-common docker-latest \
  docker-latest-logrotate docker-logrotate docker-selinux docker-engine-selinux \
  docker-engine moby-engine podman-docker
```

Then install:

```bash
sudo dnf install -y dnf-plugins-core
sudo dnf config-manager addrepo --from-repofile=https://download.docker.com/linux/fedora/docker-ce.repo
sudo dnf install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```

### RHEL

Remove conflicting packages first. `dnf` reports if none are installed.

```bash
sudo dnf remove docker docker-client docker-client-latest docker-common docker-latest \
  docker-latest-logrotate docker-logrotate docker-engine podman runc
```

Then install:

```bash
sudo dnf install -y dnf-plugins-core
sudo dnf config-manager --add-repo https://download.docker.com/linux/rhel/docker-ce.repo
sudo dnf install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```

### Start the service and allow your user to use it

```bash
sudo systemctl enable --now docker
sudo usermod -aG docker $USER
```

Log out and back in so the `docker` group applies to your session.

Verify:

```bash
docker --version
docker compose version
docker run --rm hello-world
```

---

## Kubernetes tools (optional)

The examples run on `docker compose` and need no cluster. Appendix R runs Example 05 on
minikube; install these tools when you reach it. minikube uses the Docker driver on the same
Docker Engine as compose, with the `default` Docker context. Appendix S runs the same example on
OpenShift Local; its tools are in the last subsection.

### minikube

Pinned to v1.39.0, with the binary checked against its published SHA-256 file:

```bash
MINIKUBE_VERSION=v1.39.0
mkdir -p ~/.local/bin && cd "$(mktemp -d)"
curl -fsSLO "https://github.com/kubernetes/minikube/releases/download/${MINIKUBE_VERSION}/minikube-linux-amd64"
echo "$(curl -fsSL "https://github.com/kubernetes/minikube/releases/download/${MINIKUBE_VERSION}/minikube-linux-amd64.sha256")  minikube-linux-amd64" | sha256sum -c -
install minikube-linux-amd64 ~/.local/bin/minikube
```

### kubectl

Pinned to v1.36.5 (the Kubernetes version the minikube profile runs), checked against its
published SHA-256:

```bash
KUBECTL_VERSION=v1.36.5
mkdir -p ~/.local/bin && cd "$(mktemp -d)"
curl -fsSLO "https://dl.k8s.io/release/${KUBECTL_VERSION}/bin/linux/amd64/kubectl"
echo "$(curl -fsSL "https://dl.k8s.io/release/${KUBECTL_VERSION}/bin/linux/amd64/kubectl.sha256")  kubectl" | sha256sum -c -
install kubectl ~/.local/bin/kubectl
```

### Helm

Helm 4, pinned, with the tarball checked against its published SHA-256 file:

```bash
HELM_VERSION=4.3.0
cd "$(mktemp -d)"
curl -fsSLO "https://get.helm.sh/helm-v${HELM_VERSION}-linux-amd64.tar.gz"
curl -fsSLO "https://get.helm.sh/helm-v${HELM_VERSION}-linux-amd64.tar.gz.sha256sum"
sha256sum -c "helm-v${HELM_VERSION}-linux-amd64.tar.gz.sha256sum"
tar -xzf "helm-v${HELM_VERSION}-linux-amd64.tar.gz" linux-amd64/helm
sudo install linux-amd64/helm /usr/local/bin/helm
```

### OpenShift Local (Appendix S)

OpenShift Local (CRC) runs OpenShift 4.22 in a virtual machine on Fedora or RHEL, so the host
needs KVM. Pinned to crc 2.64.0, with the archive checked against the SHA-256 file Red Hat
publishes. Run one cluster at a time: stop minikube before `crc start`.

```bash
CRC_VERSION=2.64.0
mkdir -p ~/.local/bin && cd "$(mktemp -d)"
base="https://mirror.openshift.com/pub/openshift-v4/clients/crc/${CRC_VERSION}"
curl -fsSLO "${base}/crc-linux-amd64.tar.xz"
curl -fsSL "${base}/sha256sum.txt" | grep ' crc-linux-amd64.tar.xz$' | sha256sum -c -
tar -xJf crc-linux-amd64.tar.xz --strip-components=1 --wildcards '*/crc'
install crc ~/.local/bin/crc
sudo dnf install -y skopeo jq
crc setup
```

`crc setup` also makes `api.crc.testing` and `*.apps-crc.testing` resolve on the host, which is
what lets the Routes work without tunnels. `oc` comes with CRC: `eval "$(crc oc-env)"`.

Download your pull secret from the Red Hat Hybrid Cloud Console (a free Red Hat account is
enough) to a file, and give crc its path once. The scripts never open the file, and nothing in
this book prints it:

```bash
crc config set pull-secret-file ~/Downloads/pull-secret.txt
crc config set cpus 12
crc config set memory 32768
crc config set disk-size 80
```

Sizing takes effect only while CRC is stopped. The scripts check it and never change it. They
use the `crc-admin` kubeconfig context that `crc start` writes, so no password is needed. If you
want the web console login, run `crc console --credentials` yourself.

Verify:

```bash
minikube version
kubectl version --client
helm version --short
crc version
skopeo --version
```

---

## CLI tools

These are used by the `verify.sh` scripts and the "Drive it" sections in each
example README.

### curl, jq and git (required)

Used by every example to call APIs and format JSON output. Git is needed to clone the
repository.

```bash
sudo dnf install -y curl jq git
```

### python3

The `verify.sh` scripts use `python3` to parse JSON. Fedora and RHEL ship it. Example 16
also needs the `websockets` and `aiohttp` packages; its script installs pinned copies into a
cached virtual environment under `~/.cache/cndp-verify` when the host Python lacks them
(this needs `python3 -m venv` and network access on first run).

### conftest 0.71.1 (required for example 12)

Example 12 evaluates its Rego policies with conftest, and `verify.sh` fails without it.
Install the pinned release into `~/.local/bin`, checking the archive against the release's
`checksums.txt`:

```bash
CONFTEST_VERSION=0.71.1
BASE="https://github.com/open-policy-agent/conftest/releases/download/v${CONFTEST_VERSION}"
cd "$(mktemp -d)"
curl -fsSLO "${BASE}/conftest_${CONFTEST_VERSION}_Linux_x86_64.tar.gz"
curl -fsSLO "${BASE}/checksums.txt"
grep " conftest_${CONFTEST_VERSION}_Linux_x86_64.tar.gz\$" checksums.txt | sha256sum -c -
mkdir -p ~/.local/bin
tar -xzf "conftest_${CONFTEST_VERSION}_Linux_x86_64.tar.gz" -C ~/.local/bin conftest
conftest --version
```

`~/.local/bin` is on the default `PATH` for Fedora and RHEL login shells.

### kcat (Kafka inspection)

Lists topics and reads or produces Kafka messages from the host (example 04 uses it); it
replaces the removed kafka-ui. Optional, since `kafka-console-consumer.sh` inside the
`kafka` container does the same:

```bash
sudo dnf install -y kcat
```

### hey v0.1.5 (HTTP load testing)

Used by examples that demonstrate scaling or performance patterns. Download a binary from
the [hey releases](https://github.com/rakyll/hey/releases) page, or build it with Go:

```bash
go install github.com/rakyll/hey@v0.1.5
```

### ghz v0.121.0 (gRPC load testing)

Used by examples with gRPC endpoints. Download the pinned binary from the
[ghz releases](https://github.com/bojand/ghz/releases) page:

```bash
GHZ_VERSION=0.121.0
BASE="https://github.com/bojand/ghz/releases/download/v${GHZ_VERSION}"
cd "$(mktemp -d)"
curl -fsSLO "${BASE}/ghz-linux-x86_64.tar.gz"
curl -fsSLO "${BASE}/ghz-linux-x86_64.tar.gz.sha256"
echo "$(cat ghz-linux-x86_64.tar.gz.sha256)  ghz-linux-x86_64.tar.gz" | sha256sum -c -
mkdir -p ~/.local/bin
tar -xzf ghz-linux-x86_64.tar.gz -C ~/.local/bin ghz
ghz --version
```

### newman 6.2.3 (Postman CLI, required for example 28)

Used by example 28 (Newman API testing). Requires Node.js. Install into the user prefix
`~/.local` so no `sudo` is needed:

```bash
sudo dnf install -y nodejs npm
npm install -g --prefix ~/.local newman@6.2.3 newman-reporter-htmlextra@1.23.1
```

Verify:

```bash
curl --version
jq --version
kcat -V 2>&1 | head -1          # optional
hey -h 2>&1 | head -1          # optional
ghz --version                   # optional
newman --version                # required for example 28
conftest --version              # required for example 12
```

---

## Local toolchains (optional)

Install these only if you want to build or test a service on the host instead of in its
container.

| Language | Install |
|----------|---------|
| Java (Spring Boot, Quarkus) | [SDKMAN](https://sdkman.io/): `curl -s "https://get.sdkman.io" \| bash`, then `sdk install java 25-tem` and `sdk install maven`; optional Quarkus CLI: `sdk install quarkus 3.40.1` |
| Go 1.27.2 | Official tarball from [go.dev/dl](https://go.dev/dl/): `curl -fsSLO https://go.dev/dl/go1.27.2.linux-amd64.tar.gz && echo "ecbadb99091a3f46e31f5f934b068b1864eafa7995211b39eaddf76996045fe5  go1.27.2.linux-amd64.tar.gz" \| sha256sum -c - && sudo rm -rf /usr/local/go && sudo tar -C /usr/local -xzf go1.27.2.linux-amd64.tar.gz`, then add `/usr/local/go/bin` to `PATH`. Every `go.mod` requires 1.27.2; an older `go` downloads it on demand with `GOTOOLCHAIN=go1.27.2` |
| .NET | `sudo dnf install -y dotnet-sdk-10.0` (from the Fedora or RHEL repositories) |
| Python | `sudo dnf install -y python3.14` and [uv](https://docs.astral.sh/uv/): `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| C++ (C++23) | **Fedora 44:** `sudo dnf install -y gcc-c++ cmake ninja-build git make python3` (GCC 16.2, which supports C++23; Fedora has no `gcc-toolset-15`, and ninja-build 1.13.2 matches the pinned Ninja). Fedora's cmake is 4.3.0, which satisfies the examples' 3.31 minimum; the upstream CMake 4.4.4 binary is optional there and only matches the container toolchain exactly. **RHEL 10:** `sudo dnf install -y gcc-toolset-15 git make python3`, then `source /opt/rh/gcc-toolset-15/enable` (GCC 15.2). RHEL ships cmake 3.31 and ninja 1.11, so take CMake 4.4.4 and Ninja 1.13.2 from the upstream release binaries: `curl -fsSLO https://github.com/Kitware/CMake/releases/download/v4.4.4/cmake-4.4.4-linux-x86_64.tar.gz && echo "e5bb807f7728cb60cd8b27ebc97a2edb469b68655f21e844a600c3575b76f5bb  cmake-4.4.4-linux-x86_64.tar.gz" \| sha256sum -c - && sudo tar -C /opt -xzf cmake-4.4.4-linux-x86_64.tar.gz`, `curl -fsSLO https://github.com/ninja-build/ninja/releases/download/v1.13.2/ninja-linux.zip && echo "5749cbc4e668273514150a80e387a957f933c6ed3f5f11e03fb30955e2bbead6  ninja-linux.zip" \| sha256sum -c - && sudo unzip -d /opt/cmake-4.4.4-linux-x86_64/bin ninja-linux.zip`, then add `/opt/cmake-4.4.4-linux-x86_64/bin` to `PATH`. **Both:** Conan 2.33.0 in a venv: `python3 -m venv ~/.venvs/conan && ~/.venvs/conan/bin/pip install conan==2.33.0` (or `pipx install conan==2.33.0`) |

---

## Resource requirements

| Stack | Memory | Disk | CPU |
|-------|--------|------|-----|
| Docker compose examples | ~2-4 GB | ~3 GB for images | 2+ cores |
| Minikube, Example 05 (optional) | 8 GB for the node | 40 GB (profile disk) | 4+ cores |
| OpenShift Local, Example 05 (optional) | 32 GB for the VM (32768 MiB) | 80 GB (VM disk) | 12 vCPU |

The LGTM observability stack (Grafana, Loki, Tempo, Mimir) is the heaviest
shared component at ~1.5 GB.

### Host ports

The examples publish service ports on the host. Prometheus-compatible metrics (Mimir) are
on host port **19090**, because Cockpit holds 9090 on Fedora and RHEL. All other ports are
as listed in each example README.

---

## Quick setup check

Run this to verify everything is ready:

```bash
#!/usr/bin/env bash
printf "Container runtime:\n"
docker --version 2>/dev/null || echo "  MISSING"
printf "\nCompose:\n"
docker compose version 2>/dev/null || echo "  MISSING"
printf "\nDocker daemon:\n"
docker info >/dev/null 2>&1 && echo "  ok" || echo "  NOT RUNNING (or user not in the docker group)"
printf "\nCLI tools:\n"
for cmd in curl jq git python3 conftest newman; do
  printf "  %-10s %s\n" "$cmd" "$(command -v $cmd >/dev/null && echo 'ok' || echo 'MISSING')"
done
printf "\nOptional:\n"
for cmd in minikube kubectl helm crc skopeo hey ghz; do
  printf "  %-10s %s\n" "$cmd" "$(command -v $cmd >/dev/null && echo 'ok' || echo 'not installed')"
done
```

---

## What you do NOT need

All application code runs inside containers built from **Red Hat UBI** base
images. You do not need to install any of these locally to run the examples:

- Java / JDK
- Python
- Go
- .NET SDK
- C++ toolchain

The only local tools you need are Docker Engine and the CLI utilities listed in this guide.
