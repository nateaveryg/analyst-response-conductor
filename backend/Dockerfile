# Multi-stage distroless build for The Conductor v3
# Stage 1: Build static binary
FROM golang:1.24-bookworm AS builder
WORKDIR /app

# Copy source and build static binary using vendored dependencies
COPY . .
RUN CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -mod=vendor \
    -ldflags="-s -w -extldflags '-static'" \
    -o /app/conductor-server ./cmd/server

# Stage 2: Distroless scratch runtime (~25MB container)
FROM gcr.io/distroless/static-debian12:nonroot
USER nonroot:nonroot
WORKDIR /
COPY --from=builder /app/conductor-server /conductor-server

EXPOSE 8080
ENV PORT=8080
ENV GIN_MODE=release
ENV AGENT_RUNTIME=agent-engine
ENV SERVICE_VERSION=3.3.2
ENV VERIFICATION_MARKER=v3.3.2-verified

ENTRYPOINT ["/conductor-server"]
