FROM registry.access.redhat.com/ubi9/dotnet-100 AS build
USER root
WORKDIR /src
COPY CacheService/CacheService.csproj CacheService/
RUN dotnet restore CacheService/CacheService.csproj
COPY CacheService/ CacheService/
RUN dotnet publish CacheService/CacheService.csproj -c Release -o /app

FROM registry.access.redhat.com/ubi9/dotnet-100-aspnet
WORKDIR /app
COPY --from=build /app .
EXPOSE 8080
ENTRYPOINT ["dotnet", "CacheService.dll"]
