FROM --platform=$BUILDPLATFORM golang:1.25-bookworm AS build
WORKDIR /src
COPY go.mod go.sum ./
RUN go mod download
COPY cmd ./cmd
RUN CGO_ENABLED=0 GOOS=linux GOARCH=arm64 go build -o /out/scheduler-harness ./cmd/scheduler-harness

FROM --platform=linux/arm64 gcr.io/distroless/static-debian12
COPY --from=build /out/scheduler-harness /scheduler-harness
ENTRYPOINT ["/scheduler-harness"]
