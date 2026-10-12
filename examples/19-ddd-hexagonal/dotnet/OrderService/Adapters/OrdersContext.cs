using Microsoft.EntityFrameworkCore;
using OrderService.Domain;

namespace OrderService.Adapters;

/// <summary>
/// Persistence adapter mapping: the domain Order stays free of persistence attributes and the mapping lives here.
/// The schema is owned by db/init, so there are no migrations.
/// </summary>
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
            e.Property(o => o.CreatedAt).HasColumnName("created_at");
        });
}
