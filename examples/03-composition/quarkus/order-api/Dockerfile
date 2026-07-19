FROM registry.access.redhat.com/ubi10/openjdk-25 AS build
USER root
RUN microdnf install -y maven && microdnf clean all
USER default
WORKDIR /home/default
COPY order-api/pom.xml pom.xml
RUN mvn dependency:go-offline -B
COPY order-api/src src
RUN mvn package -DskipTests -B

FROM registry.access.redhat.com/ubi10/openjdk-25-runtime
WORKDIR /deployments
COPY --from=build /home/default/target/quarkus-app/ ./
EXPOSE 8081
CMD ["java", "-jar", "quarkus-run.jar"]
