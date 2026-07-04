---
title: "Prerequisites & Setup"
description: "Install the tools you need to run the examples on Linux, macOS, or Windows."
marker: "⚙"
label: "Setup"
order: 0
---

Everything runs in containers — you do **not** need local JDK, Python, Go, or .NET
installations. You need a container runtime, a handful of CLI tools, and (for four
Kubernetes-based examples) a local cluster.

---

## Container runtime

Most examples use **Podman** with the Compose plugin. Docker works too — the
`compose.yaml` files are compatible with both.

### Podman (recommended)

| Platform | Install |
|----------|---------|
| **Fedora / RHEL / CentOS** | `sudo dnf install -y podman podman-compose` |
| **Ubuntu / Debian** | `sudo apt install -y podman && pip install podman-compose` |
| **macOS** | `brew install podman podman-compose && podman machine init && podman machine start` |
| **Windows** | Install [Podman Desktop](https://podman-desktop.io/) or `winget install RedHat.Podman` and [enable WSL 2](https://learn.microsoft.com/en-us/windows/wsl/install) |

### Docker (alternative)

| Platform | Install |
|----------|---------|
| **Linux** | Follow [docs.docker.com/engine/install](https://docs.docker.com/engine/install/) for your distro |
| **macOS** | `brew install --cask docker` (Docker Desktop) or [Colima](https://github.com/abiosoft/colima) |
| **Windows** | Install [Docker Desktop](https://www.docker.com/products/docker-desktop/) with WSL 2 backend |

Verify:

```bash
podman --version        # or docker --version
podman compose version  # or docker compose version
```

---

## Kubernetes tools (optional)

Four examples (09 API Registry, 12 Security, 22 L7 Routing, 24 Monolith to
Microservices) run on a local Kubernetes cluster. Skip these if you only plan to
run the Podman-based examples.

### minikube

| Platform | Install |
|----------|---------|
| **Linux** | `curl -LO https://storage.googleapis.com/minikube/releases/latest/minikube-linux-amd64 && sudo install minikube-linux-amd64 /usr/local/bin/minikube` |
| **macOS** | `brew install minikube` |
| **Windows** | `winget install Kubernetes.minikube` |

### kubectl

| Platform | Install |
|----------|---------|
| **Linux** | `curl -LO "https://dl.k8s.io/release/$(curl -sL https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl" && sudo install kubectl /usr/local/bin/kubectl` |
| **macOS** | `brew install kubectl` |
| **Windows** | `winget install Kubernetes.kubectl` |

### Helm

| Platform | Install |
|----------|---------|
| **Linux** | `curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 \| bash` |
| **macOS** | `brew install helm` |
| **Windows** | `winget install Helm.Helm` |

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

### curl and jq (required)

Used by every example to call APIs and format JSON output.

| Platform | Install |
|----------|---------|
| **Linux** | `sudo dnf install -y curl jq` (Fedora) or `sudo apt install -y curl jq` (Debian/Ubuntu) |
| **macOS** | Pre-installed; or `brew install curl jq` for latest |
| **Windows** | `winget install cURL.cURL stedolan.jq` (or use Git Bash which bundles curl) |

### hey (HTTP load testing)

Used by examples that demonstrate scaling or performance patterns.

| Platform | Install |
|----------|---------|
| **Linux / macOS** | `go install github.com/rakyll/hey@latest` (requires Go) or download a binary from [hey releases](https://github.com/rakyll/hey/releases) |
| **Windows** | Download from [hey releases](https://github.com/rakyll/hey/releases) |

### ghz (gRPC load testing)

Used by examples with gRPC endpoints.

| Platform | Install |
|----------|---------|
| **Linux / macOS** | `brew install ghz` or download from [ghz releases](https://github.com/bojand/ghz/releases) |
| **Windows** | Download from [ghz releases](https://github.com/bojand/ghz/releases) |

### newman (Postman CLI)

Used by example 28 (Newman API testing).

| Platform | Install |
|----------|---------|
| **All platforms** | `npm install -g newman newman-reporter-htmlextra` (requires Node.js) |

Verify:

```bash
curl --version
jq --version
hey -h 2>&1 | head -1          # optional
ghz --version                   # optional
newman --version                # optional
```

---

## Git

Required to clone the repository.

| Platform | Install |
|----------|---------|
| **Linux** | `sudo dnf install -y git` or `sudo apt install -y git` |
| **macOS** | Pre-installed via Xcode CLT; or `brew install git` |
| **Windows** | `winget install Git.Git` |

---

## Resource requirements

| Stack | Memory | Disk | CPU |
|-------|--------|------|-----|
| Podman examples (most) | ~2-4 GB | ~3 GB for images | 2+ cores |
| Minikube examples | ~6-8 GB | ~10 GB | 4+ cores |

The LGTM observability stack (Grafana, Loki, Tempo, Mimir) is the heaviest
shared component at ~1.5 GB.

---

## Quick setup check

Run this to verify everything is ready:

```bash
#!/usr/bin/env bash
printf "Container runtime:\n"
podman --version 2>/dev/null || docker --version 2>/dev/null || echo "  MISSING"
printf "\nCompose:\n"
podman compose version 2>/dev/null || docker compose version 2>/dev/null || echo "  MISSING"
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
images. You do **not** need to install any of these locally:

- Java / JDK (containers use `ubi9/openjdk-21`)
- Python (containers use `ubi9/python-312`)
- Go (multi-stage build with `ubi9/ubi-minimal` runtime)
- .NET SDK
- C++ toolchain

The only local tools you need are the container runtime and CLI utilities listed
in this guide.
