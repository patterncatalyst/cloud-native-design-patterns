using System.Collections.Concurrent;
using System.Net.WebSockets;
using System.Text;
using System.Text.Json;
using StackExchange.Redis;

var builder = WebApplication.CreateBuilder(args);
builder.WebHost.UseUrls("http://+:8080");
var app = builder.Build();

var podName = Environment.GetEnvironmentVariable("POD_NAME") ?? "ws-pod";
var redisUrl = Environment.GetEnvironmentVariable("REDIS_URL") ?? "redis://redis:6379";
var redisHost = redisUrl.Replace("redis://", "");

var clients = new ConcurrentDictionary<string, WebSocket>();
var seqCounters = new ConcurrentDictionary<string, int>();
var messageBuffers = new ConcurrentDictionary<string, List<JsonElement>>();
const int BufferSize = 100;

ConnectionMultiplexer? redis = null;
for (var i = 0; i < 10; i++)
{
    try { redis = ConnectionMultiplexer.Connect(redisHost); break; }
    catch { Thread.Sleep(2000); }
}

if (redis is not null)
{
    var sub = redis.GetSubscriber();
    _ = Task.Run(async () =>
    {
        var channel = await sub.SubscribeAsync(RedisChannel.Literal("ws:broadcast"));
        channel.OnMessage(async msg =>
        {
            try
            {
                using var doc = JsonDocument.Parse((string)msg.Message!);
                var root = doc.RootElement;
                var fromPod = root.GetProperty("pod").GetString();
                if (fromPod == podName) return;

                var data = root.GetProperty("data").GetString() ?? "";
                var hasTarget = root.TryGetProperty("target", out var targetProp)
                    && targetProp.ValueKind != JsonValueKind.Null;
                var target = hasTarget ? targetProp.GetString() : null;

                if (target is not null)
                {
                    if (clients.TryGetValue(target, out var ws) && ws.State == WebSocketState.Open)
                        await SendFrame(ws, target, data);
                }
                else
                {
                    foreach (var (cid, ws) in clients)
                    {
                        if (ws.State == WebSocketState.Open)
                            await SendFrame(ws, cid, data);
                    }
                }
            }
            catch { }
        });
    });
}

app.UseWebSockets();

app.MapGet("/healthz", () => new { status = "ok", pod = podName });

app.MapGet("/info", () => new { pod = podName, clients = clients.Keys.ToArray() });

app.MapPost("/send", async (HttpContext ctx) =>
{
    var target = ctx.Request.Query["target"].FirstOrDefault();
    var message = ctx.Request.Query["message"].FirstOrDefault() ?? "hello";

    var payload = JsonSerializer.Serialize(new { pod = podName, target = (object?)target, data = message });
    if (redis is not null)
    {
        try { await redis.GetSubscriber().PublishAsync(RedisChannel.Literal("ws:broadcast"), payload); }
        catch { }
    }

    if (target is not null)
    {
        if (clients.TryGetValue(target, out var ws) && ws.State == WebSocketState.Open)
            await SendFrame(ws, target, message);
    }
    else
    {
        foreach (var (cid, ws) in clients)
        {
            if (ws.State == WebSocketState.Open)
                await SendFrame(ws, cid, message);
        }
    }

    return Results.Json(new { sent = true, pod = podName });
});

app.Map("/ws/{clientId}", async (HttpContext ctx, string clientId) =>
{
    if (!ctx.WebSockets.IsWebSocketRequest)
    {
        ctx.Response.StatusCode = 400;
        return;
    }

    var ws = await ctx.WebSockets.AcceptWebSocketAsync();
    clients[clientId] = ws;
    seqCounters.TryAdd(clientId, 0);
    messageBuffers.TryAdd(clientId, new List<JsonElement>());

    var resumeSeqStr = ctx.Request.Query["resume_seq"].FirstOrDefault();
    if (int.TryParse(resumeSeqStr, out var resumeSeq))
    {
        var buf = messageBuffers.GetValueOrDefault(clientId);
        if (buf is not null)
        {
            List<JsonElement> toReplay;
            lock (buf) toReplay = buf.Where(m => m.GetProperty("seq").GetInt32() > resumeSeq).ToList();
            foreach (var m in toReplay)
                await SendRaw(ws, m.GetRawText());
        }
    }

    var buffer = new byte[4096];
    try
    {
        while (ws.State == WebSocketState.Open)
        {
            var result = await ws.ReceiveAsync(buffer, CancellationToken.None);
            if (result.MessageType == WebSocketMessageType.Close) break;

            var text = Encoding.UTF8.GetString(buffer, 0, result.Count);
            try
            {
                using var doc = JsonDocument.Parse(text);
                var msgType = doc.RootElement.TryGetProperty("type", out var tp) ? tp.GetString() : null;
                if (msgType == "ping")
                {
                    var pong = JsonSerializer.Serialize(new { type = "pong", pod = podName });
                    await SendRaw(ws, pong);
                }
            }
            catch { }
        }
    }
    catch { }
    finally
    {
        clients.TryRemove(clientId, out _);
        try { await ws.CloseAsync(WebSocketCloseStatus.NormalClosure, "", CancellationToken.None); } catch { }
    }
});

app.Run();

async Task SendFrame(WebSocket ws, string clientId, string data)
{
    var seq = seqCounters.AddOrUpdate(clientId, 1, (_, v) => v + 1);
    var frame = JsonSerializer.Serialize(new { seq, data });
    var frameDoc = JsonDocument.Parse(frame).RootElement.Clone();

    var buf = messageBuffers.GetOrAdd(clientId, _ => new List<JsonElement>());
    lock (buf)
    {
        buf.Add(frameDoc);
        if (buf.Count > BufferSize) buf.RemoveAt(0);
    }

    await SendRaw(ws, frame);
}

async Task SendRaw(WebSocket ws, string text)
{
    if (ws.State != WebSocketState.Open) return;
    var bytes = Encoding.UTF8.GetBytes(text);
    await ws.SendAsync(bytes, WebSocketMessageType.Text, true, CancellationToken.None);
}
