package main

import (
	"context"
	"log/slog"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/tundraws/labwork13/src/agents/internal/agent"
	"github.com/tundraws/labwork13/src/agents/internal/config"
	"github.com/tundraws/labwork13/src/agents/internal/messaging"
	"github.com/tundraws/labwork13/src/agents/internal/observability"
	"github.com/tundraws/labwork13/src/agents/internal/state"
)

func main() {
	if err := run(context.Background()); err != nil {
		slog.Error("agent stopped with error", "error", err)
		os.Exit(1)
	}
}

func run(parent context.Context) error {
	ctx, stop := signal.NotifyContext(parent, syscall.SIGINT, syscall.SIGTERM)
	defer stop()

	logger := slog.New(slog.NewJSONHandler(os.Stdout, &slog.HandlerOptions{Level: slog.LevelInfo}))
	cfg, err := config.Load(ctx)
	if err != nil {
		return err
	}
	shutdownTracing, err := observability.ConfigureTracing(ctx, "supply-agent-"+string(cfg.Rules.Role), cfg.JaegerEndpoint)
	if err != nil {
		return err
	}
	defer func() {
		shutdownCtx, cancel := context.WithTimeout(context.Background(), cfg.ShutdownGrace)
		defer cancel()
		_ = shutdownTracing(shutdownCtx)
	}()

	bus, err := messaging.NewNATSBus(cfg.NATSURL)
	if err != nil {
		return err
	}
	defer bus.Close()

	store, err := state.NewRedisStore(cfg.RedisURL)
	if err != nil {
		return err
	}
	defer store.Close()

	service := agent.NewService(cfg, bus, store, logger)
	done := make(chan error, 1)
	go func() { done <- service.Start(ctx) }()
	select {
	case <-ctx.Done():
		shutdownCtx, cancel := context.WithTimeout(context.Background(), 3*time.Second)
		defer cancel()
		<-shutdownCtx.Done()
		return nil
	case err := <-done:
		return err
	}
}
