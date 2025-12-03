# Stage 1: Builder
FROM golang:1.21-alpine AS builder

WORKDIR /app
COPY go.mod ./
COPY main.go ./

# Build the binary
# CGO_ENABLED=0 creates a statically linked binary (required for scratch)
RUN CGO_ENABLED=0 GOOS=linux go build -o helix-agent .

# Stage 2: Runtime
FROM scratch

WORKDIR /root/

# Copy the binary from builder
COPY --from=builder /app/helix-agent .

# Entrypoint
ENTRYPOINT ["./helix-agent"]
