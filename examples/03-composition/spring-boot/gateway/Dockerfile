FROM registry.access.redhat.com/ubi9/openjdk-21 AS build
USER root
RUN microdnf install -y maven && microdnf clean all
USER default
WORKDIR /home/default
COPY gateway/pom.xml pom.xml
COPY proto/ src/main/proto/
RUN mvn dependency:go-offline -B
COPY gateway/src src
RUN mvn package -DskipTests -B

FROM registry.access.redhat.com/ubi9/openjdk-21-runtime
COPY --from=build /home/default/target/*.jar /deployments/app.jar
EXPOSE 8080
CMD ["java", "-jar", "/deployments/app.jar"]
