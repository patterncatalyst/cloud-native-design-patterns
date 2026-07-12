---
title: ".NET on Linux: Runtime, Kestrel, and Containers"
marker: "P"
label: "Appendix P"
order: 29
part: "Deep-dive appendices"
description: ".NET-specific primer: what C# compiles to, how the CoreCLR runtime works on Linux, what Kestrel does instead of IIS, and how multi-stage container builds produce minimal production images."
duration: 15 minutes
---

> **This appendix is .NET-specific.** It exists for developers who know C# but have
> only ever run it on Windows with Visual Studio. Every other chapter is
> multi-language — this one answers the questions that come up when the deployment
> target changes from IIS on Windows Server to a container on Linux.

The move from Windows to Linux changes _where_ .NET runs, not _what_ it is. The same
language, the same compiler, the same runtime, the same NuGet packages. What disappears
is the Windows-only substrate: IIS, the Windows registry, COM interop, Windows
Services. What replaces them is the same thing that replaced them for Java and Python
years ago — a container runtime, a process supervisor (Kubernetes), and a
standards-based web server (Kestrel).

This appendix walks through four layers, from source code to running container:

1. **C# and .NET** — the language vs. the platform, and why the distinction matters.
2. **CIL and the CoreCLR runtime** — what `dotnet build` produces and how it executes.
3. **Kestrel** — the web server built into ASP.NET Core.
4. **Containers** — multi-stage builds, Red Hat UBI images, and what ships to production.

## C# is a language. .NET is a platform.

The distinction matters because conflating them causes architectural confusion. **C#** is
a statically-typed, garbage-collected language — one of several that target .NET. F# and
VB.NET are the others. All three compile to the same intermediate representation and run
on the same runtime.

**.NET** (since .NET 5, unified; previously split into .NET Framework, .NET Core, and
Mono) is the platform: a runtime (CoreCLR), a base class library (BCL — `System.*`,
`Microsoft.Extensions.*`), a compiler toolchain (Roslyn for C#, the F# compiler), a
package manager (NuGet), and a CLI (`dotnet`). The platform is cross-platform — the
same `dotnet publish` output runs on Linux x86-64, Linux ARM64, macOS, and Windows
without recompilation, because the output is not native machine code.

The practical consequence: when this book says ".NET 10," it means the platform — the
runtime, the BCL, and the ASP.NET Core framework that sits on top. When it says "C#," it
means the language syntax. A `.csproj` file targets a .NET version (`net10.0`), not a C#
version, because the platform version determines what APIs are available.

## CIL: what `dotnet build` actually produces

When Roslyn compiles a C# source file, the output is not x86 machine code. It is
**Common Intermediate Language** (CIL, historically called MSIL or just IL) — a
CPU-agnostic bytecode stored in `.dll` files. A `.dll` built on macOS runs unmodified on
Linux because the bytes inside are CIL, not native instructions.

{% include excalidraw.html
   file="29-dotnet-compilation"
   alt="The .NET compilation pipeline. C# source is compiled by Roslyn into CIL bytecode stored in DLL files. At runtime, CoreCLR loads the CIL and RyuJIT compiles it method-at-a-time into native x86-64 code. NativeAOT is an alternative that compiles ahead of time."
   caption="Figure P.1 — From C# source to native code: Roslyn emits CIL bytecode, RyuJIT compiles to native at runtime" %}

The runtime — **CoreCLR** — loads these CIL assemblies and compiles them to native code
on the fly using **RyuJIT**, the just-in-time compiler. RyuJIT compiles one method at a
time, the first time it is called. After that first call, the method runs at native
speed — there is no interpreter step and no re-compilation on subsequent calls.

CoreCLR on Linux is `libcoreclr.so`, a shared library. It provides:

- **JIT compilation** (RyuJIT) — CIL to native x86-64 or ARM64.
- **Garbage collection** — a generational, concurrent GC that runs on its own threads.
  Server GC mode (the default in ASP.NET Core) allocates one heap per CPU core.
- **Type system** — reflection, generics, interface dispatch.
- **Threading** — maps .NET threads to pthreads; `Task` and `async/await` run on the
  thread pool.
- **Exception handling** — uses platform-specific unwinding (libunwind on Linux).
- **P/Invoke** — call native C libraries directly (`libpq`, `librdkafka`, `openssl`).

### NativeAOT: the ahead-of-time alternative

.NET also offers **NativeAOT** compilation, which runs Roslyn and the AOT compiler at
build time to produce a single native binary — no JIT, no `libcoreclr.so`, no `.dll`
files at runtime. The trade-off is real: NativeAOT binaries start faster and use less
memory, but they cannot use runtime code generation (no `Reflection.Emit`, limited
reflection). For the examples in this book, the JIT path is the default because it
supports the full library ecosystem without restrictions.

### What the runtime is _not_

CoreCLR is not a virtual machine in the JVM sense. There is no bytecode interpreter
running continuously — CIL is compiled to native code before it executes. After JIT
compilation, a .NET method is indistinguishable from a method compiled by GCC or Clang.
The runtime is still present (for GC, exception handling, and type loading), but the
hot path is native machine code.

## Kestrel: the web server that replaced IIS

On Windows, .NET web applications historically ran inside IIS (Internet Information
Services). IIS managed the process lifecycle, handled TLS, parsed HTTP, and forwarded
requests to the .NET application via a proprietary hosting model.

On Linux (and on modern Windows), **Kestrel** replaces all of that. Kestrel is the web
server built into ASP.NET Core — it is not a separate process, not a reverse proxy, and
not optional. When a .NET web application starts, Kestrel binds to a port and handles
HTTP directly.

{% include excalidraw.html
   file="29-kestrel-pipeline"
   alt="Kestrel request processing pipeline. Kestrel handles TLS via OpenSSL, parses HTTP using Span-based parsers, passes requests through the ASP.NET Core middleware pipeline (routing, auth, CORS, diagnostics), and dispatches to application endpoints (minimal APIs, gRPC, GraphQL, WebSockets, health checks)."
   caption="Figure P.2 — Kestrel processes requests end to end: TLS, HTTP parsing, middleware, endpoint dispatch" %}

Key things Kestrel does:

- **Listens on TCP sockets** — using `epoll` on Linux (or `io_uring` on newer kernels).
  No external web server needed.
- **Handles TLS** — via OpenSSL on Linux. In Kubernetes, TLS is typically terminated by
  the service mesh (Istio) or ingress controller, so Kestrel often runs plain HTTP
  inside the Pod.
- **Parses HTTP/1.1, HTTP/2, and HTTP/3** — using zero-allocation `Span<byte>` parsers.
  gRPC requires HTTP/2, which Kestrel supports natively.
- **Runs the middleware pipeline** — each request passes through a configurable chain:
  routing, authentication, CORS, diagnostics, exception handling.
- **Dispatches to endpoints** — minimal APIs, gRPC services, GraphQL servers,
  WebSocket handlers, and health check endpoints all share the same Kestrel host.

### Why not nginx or Apache in front?

In production Kubernetes, the answer is usually: you do not need them. The service mesh
handles TLS termination, load balancing, and retries. Kestrel handles everything else.
Adding nginx as a sidecar adds latency, memory, and operational complexity for features
Kestrel already provides. The one exception is when you need nginx-specific features
like rate limiting at the edge — in that case, it sits in front as an ingress controller,
not as a per-Pod sidecar.

### Kestrel configuration in practice

Every .NET example in this book configures Kestrel the same way:

```csharp
var builder = WebApplication.CreateBuilder(args);
builder.WebHost.UseUrls("http://+:8080");
```

For gRPC services that need HTTP/2-only:

```csharp
builder.WebHost.ConfigureKestrel(k =>
    k.ListenAnyIP(50051, o => o.Protocols = HttpProtocols.Http2));
```

The `+` binds to all interfaces (0.0.0.0). Port 8080 is the convention for non-root
containers — ports below 1024 require root, which containers should not run as.

## Containers: what ships to production

A .NET application in a container is a Linux process. There is no VM, no app pool, no
IIS — just `dotnet YourApp.dll` running as PID 1 (or behind a container init process
like `tini`). The container image must contain the .NET runtime and your application's
published DLLs; it does not need the SDK, Roslyn, NuGet, or MSBuild.

{% include excalidraw.html
   file="29-container-layers"
   alt="Multi-stage container build. The build stage uses the UBI9 .NET 10 SDK image to restore NuGet packages and compile the application. Only the published output is copied to the runtime stage, which uses the smaller UBI9 ASP.NET runtime image. The SDK never ships."
   caption="Figure P.3 — Multi-stage build: the SDK compiles, only the runtime and app DLLs ship" %}

### Multi-stage Dockerfiles

Every example in this book uses a two-stage Dockerfile:

```dockerfile
FROM registry.access.redhat.com/ubi9/dotnet-100 AS build
USER root
WORKDIR /src
COPY OrderService/OrderService.csproj OrderService/
RUN dotnet restore OrderService/OrderService.csproj
COPY OrderService/ OrderService/
RUN dotnet publish OrderService/OrderService.csproj -c Release -o /app

FROM registry.access.redhat.com/ubi9/dotnet-100-aspnet
WORKDIR /app
COPY --from=build /app .
EXPOSE 8080
ENTRYPOINT ["dotnet", "OrderService.dll"]
```

**Stage 1 (build)** uses the SDK image (`ubi9/dotnet-100`, ~780 MB). It restores
NuGet packages first (this layer is cached if the `.csproj` has not changed), then copies
source and publishes. `USER root` is required because the UBI SDK image runs as a
non-root user by default, but `dotnet restore` needs write access to the NuGet cache.

**Stage 2 (runtime)** uses the ASP.NET runtime image (`ubi9/dotnet-100-aspnet`,
~170 MB). It copies only the published output from stage 1. The SDK, NuGet cache, source
code, and intermediate build artifacts are all discarded. The final image is typically
~200 MB.

### Why Red Hat UBI?

The examples use **Red Hat Universal Base Images** (UBI) instead of the
`mcr.microsoft.com/dotnet/*` images from Microsoft. UBI images are:

- **Freely redistributable** — no subscription required to pull, run, or ship them.
- **Based on RHEL 9** — same packages, same security patches, same lifecycle.
- **Supported by Red Hat** — when running on OpenShift or RHEL, UBI images get full
  commercial support.
- **Minimal by default** — `ubi9-minimal` variants use microdnf instead of yum,
  producing smaller images.

The .NET UBI images (`ubi9/dotnet-100` for SDK, `ubi9/dotnet-100-aspnet` for runtime)
are built by Red Hat and published to `registry.access.redhat.com`. They contain the
same .NET runtime bits as Microsoft's images — the difference is the base OS layer.

### What is inside the final image

Layer by layer, from bottom to top:

1. **UBI9 base** (~70 MB) — glibc, openssl, ca-certificates, tzdata, libicu.
2. **ASP.NET Core runtime** (~100 MB) — `libcoreclr.so`, `libclrjit.so`, the BCL
   assemblies (`System.*.dll`), and the ASP.NET Core shared framework.
3. **Your application** (~5–80 MB) — your compiled `.dll` files, third-party NuGet
   package DLLs, appsettings.json.

Things that are _not_ in the final image: the SDK, MSBuild, Roslyn, NuGet, your source
code, `obj/` and `bin/` intermediates, test projects.

### Container runtime behavior

When Kubernetes starts the container, `dotnet OrderService.dll` runs:

1. CoreCLR initializes — loads `libcoreclr.so`, starts the GC, initializes the thread
   pool.
2. The host builder runs — registers services (DI), configures logging, sets up
   OpenTelemetry.
3. Kestrel binds to port 8080 — begins accepting HTTP connections.
4. The application is ready — Kubernetes starts sending liveness and readiness probes.
5. On shutdown, Kubernetes sends **SIGTERM** — the .NET host catches it and begins
   graceful shutdown: stops accepting new requests, drains in-flight requests, flushes
   telemetry, disposes services.

The entire lifecycle is the same as any Linux process. There is no IIS app pool recycle,
no w3wp.exe, no application domain. The container _is_ the process boundary.

### Cross-check it yourself

Verify the compilation pipeline by inspecting a published application's output. Run
`dotnet publish -c Release` on any example and list the output directory — you will see
`.dll` files (CIL bytecode, not native code), a `.deps.json` (dependency graph), and a
`.runtimeconfig.json` (runtime version selector). Open one of the `.dll` files with
`dotnet-ildasm` or `ILSpy` and you will see CIL opcodes, not x86 instructions — proof
that the JIT does its work at runtime, not at build time.

Then build a container image and inspect its layers. Run
`podman inspect <image> | jq '.[0].RootFS.Layers | length'` — you should see the UBI
base layer, the runtime layer, and your application layer. Compare the image size to the
SDK image: the runtime image should be roughly 4x smaller.

---
*Verification status: unverified — the three diagrams (P.1 compilation pipeline, P.2
Kestrel pipeline, P.3 container layers) are structurally correct based on the .NET 10
architecture, and the Dockerfile pattern matches the verified examples in this book. The
UBI image sizes (~780 MB SDK, ~170 MB runtime) are approximate and will vary by .NET
version. The NativeAOT section describes general availability behavior as of .NET 8+.*
