FROM --platform=$BUILDPLATFORM golang:1.25-bookworm AS build
WORKDIR /src
COPY go.mod go.sum ./
COPY cmd ./cmd
RUN CGO_ENABLED=0 GOOS=linux GOARCH=arm64 go build -o /out/echo-backend ./cmd/echo-backend

FROM --platform=linux/arm64 gcr.io/distroless/static-debian12
COPY --from=build /out/echo-backend /echo-backend
ENTRYPOINT ["/echo-backend"]
