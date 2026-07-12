FROM registry.access.redhat.com/ubi9/dotnet-100 AS build
USER root
WORKDIR /src
COPY FlagService/FlagService.csproj FlagService/
RUN dotnet restore FlagService/FlagService.csproj
COPY FlagService/ FlagService/
RUN dotnet publish FlagService/FlagService.csproj -c Release -o /app

FROM registry.access.redhat.com/ubi9/dotnet-100-aspnet
WORKDIR /app
COPY --from=build /app .
EXPOSE 8080
ENTRYPOINT ["dotnet", "FlagService.dll"]
