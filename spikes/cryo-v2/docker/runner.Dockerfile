# Multi-stage build: static arm64 binaries, minimal runtime image. Runs as
# root inside the container (the task's own boundary) since the runner needs
# to mkdir/write under /sys/fs/cgroup and fork+setuid children; the forked
# backend itself drops to a non-root uid/gid at exec time.
FROM --platform=$BUILDPLATFORM golang:1.25-bookworm AS build
WORKDIR /src
COPY go.mod ./
COPY cmd ./cmd
RUN CGO_ENABLED=0 GOOS=linux GOARCH=arm64 go build -o /out/runner ./cmd/runner
RUN CGO_ENABLED=0 GOOS=linux GOARCH=arm64 go build -o /out/backend ./cmd/backend

FROM --platform=linux/arm64 public.ecr.aws/debian/debian:bookworm-slim
COPY --from=build /out/runner /usr/local/bin/runner
COPY --from=build /out/backend /usr/local/bin/backend
ENTRYPOINT ["/usr/local/bin/runner"]
