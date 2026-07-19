FROM registry.access.redhat.com/ubi10/openjdk-25 AS build
USER root
RUN microdnf install -y maven && microdnf clean all
USER default
WORKDIR /home/default
COPY pom.xml .
RUN mvn dependency:go-offline -B
COPY src src
RUN mvn package -DskipTests -B

FROM registry.access.redhat.com/ubi10/openjdk-25-runtime
USER root
RUN microdnf install -y python3 && ln -sf /usr/bin/python3 /usr/bin/python && microdnf clean all
USER 185
WORKDIR /deployments
COPY --from=build /home/default/target/quarkus-app/ ./
COPY cli_place_order.py ./
EXPOSE 8080
CMD ["java", "-jar", "quarkus-run.jar"]
