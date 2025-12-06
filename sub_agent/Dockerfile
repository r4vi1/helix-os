# Stage 1: Builder
# Use Alpine for build tools (UPX)
FROM golang:1.21-alpine AS builder

# Install UPX (Ultimate Packer for eXecutables)
# Novel Idea: Binary Packing to rival TinyGo size
RUN apk add --no-cache upx

WORKDIR /app
COPY go.mod ./
COPY main.go ./

# Build the binary (Standard Go)
# -ldflags="-s -w": Strip symbols
RUN CGO_ENABLED=0 GOOS=linux go build -ldflags="-s -w" -o helix-agent .

# Compress with UPX
# --best: Max compression
# --lzma: Use LZMA algorithm for tightest pack
RUN upx --best --lzma -o helix-agent-compressed helix-agent

# Stage 2: Runtime
FROM scratch

WORKDIR /root/
# Copy the compressed binary
COPY --from=builder /app/helix-agent-compressed ./helix-agent
ENTRYPOINT ["./helix-agent"]
