FROM golang:1.26-bookworm AS builder
WORKDIR /src
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build -ldflags='-s -w' -o /app ./cmd/consumer

FROM registry.access.redhat.com/ubi10/ubi-minimal:latest AS runtime
COPY --from=builder /app /usr/local/bin/app
ENTRYPOINT ["/usr/local/bin/app"]
