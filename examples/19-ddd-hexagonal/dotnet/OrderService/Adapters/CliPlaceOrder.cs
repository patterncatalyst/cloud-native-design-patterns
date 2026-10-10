using OrderService.Domain;

namespace OrderService.Adapters;

/// <summary>
/// CLI driving adapter: `OrderService place-order &lt;sku&gt; &lt;quantity&gt;`.
/// Translates argv into a PlaceOrderCmd and calls the application service —
/// it never touches the repository. Same use case as the REST adapter.
/// </summary>
public static class CliPlaceOrder
{
    public static async Task<int> RunAsync(string[] args, PlaceOrderUseCase placeOrder)
    {
        if (args.Length < 2 || !int.TryParse(args[1], out var quantity))
        {
            Console.Error.WriteLine("Usage: cli-place-order <sku> <quantity>");
            return 1;
        }

        try
        {
            var order = await placeOrder.ExecuteAsync(new PlaceOrderCmd(args[0], quantity));
            Console.WriteLine(
                $"CLI_ORDER_CREATED id={order.Id} sku={order.Sku} qty={order.Quantity} status={order.Status}");
            return 0;
        }
        catch (ArgumentException e)
        {
            Console.Error.WriteLine($"Error: {e.Message}");
            return 1;
        }
    }
}
