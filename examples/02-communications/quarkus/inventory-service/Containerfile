FROM registry.access.redhat.com/ubi10/openjdk-25 AS build
USER root
RUN microdnf install -y maven && microdnf clean all
USER default
WORKDIR /home/default
COPY inventory-service/pom.xml pom.xml
COPY proto/ src/main/proto/
RUN mvn dependency:go-offline -B
COPY inventory-service/src src
RUN mvn package -DskipTests -B

FROM registry.access.redhat.com/ubi10/openjdk-25-runtime
WORKDIR /deployments
COPY --from=build /home/default/target/quarkus-app/ ./
EXPOSE 9000
CMD ["java", "-jar", "quarkus-run.jar"]
