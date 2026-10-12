using Microsoft.EntityFrameworkCore;

public class Order
{
    public string Id { get; set; } = "";
    public string MerchantId { get; set; } = "";
    public string Sku { get; set; } = "";
    public int Quantity { get; set; }
    public decimal Total { get; set; }
    public string Status { get; set; } = "";
    public DateTime CreatedAt { get; set; }
}

public record OrderRequest(string MerchantId, string Sku, int Quantity, double Total);

/// <summary>The POST response and the order.placed event: the total is echoed as the client sent it.</summary>
public record OrderPlaced(string Id, string MerchantId, string Sku, int Quantity, double Total, string Status);

public record OrderDto(string Id, string MerchantId, string Sku, int Quantity, decimal Total, string Status)
{
    public static OrderDto From(Order o) => new(o.Id, o.MerchantId, o.Sku, o.Quantity, o.Total, o.Status);
}

/// <summary>Maps the shared orders table; the schema is owned by db/init, so there are no migrations.</summary>
public class OrdersContext(DbContextOptions<OrdersContext> options) : DbContext(options)
{
    public DbSet<Order> Orders => Set<Order>();

    protected override void OnModelCreating(ModelBuilder modelBuilder) =>
        modelBuilder.Entity<Order>(e =>
        {
            e.ToTable("orders");
            e.Property(o => o.Id).HasColumnName("id");
            e.Property(o => o.MerchantId).HasColumnName("merchant_id");
            e.Property(o => o.Sku).HasColumnName("sku");
            e.Property(o => o.Quantity).HasColumnName("quantity");
            e.Property(o => o.Total).HasColumnName("total").HasPrecision(12, 2);
            e.Property(o => o.Status).HasColumnName("status");
            e.Property(o => o.CreatedAt).HasColumnName("created_at").HasDefaultValueSql("now()");
        });
}
