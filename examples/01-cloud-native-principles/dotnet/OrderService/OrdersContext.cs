using Microsoft.EntityFrameworkCore;

public class Order
{
    public int Id { get; set; }
    public string Customer { get; set; } = "";
    public decimal Total { get; set; }
}

public record OrderDto(int Id, string Customer, decimal Total)
{
    public static OrderDto From(Order o) => new(o.Id, o.Customer, Scale2(o.Total));

    // The column is numeric(10,2), so a total always reads back with two decimals ("42.50", not "42.5").
    private static decimal Scale2(decimal value) => decimal.Round(value, 2, MidpointRounding.AwayFromZero) + 0.00m;
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
            e.Property(o => o.Customer).HasColumnName("customer");
            e.Property(o => o.Total).HasColumnName("total").HasPrecision(10, 2);
        });
}
