package config

import (
	"context"
	"errors"
	"os"
	"time"

	"github.com/tundraws/labwork13/src/agents/internal/domain"
	"gopkg.in/yaml.v3"
)

type Config struct {
	NATSURL         string
	RedisURL        string
	JaegerEndpoint  string
	InstanceID      string
	TaskSubject     string
	ResultSubject   string
	BidSubject      string
	BidReplySubject string
	ShutdownGrace   time.Duration
	Rules           domain.RoleRules
}

func Load(ctx context.Context) (Config, error) {
	path := env("AGENT_CONFIG_PATH", "")
	if path == "" {
		return Config{}, errors.New("AGENT_CONFIG_PATH is required")
	}
	data, err := os.ReadFile(path)
	if err != nil {
		return Config{}, err
	}
	var rules domain.RoleRules
	if err := yaml.Unmarshal(data, &rules); err != nil {
		return Config{}, err
	}
	select {
	case <-ctx.Done():
		return Config{}, ctx.Err()
	default:
	}
	return Config{
		NATSURL:         env("NATS_URL", "nats://localhost:4222"),
		RedisURL:        env("REDIS_URL", "redis://localhost:6379/0"),
		JaegerEndpoint:  env("JAEGER_ENDPOINT", ""),
		InstanceID:      env("AGENT_INSTANCE_ID", string(rules.Role)+"-local"),
		TaskSubject:     "supply.tasks." + string(rules.Role),
		ResultSubject:   "supply.results",
		BidSubject:      "supply.auction.bid",
		BidReplySubject: "supply.auction.reply",
		ShutdownGrace:   8 * time.Second,
		Rules:           rules,
	}, nil
}

func env(key string, fallback string) string {
	value := os.Getenv(key)
	if value == "" {
		return fallback
	}
	return value
}
