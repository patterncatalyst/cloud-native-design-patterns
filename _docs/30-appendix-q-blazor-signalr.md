---
title: "Blazor Server + SignalR"
marker: "Q"
label: "Appendix Q"
order: 30
part: "Deep-dive appendices"
description: "Real-time server-rendered UI with Blazor Server over a SignalR circuit — how the persistent connection works, the Redis backplane for scale-out, and when to choose SignalR over raw WebSockets."
duration: 22 minutes
---

Everything in **Appendix C** used raw WebSockets — manual binary frames, hand-built
backplanes, explicit sequence tracking. That is the right choice for a polyglot
system. But when the entire stack is .NET, **SignalR** abstracts all of that away,
and **Blazor Server** builds a full server-rendered UI on top of it. This appendix
covers both — what they are, how they scale, and when to reach for them instead of
raw sockets.

## What Blazor Server is

Blazor Server is a server-rendered component model where the browser runs a thin
JavaScript runtime (the SignalR client) and all C# logic stays server-side. The
browser and the server maintain a **persistent SignalR circuit** — a single
WebSocket per connected client — and the server sends DOM diffs over that circuit
whenever the UI changes. The browser applies the diff; the user sees a live,
interactive page without downloading a heavy client-side framework.

{% include excalidraw.html
   file="30-blazor-circuit"
   alt="A browser running the Blazor JS runtime connects to the ASP.NET Core server via a SignalR circuit (WebSocket). The server holds the component tree, handles events (button click, form submit), re-renders the affected components, computes the DOM diff, and sends it over the circuit. The browser applies the diff. All C# logic stays server-side."
   caption="Figure Q.1 — Blazor Server: a persistent SignalR circuit carries DOM diffs, events flow up, diffs flow down" %}

The trade-off is latency: every click is a round-trip to the server, so users on
high-latency connections notice a delay. For internal dashboards, admin panels, and
tools where the server is close, this is invisible. For consumer-facing apps on
mobile networks, consider Blazor WebAssembly (runs in the browser) or a traditional
SPA instead.

## SignalR under the hood

SignalR is ASP.NET Core's real-time abstraction. At its core it is a **Hub** — a
class with methods the client can call, and methods the server can push to connected
clients. The transport is a WebSocket by default, with automatic fallback to
Server-Sent Events or long polling when WebSockets aren't available.

```csharp
// OrderHub.cs — a SignalR hub that pushes order events to connected clients
public class OrderHub : Hub
{
    public async Task JoinTenantGroup(string tenantId)
    {
        await Groups.AddToGroupAsync(Context.ConnectionId, tenantId);
    }

    public async Task BroadcastOrder(OrderDto order)
    {
        await Clients.Group(order.TenantId).SendAsync("OrderPlaced", order);
    }
}
```

Three features distinguish SignalR from raw WebSockets:

- **Strongly typed methods** — the server calls `Clients.All.SendAsync("OrderPlaced", order)`
  and the client receives a typed callback, not a raw byte buffer. No manual
  serialization, no type discriminators, no `switch` on message type.
- **Connection groups** — `Groups.AddToGroupAsync` replaces the per-pod registry
  and backplane fan-out from Appendix C. One API call adds a client to a logical
  group; SignalR handles the routing.
- **Automatic reconnection** — the client SDK reconnects with configurable backoff
  and restores group memberships automatically.

## Scaling: the same problem, a built-in solution

Blazor Server and SignalR face the same per-pod pinning problem as raw WebSockets
(Appendix C, Figure C.1): each SignalR circuit is pinned to the pod that accepted
it, scale-up leaves new pods idle, and scale-down drops active circuits.

{% include excalidraw.html
   file="30-signalr-backplane"
   alt="Three Blazor Server pods behind a Kubernetes Service / load balancer, each holding its own set of SignalR circuits. All three subscribe and publish to a shared Redis backplane (StackExchange.Redis). A message sent to a group on pod-1 is published to Redis; Redis delivers it to pod-2 and pod-3, which push it to their local circuits in that group."
   caption="Figure Q.2 — SignalR's Redis backplane: the same pub/sub externalisation as Appendix C, built into the framework" %}

The solution is the same — a shared backplane — but SignalR builds it in:

```csharp
// Program.cs — wire the Redis backplane for multi-pod scale-out
builder.Services.AddSignalR()
    .AddStackExchangeRedis(builder.Configuration.GetConnectionString("Redis")!,
        options => options.Configuration.ChannelPrefix =
            RedisChannel.Literal("cndp-signalr"));
```

One line replaces the manual Redis pub/sub subscription, the per-topic fan-out,
and the per-pod connection registry from Appendix C. Under the hood, SignalR
publishes group messages to Redis channels and each pod's subscriber delivers
them to the local circuits. The `ChannelPrefix` isolates this app's traffic from
other SignalR apps sharing the same Redis instance.

For teams that want fully managed infrastructure, **Azure SignalR Service** offloads
the persistent connections entirely: the app server handles Hub logic but the
connections terminate at Azure, removing the per-pod connection limit from your
scaling equation.

## A Blazor Server order dashboard

Here is a minimal but complete example: a Blazor Server page that shows orders in
real time. When a new order is placed via the REST API, the hub pushes it to every
connected dashboard.

```csharp
// Pages/Dashboard.razor — live-updating order list via SignalR
@page "/dashboard"
@inject NavigationManager Nav
@implements IAsyncDisposable

<h3>Live Orders</h3>
<table class="table">
    <thead><tr><th>ID</th><th>SKU</th><th>Qty</th><th>Status</th></tr></thead>
    <tbody>
        @foreach (var o in orders)
        {
            <tr><td>@o.Id</td><td>@o.Sku</td><td>@o.Quantity</td><td>@o.Status</td></tr>
        }
    </tbody>
</table>

@code {
    private HubConnection? hub;
    private readonly List<OrderDto> orders = [];

    protected override async Task OnInitializedAsync()
    {
        hub = new HubConnectionBuilder()
            .WithUrl(Nav.ToAbsoluteUri("/hubs/orders"))
            .WithAutomaticReconnect()
            .Build();

        hub.On<OrderDto>("OrderPlaced", order =>
        {
            orders.Insert(0, order);
            InvokeAsync(StateHasChanged);
        });

        await hub.StartAsync();
    }

    public async ValueTask DisposeAsync()
    {
        if (hub is not null) await hub.DisposeAsync();
    }
}
```

The component subscribes to the hub on mount, inserts each new order at the top of
the list, and calls `StateHasChanged` to trigger a re-render — which sends a DOM
diff (one new `<tr>`) over the circuit. No polling, no manual WebSocket code, no
binary framing.

## When to choose what

| Criterion | Raw WebSockets (Appendix C) | SignalR | Blazor Server |
|---|---|---|---|
| **Languages** | Any (cross-language) | .NET server, JS/C#/.NET client | .NET only |
| **Wire format** | Binary protobuf (you own it) | MessagePack or JSON (SignalR owns it) | DOM diffs (Blazor owns it) |
| **Backplane** | Hand-built (Redis pub/sub, Kafka) | Built-in (`AddStackExchangeRedis`) | Inherits from SignalR |
| **Reconnection** | Hand-built (backoff + seq resume) | Built-in (`WithAutomaticReconnect`) | Built-in (circuit recovery) |
| **Latency** | Minimal (raw frames) | Low (hub invocation overhead) | Round-trip per interaction |
| **Use case** | Polyglot, low-latency, custom protocols | .NET real-time APIs, chat, notifications | Internal dashboards, admin panels |

The rule of thumb: **raw WebSockets** when you need cross-language support or control
over the wire format. **SignalR** when the server is .NET and you want connection
management handled for you. **Blazor Server** when you also want the UI rendered
server-side, avoiding a separate frontend framework entirely.

### Cross-check it yourself

Run the Blazor Server example, open the dashboard in two browser tabs, and place an
order via `curl`. Both tabs should update simultaneously — confirming the SignalR hub
push and the Redis backplane fan-out. Then stop and restart one of the Blazor Server
pods and confirm the circuit reconnects automatically without losing the dashboard
state.

The code is in [`examples/30-blazor-signalr/`](https://github.com/patterncatalyst/cloud-native-design-patterns/tree/main/examples/30-blazor-signalr/). The run script there builds and
runs it; its `README.md` covers what it does and how to drive it.

---
*Verification status: unverified — runnable example at `examples/30-blazor-signalr/`
demonstrates SignalR hub push, Redis backplane scale-out, and Blazor Server circuit
recovery.*
