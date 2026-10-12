using System.Text.Json;
using Microsoft.EntityFrameworkCore;

public class Order
{
    public string Id { get; set; } = "";
    public string Sku { get; set; } = "";
    public int Quantity { get; set; }
    public string Status { get; set; } = "";
    public DateTime CreatedAt { get; set; }
}

public class OutboxEvent
{
    public long Id { get; set; }
    public string AggregateId { get; set; } = "";
    public string EventType { get; set; } = "";
    public JsonElement Payload { get; set; }
    public DateTime CreatedAt { get; set; }
}

public record OrderRequest(string Sku, int Quantity);

public record OrderDto(string Id, string Sku, int Quantity, string Status)
{
    public static OrderDto From(Order o) => new(o.Id, o.Sku, o.Quantity, o.Status);
}

public record OutboxDto(long Id, string AggregateId, string EventType, JsonElement Payload, string CreatedAt)
{
    public static OutboxDto From(OutboxEvent e) => new(e.Id, e.AggregateId, e.EventType, e.Payload, e.CreatedAt.ToString("o"));
}

/// <summary>Maps the shared tables; the schema is owned by db/init, so there are no migrations.</summary>
public class OrdersContext(DbContextOptions<OrdersContext> options) : DbContext(options)
{
    public DbSet<Order> Orders => Set<Order>();
    public DbSet<OutboxEvent> Outbox => Set<OutboxEvent>();

    protected override void OnModelCreating(ModelBuilder modelBuilder)
    {
        modelBuilder.Entity<Order>(e =>
        {
            e.ToTable("orders");
            e.Property(o => o.Id).HasColumnName("id");
            e.Property(o => o.Sku).HasColumnName("sku");
            e.Property(o => o.Quantity).HasColumnName("quantity");
            e.Property(o => o.Status).HasColumnName("status");
            e.Property(o => o.CreatedAt).HasColumnName("created_at").HasDefaultValueSql("now()");
        });

        modelBuilder.Entity<OutboxEvent>(e =>
        {
            e.ToTable("outbox");
            e.Property(o => o.Id).HasColumnName("id");
            e.Property(o => o.AggregateId).HasColumnName("aggregate_id");
            e.Property(o => o.EventType).HasColumnName("event_type");
            e.Property(o => o.Payload).HasColumnName("payload").HasColumnType("jsonb");
            e.Property(o => o.CreatedAt).HasColumnName("created_at").HasDefaultValueSql("now()");
        });
    }
}
