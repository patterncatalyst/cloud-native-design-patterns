namespace BlazorDashboard;

public record OrderDto(string Id, string Sku, int Quantity, string Status)
{
    public static OrderDto From(Order o) => new(o.Id, o.Sku, o.Quantity, o.Status);
}
