package state

import (
	"context"

	"github.com/redis/go-redis/v9"
)

type Store interface {
	IncrementProcessed(ctx context.Context, agentID string) (int64, error)
	ProcessedCount(ctx context.Context, agentID string) (int64, error)
	Close() error
}

type RedisStore struct {
	client *redis.Client
}

func NewRedisStore(redisURL string) (*RedisStore, error) {
	options, err := redis.ParseURL(redisURL)
	if err != nil {
		return nil, err
	}
	return &RedisStore{client: redis.NewClient(options)}, nil
}

func (s *RedisStore) IncrementProcessed(ctx context.Context, agentID string) (int64, error) {
	return s.client.Incr(ctx, "agent:"+agentID+":processed").Result()
}

func (s *RedisStore) ProcessedCount(ctx context.Context, agentID string) (int64, error) {
	value, err := s.client.Get(ctx, "agent:"+agentID+":processed").Int64()
	if err == redis.Nil {
		return 0, nil
	}
	return value, err
}

func (s *RedisStore) Close() error {
	return s.client.Close()
}
