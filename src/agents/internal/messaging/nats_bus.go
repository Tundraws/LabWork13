package messaging

import (
	"context"
	"encoding/json"
	"time"

	"github.com/nats-io/nats.go"
)

type MessageHandler func(ctx context.Context, data []byte) error

type Bus interface {
	Publish(ctx context.Context, subject string, value any) error
	Subscribe(subject string, queue string, handler MessageHandler) (*nats.Subscription, error)
	Close()
}

type NATSBus struct {
	conn *nats.Conn
}

func NewNATSBus(url string) (*NATSBus, error) {
	conn, err := nats.Connect(url, nats.Timeout(5*time.Second), nats.RetryOnFailedConnect(true))
	if err != nil {
		return nil, err
	}
	return &NATSBus{conn: conn}, nil
}

func (b *NATSBus) Publish(ctx context.Context, subject string, value any) error {
	data, err := json.Marshal(value)
	if err != nil {
		return err
	}
	if err := b.conn.Publish(subject, data); err != nil {
		return err
	}
	done := make(chan error, 1)
	go func() { done <- b.conn.Flush() }()
	select {
	case <-ctx.Done():
		return ctx.Err()
	case err := <-done:
		return err
	}
}

func (b *NATSBus) Subscribe(subject string, queue string, handler MessageHandler) (*nats.Subscription, error) {
	return b.conn.QueueSubscribe(subject, queue, func(message *nats.Msg) {
		ctx, cancel := context.WithTimeout(context.Background(), 20*time.Second)
		defer cancel()
		_ = handler(ctx, message.Data)
	})
}

func (b *NATSBus) Close() {
	b.conn.Drain()
	b.conn.Close()
}
