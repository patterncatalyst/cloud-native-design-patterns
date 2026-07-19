FROM registry.access.redhat.com/ubi10/openjdk-25 AS build
USER root
RUN microdnf install -y maven && microdnf clean all
USER default
WORKDIR /home/default
COPY gateway/pom.xml pom.xml
COPY proto/ src/main/proto/
RUN mvn dependency:go-offline -B
COPY gateway/src src
RUN mvn package -DskipTests -B

FROM registry.access.redhat.com/ubi10/openjdk-25-runtime
WORKDIR /deployments
COPY --from=build /home/default/target/quarkus-app/ ./
EXPOSE 8080
CMD ["java", "-jar", "quarkus-run.jar"]
