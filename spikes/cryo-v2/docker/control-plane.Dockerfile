FROM --platform=$BUILDPLATFORM golang:1.25-bookworm AS build
WORKDIR /src
COPY go.mod go.sum ./
RUN go mod download
COPY cmd ./cmd
RUN CGO_ENABLED=0 GOOS=linux GOARCH=arm64 go build -o /out/control-plane ./cmd/control-plane

FROM --platform=linux/arm64 gcr.io/distroless/static-debian12
COPY --from=build /out/control-plane /control-plane
ENTRYPOINT ["/control-plane"]
