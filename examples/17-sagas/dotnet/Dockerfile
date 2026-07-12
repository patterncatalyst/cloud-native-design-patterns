FROM registry.access.redhat.com/ubi9/dotnet-100 AS build
USER root
WORKDIR /src
COPY SagaOrchestrator/SagaOrchestrator.csproj SagaOrchestrator/
RUN dotnet restore SagaOrchestrator/SagaOrchestrator.csproj
COPY SagaOrchestrator/ SagaOrchestrator/
RUN dotnet publish SagaOrchestrator/SagaOrchestrator.csproj -c Release -o /app

FROM registry.access.redhat.com/ubi9/dotnet-100-aspnet
WORKDIR /app
COPY --from=build /app .
EXPOSE 8080
ENTRYPOINT ["dotnet", "SagaOrchestrator.dll"]
