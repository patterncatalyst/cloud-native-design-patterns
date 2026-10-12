using Microsoft.EntityFrameworkCore;
using OrderService.Domain;

namespace OrderService.Adapters;

public class EfOrderRepository(OrdersContext db) : IOrderRepository
{
    public async Task SaveAsync(Order order)
    {
        db.Orders.Add(order);
        await db.SaveChangesAsync();
    }

    public Task<Order?> FindByIdAsync(string orderId) =>
        db.Orders.AsNoTracking().FirstOrDefaultAsync(o => o.Id == orderId);

    public async Task<IReadOnlyList<Order>> ListAllAsync() =>
        await db.Orders.AsNoTracking().OrderBy(o => o.CreatedAt).ToListAsync();
}
