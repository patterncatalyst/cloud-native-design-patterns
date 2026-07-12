namespace OrderService.Domain;

public record PlaceOrderCmd(string Sku, int Quantity);

public class Order
{
    public string Id { get; init; } = "";
    public string Sku { get; init; } = "";
    public int Quantity { get; init; }
    public string Status { get; init; } = "placed";
    public DateTime CreatedAt { get; init; }

    public static Order Create(PlaceOrderCmd cmd)
    {
        if (cmd.Quantity <= 0) throw new ArgumentException("quantity must be positive");
        if (string.IsNullOrEmpty(cmd.Sku)) throw new ArgumentException("sku is required");

        return new Order
        {
            Id = Guid.NewGuid().ToString(),
            Sku = cmd.Sku,
            Quantity = cmd.Quantity,
            Status = "placed",
            CreatedAt = DateTime.UtcNow
        };
    }
}

public record OrderPlaced(string OrderId, string Sku, int Quantity);
