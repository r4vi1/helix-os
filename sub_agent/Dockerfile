# Stage 1: Builder
FROM golang:1.21-alpine AS builder

WORKDIR /app
COPY go.mod ./
COPY main.go ./

# Build the binary
# CGO_ENABLED=0 ensures static linking
# -ldflags="-s -w": Strip DWARF and symbol table for smaller size
RUN CGO_ENABLED=0 GOOS=linux go build -ldflags="-s -w" -o helix-agent .

# Stage 2: Runtime
FROM scratch

WORKDIR /root/
COPY --from=builder /app/helix-agent .
ENTRYPOINT ["./helix-agent"]
