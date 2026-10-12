using System.Text.Json.Nodes;
using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.ChangeTracking;

public class Saga
{
    public string Id { get; set; } = "";
    public string Status { get; set; } = "RUNNING";
    public int StepIndex { get; set; }
    public JsonObject Context { get; set; } = new();
    public DateTime CreatedAt { get; set; }
    public DateTime UpdatedAt { get; set; }
}

public class SagaLogEntry
{
    public long Id { get; set; }
    public string SagaId { get; set; } = "";
    public string Step { get; set; } = "";
    public string Action { get; set; } = "";
    public JsonObject? Result { get; set; }
    public DateTime CreatedAt { get; set; }
}

public record SagaRequest(string OrderId, string Sku, double Total, bool FailShipping = false);

public record SagaDto(string Id, string Status, int StepIndex, JsonObject Context)
{
    public static SagaDto From(Saga s) => new(s.Id, s.Status, s.StepIndex, s.Context);
}

public record SagaLogDto(string Step, string Action, JsonObject? Result)
{
    public static SagaLogDto From(SagaLogEntry e) => new(e.Step, e.Action, e.Result);
}

/// <summary>Maps the shared sagas and saga_log tables; the schema is owned by db/init, so there are no migrations.</summary>
public class SagaContext(DbContextOptions<SagaContext> options) : DbContext(options)
{
    public DbSet<Saga> Sagas => Set<Saga>();
    public DbSet<SagaLogEntry> Log => Set<SagaLogEntry>();

    protected override void OnModelCreating(ModelBuilder modelBuilder)
    {
        // jsonb columns hold JsonObject documents; the comparer lets EF see in-place edits of the context.
        var json = new ValueComparer<JsonObject?>(
            (a, b) => a == null ? b == null : b != null && a.ToJsonString() == b.ToJsonString(),
            v => v == null ? 0 : v.ToJsonString().GetHashCode(),
            v => v == null ? null : v.DeepClone().AsObject());

        modelBuilder.Entity<Saga>(e =>
        {
            e.ToTable("sagas");
            e.Property(s => s.Id).HasColumnName("id");
            e.Property(s => s.Status).HasColumnName("status");
            e.Property(s => s.StepIndex).HasColumnName("step_index");
            e.Property(s => s.Context).HasColumnName("context").HasColumnType("jsonb")
                .HasConversion(v => v.ToJsonString(), v => JsonNode.Parse(v)!.AsObject(), json!);
            e.Property(s => s.CreatedAt).HasColumnName("created_at").HasDefaultValueSql("now()");
            e.Property(s => s.UpdatedAt).HasColumnName("updated_at").HasDefaultValueSql("now()");
        });

        modelBuilder.Entity<SagaLogEntry>(e =>
        {
            e.ToTable("saga_log");
            e.Property(l => l.Id).HasColumnName("id");
            e.Property(l => l.SagaId).HasColumnName("saga_id");
            e.Property(l => l.Step).HasColumnName("step");
            e.Property(l => l.Action).HasColumnName("action");
            e.Property(l => l.Result).HasColumnName("result").HasColumnType("jsonb")
                .HasConversion(v => v == null ? null : v.ToJsonString(), v => v == null ? null : JsonNode.Parse(v)!.AsObject(), json);
            e.Property(l => l.CreatedAt).HasColumnName("created_at").HasDefaultValueSql("now()");
        });
    }
}
