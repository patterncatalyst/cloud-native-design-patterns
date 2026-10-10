FROM golang:1.26-bookworm AS builder
WORKDIR /src
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build -ldflags='-s -w' -o /app ./cmd/server
RUN CGO_ENABLED=0 GOOS=linux go build -ldflags='-s -w' -o /cli-place-order ./cmd/cli

FROM registry.access.redhat.com/ubi10/ubi-minimal:latest AS runtime
RUN microdnf install -y curl-minimal python3 && microdnf clean all && \
    ln -sf /usr/bin/python3 /usr/bin/python
COPY --from=builder /app /usr/local/bin/app
COPY --from=builder /cli-place-order /usr/local/bin/cli-place-order
COPY cli_place_order.py /cli_place_order.py
WORKDIR /
EXPOSE 8080
ENTRYPOINT ["/usr/local/bin/app"]
