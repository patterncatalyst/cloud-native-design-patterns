using Npgsql;
using OrderService.Domain;

namespace OrderService.Adapters;

public class PostgresOrderRepository : IOrderRepository
{
    private readonly NpgsqlDataSource _db;

    public PostgresOrderRepository(NpgsqlDataSource db) => _db = db;

    public async Task SaveAsync(Order order)
    {
        await using var conn = await _db.OpenConnectionAsync();
        await using var cmd = conn.CreateCommand();
        cmd.CommandText = "INSERT INTO orders (id, sku, quantity, status, created_at) VALUES ($1, $2, $3, $4, $5)";
        cmd.Parameters.AddWithValue(order.Id);
        cmd.Parameters.AddWithValue(order.Sku);
        cmd.Parameters.AddWithValue(order.Quantity);
        cmd.Parameters.AddWithValue(order.Status);
        cmd.Parameters.AddWithValue(order.CreatedAt);
        await cmd.ExecuteNonQueryAsync();
    }

    public async Task<Order?> FindByIdAsync(string orderId)
    {
        await using var conn = await _db.OpenConnectionAsync();
        await using var cmd = conn.CreateCommand();
        cmd.CommandText = "SELECT id, sku, quantity, status, created_at FROM orders WHERE id = $1";
        cmd.Parameters.AddWithValue(orderId);
        await using var reader = await cmd.ExecuteReaderAsync();
        if (!await reader.ReadAsync()) return null;

        return new Order
        {
            Id = reader.GetString(0),
            Sku = reader.GetString(1),
            Quantity = reader.GetInt32(2),
            Status = reader.GetString(3),
            CreatedAt = reader.GetDateTime(4)
        };
    }

    public async Task<IReadOnlyList<Order>> ListAllAsync()
    {
        await using var conn = await _db.OpenConnectionAsync();
        await using var cmd = conn.CreateCommand();
        cmd.CommandText = "SELECT id, sku, quantity, status, created_at FROM orders ORDER BY created_at";
        await using var reader = await cmd.ExecuteReaderAsync();

        var orders = new List<Order>();
        while (await reader.ReadAsync())
        {
            orders.Add(new Order
            {
                Id = reader.GetString(0),
                Sku = reader.GetString(1),
                Quantity = reader.GetInt32(2),
                Status = reader.GetString(3),
                CreatedAt = reader.GetDateTime(4)
            });
        }
        return orders;
    }
}
