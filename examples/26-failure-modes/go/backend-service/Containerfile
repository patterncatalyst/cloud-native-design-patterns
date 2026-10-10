FROM golang:1.26-bookworm AS builder
WORKDIR /src
COPY go.mod ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build -ldflags='-s -w' -o /app ./cmd/server

FROM registry.access.redhat.com/ubi10/ubi-minimal:latest AS runtime
RUN microdnf install -y curl-minimal && microdnf clean all
COPY --from=builder /app /usr/local/bin/app
EXPOSE 8081
ENTRYPOINT ["/usr/local/bin/app"]
