---
title: "Prerequisites & Setup"
description: "Install the tools you need to run the examples on Fedora or RHEL."
marker: "⚙"
label: "Setup"
order: 0
---

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

```bash
sudo dnf install -y dnf-plugins-core
sudo dnf config-manager addrepo --from-repofile=https://download.docker.com/linux/fedora/docker-ce.repo
sudo dnf install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```

### RHEL

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

The examples run on `docker compose` and need no cluster. A later part of the tutorial adds
optional minikube and OpenShift Local paths; install these tools only when you reach them.

### minikube

```bash
curl -LO https://storage.googleapis.com/minikube/releases/latest/minikube-linux-amd64
sudo install minikube-linux-amd64 /usr/local/bin/minikube
```

### kubectl

```bash
curl -LO "https://dl.k8s.io/release/$(curl -sL https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
sudo install kubectl /usr/local/bin/kubectl
```

### Helm

```bash
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash
```

Verify:

```bash
minikube version
kubectl version --client
helm version --short
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

### hey (HTTP load testing)

Used by examples that demonstrate scaling or performance patterns. Download a binary from
the [hey releases](https://github.com/rakyll/hey/releases) page, or build it with Go:

```bash
go install github.com/rakyll/hey@latest
```

### ghz (gRPC load testing)

Used by examples with gRPC endpoints. Download a binary from the
[ghz releases](https://github.com/bojand/ghz/releases) page.

### newman (Postman CLI)

Used by example 28 (Newman API testing). Requires Node.js.

```bash
sudo dnf install -y nodejs npm
sudo npm install -g newman newman-reporter-htmlextra
```

Verify:

```bash
curl --version
jq --version
hey -h 2>&1 | head -1          # optional
ghz --version                   # optional
newman --version                # optional
```

---

## Local toolchains (optional)

Install these only if you want to build or test a service on the host instead of in its
container.

| Language | Install |
|----------|---------|
| Java (Spring Boot, Quarkus) | [SDKMAN](https://sdkman.io/): `curl -s "https://get.sdkman.io" \| bash`, then `sdk install java 25-tem` and `sdk install maven` |
| Go | Download the Linux tarball from [go.dev/dl](https://go.dev/dl/), then `sudo rm -rf /usr/local/go && sudo tar -C /usr/local -xzf go<version>.linux-amd64.tar.gz` and add `/usr/local/go/bin` to `PATH` |
| .NET | `sudo dnf install -y dotnet-sdk-10.0` (from the Fedora or RHEL repositories) |
| Python | `sudo dnf install -y python3.14` and [uv](https://docs.astral.sh/uv/): `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| C++ | `sudo dnf install -y gcc-c++ cmake ninja-build` and `pip install conan` |

---

## Resource requirements

| Stack | Memory | Disk | CPU |
|-------|--------|------|-----|
| Docker compose examples | ~2-4 GB | ~3 GB for images | 2+ cores |
| Minikube (optional) | ~6-8 GB | ~10 GB | 4+ cores |

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
for cmd in curl jq git; do
  printf "  %-10s %s\n" "$cmd" "$(command -v $cmd >/dev/null && echo 'ok' || echo 'MISSING')"
done
printf "\nOptional:\n"
for cmd in minikube kubectl helm hey ghz newman; do
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
