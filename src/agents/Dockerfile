FROM golang:1.22-alpine AS build
WORKDIR /src
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build -trimpath -ldflags="-s -w" -o /out/supply-agent ./cmd/supply-agent

FROM gcr.io/distroless/static-debian12:nonroot
WORKDIR /app
COPY --from=build /out/supply-agent /app/supply-agent
USER nonroot:nonroot
ENTRYPOINT ["/app/supply-agent"]
