using System.Text.Json;
using Microsoft.EntityFrameworkCore;

public class Product
{
    public string Id { get; set; } = "";
    public string Name { get; set; } = "";
    public int PriceCents { get; set; }
}

public class EventRecord
{
    public string Id { get; set; } = "";
    public string Type { get; set; } = "";
    public JsonElement Payload { get; set; }
    public DateTime Ts { get; set; }
}

public class MetricRow
{
    public string Id { get; set; } = "";
    public JsonElement Payload { get; set; }
    public DateTime Ts { get; set; }
}

public record ProductDto(string Id, string Name, int PriceCents)
{
    public static ProductDto From(Product p) => new(p.Id, p.Name, p.PriceCents);
}

public record EventDto(string Id, string Type, JsonElement Payload)
{
    public static EventDto From(EventRecord e) => new(e.Id, e.Type, e.Payload);
}

public record ProductUpdate(string Name, int PriceCents);
public record EventRequest(string Id, string Type, JsonElement? Payload);
public record MetricRequest(double Value, JsonElement? Tags);

/// <summary>Maps the shared products, events and metrics tables; the schema is owned by db/init, so there are no migrations.</summary>
public class CacheContext(DbContextOptions<CacheContext> options) : DbContext(options)
{
    public DbSet<Product> Products => Set<Product>();
    public DbSet<EventRecord> Events => Set<EventRecord>();
    public DbSet<MetricRow> Metrics => Set<MetricRow>();

    protected override void OnModelCreating(ModelBuilder modelBuilder)
    {
        modelBuilder.Entity<Product>(e =>
        {
            e.ToTable("products");
            e.Property(p => p.Id).HasColumnName("id");
            e.Property(p => p.Name).HasColumnName("name");
            e.Property(p => p.PriceCents).HasColumnName("price_cents");
        });

        modelBuilder.Entity<EventRecord>(e =>
        {
            e.ToTable("events");
            e.Property(x => x.Id).HasColumnName("id");
            e.Property(x => x.Type).HasColumnName("type");
            e.Property(x => x.Payload).HasColumnName("payload").HasColumnType("jsonb");
            e.Property(x => x.Ts).HasColumnName("ts").HasDefaultValueSql("NOW()");
        });

        modelBuilder.Entity<MetricRow>(e =>
        {
            e.ToTable("metrics");
            e.Property(x => x.Id).HasColumnName("id");
            e.Property(x => x.Payload).HasColumnName("payload").HasColumnType("jsonb");
            e.Property(x => x.Ts).HasColumnName("ts").HasDefaultValueSql("NOW()");
        });
    }

    /// <summary>Insert-or-update of one metric; ExecuteSql keeps the ON CONFLICT upsert as a single statement.</summary>
    public Task<int> UpsertMetricAsync(string id, string payloadJson, CancellationToken ct = default) =>
        Database.ExecuteSqlAsync(
            $"""
            INSERT INTO metrics (id, payload) VALUES ({id}, {payloadJson}::jsonb)
            ON CONFLICT (id) DO UPDATE SET payload = {payloadJson}::jsonb, ts = NOW()
            """, ct);
}
