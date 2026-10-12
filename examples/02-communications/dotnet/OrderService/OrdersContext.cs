using Microsoft.EntityFrameworkCore;

public class Order
{
    public string Id { get; set; } = "";
    public string Sku { get; set; } = "";
    public int Quantity { get; set; }
    public string Status { get; set; } = "";
}

public record OrderDto(string Id, string Sku, int Quantity, string Status)
{
    public static OrderDto From(Order o) => new(o.Id, o.Sku, o.Quantity, o.Status);
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
            e.Property(o => o.Sku).HasColumnName("sku");
            e.Property(o => o.Quantity).HasColumnName("quantity");
            e.Property(o => o.Status).HasColumnName("status");
        });
}
