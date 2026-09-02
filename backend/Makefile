.PHONY: all build test race bench run clean

all: build test

build:
	CGO_ENABLED=0 go build -ldflags="-s -w -extldflags '-static'" -o conductor-server ./cmd/server

test:
	go test -v ./...

race:
	go test -v -race ./...

bench:
	go test -v ./internal/rag -bench=. -benchmem

run: build
	PORT=8080 ./conductor-server

clean:
	rm -f conductor-server
