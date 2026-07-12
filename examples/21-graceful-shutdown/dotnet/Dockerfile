FROM registry.access.redhat.com/ubi9/dotnet-100 AS build
USER root
WORKDIR /src
COPY OrderService/OrderService.csproj OrderService/
RUN dotnet restore OrderService/OrderService.csproj
COPY OrderService/ OrderService/
RUN dotnet publish OrderService/OrderService.csproj -c Release -o /app

FROM registry.access.redhat.com/ubi9/dotnet-100-aspnet
WORKDIR /app
COPY --from=build /app .
EXPOSE 8080
ENTRYPOINT ["dotnet", "OrderService.dll"]
