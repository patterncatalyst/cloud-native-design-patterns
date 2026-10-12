using Microsoft.EntityFrameworkCore;

public class Notification
{
    public long Id { get; set; }
    public string OrderId { get; set; } = "";
    public string Channel { get; set; } = "";
    public DateTime CreatedAt { get; set; }
}

/// <summary>Maps the shared notifications table (unique on order_id); the schema is owned by db/init, so there are no migrations.</summary>
public class NotificationsContext(DbContextOptions<NotificationsContext> options) : DbContext(options)
{
    public DbSet<Notification> Notifications => Set<Notification>();

    protected override void OnModelCreating(ModelBuilder modelBuilder) =>
        modelBuilder.Entity<Notification>(e =>
        {
            e.ToTable("notifications");
            e.Property(x => x.Id).HasColumnName("id");
            e.Property(x => x.OrderId).HasColumnName("order_id");
            e.Property(x => x.Channel).HasColumnName("channel");
            e.Property(x => x.CreatedAt).HasColumnName("created_at").HasDefaultValueSql("now()");
            e.HasIndex(x => x.OrderId).IsUnique();
        });
}
