FROM registry.access.redhat.com/ubi9/openjdk-21:latest AS build
USER root
RUN microdnf install -y maven && microdnf clean all
WORKDIR /build
COPY pom.xml .
RUN mvn dependency:go-offline -B
COPY src src
RUN mvn package -DskipTests -B

FROM registry.access.redhat.com/ubi9/openjdk-21-runtime:latest
USER root
RUN microdnf install -y curl-minimal && microdnf clean all
USER default
WORKDIR /app
COPY --from=build /build/target/*.jar app.jar
EXPOSE 8080
CMD ["java", "-jar", "app.jar"]
