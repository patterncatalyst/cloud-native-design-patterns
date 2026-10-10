FROM registry.access.redhat.com/ubi9/dotnet-100 AS build
USER root
WORKDIR /src
COPY WsServer/WsServer.csproj WsServer/
RUN dotnet restore WsServer/WsServer.csproj
COPY WsServer/ WsServer/
RUN dotnet publish WsServer/WsServer.csproj -c Release -o /app

FROM registry.access.redhat.com/ubi9/dotnet-100-aspnet
WORKDIR /app
COPY --from=build /app .
EXPOSE 8080
ENTRYPOINT ["dotnet", "WsServer.dll"]
