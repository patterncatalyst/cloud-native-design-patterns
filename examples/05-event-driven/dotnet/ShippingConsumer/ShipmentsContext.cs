using Microsoft.EntityFrameworkCore;

public class Shipment
{
    public long Id { get; set; }
    public string OrderId { get; set; } = "";
    public string Status { get; set; } = "";
    public DateTime CreatedAt { get; set; }
}

/// <summary>Maps the shared shipments table (unique on order_id); the schema is owned by db/init, so there are no migrations.</summary>
public class ShipmentsContext(DbContextOptions<ShipmentsContext> options) : DbContext(options)
{
    public DbSet<Shipment> Shipments => Set<Shipment>();

    protected override void OnModelCreating(ModelBuilder modelBuilder) =>
        modelBuilder.Entity<Shipment>(e =>
        {
            e.ToTable("shipments");
            e.Property(x => x.Id).HasColumnName("id");
            e.Property(x => x.OrderId).HasColumnName("order_id");
            e.Property(x => x.Status).HasColumnName("status");
            e.Property(x => x.CreatedAt).HasColumnName("created_at").HasDefaultValueSql("now()");
            e.HasIndex(x => x.OrderId).IsUnique();
        });
}
