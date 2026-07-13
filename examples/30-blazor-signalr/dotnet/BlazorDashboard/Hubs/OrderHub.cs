using Microsoft.AspNetCore.SignalR;

namespace BlazorDashboard.Hubs;

public class OrderHub : Hub
{
    public async Task JoinDashboard()
    {
        await Groups.AddToGroupAsync(Context.ConnectionId, "dashboard");
    }
}
