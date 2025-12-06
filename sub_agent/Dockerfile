# Stage 1: Builder
# Use TinyGo for extreme size optimization (Level 2)
FROM tinygo/tinygo:latest AS builder

WORKDIR /app
COPY go.mod ./
COPY main.go ./

# Build the binary with TinyGo
# -no-debug: Strip debug symbols (Level 1)
RUN tinygo build -o helix-agent -no-debug .

# Stage 2: Runtime
FROM scratch

WORKDIR /root/

# Copy the binary from builder
COPY --from=builder /app/helix-agent .

# Entrypoint
ENTRYPOINT ["./helix-agent"]
