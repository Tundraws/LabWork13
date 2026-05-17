package agent

import (
	"context"
	"encoding/json"
	"errors"
	"log/slog"

	"github.com/nats-io/nats.go"
	"github.com/tundraws/labwork13/src/agents/internal/config"
	"github.com/tundraws/labwork13/src/agents/internal/domain"
	"github.com/tundraws/labwork13/src/agents/internal/messaging"
	"github.com/tundraws/labwork13/src/agents/internal/state"
	"go.opentelemetry.io/otel"
)

type Service struct {
	cfg       config.Config
	bus       messaging.Bus
	store     state.Store
	processor domain.Processor
	logger    *slog.Logger
}

func NewService(cfg config.Config, bus messaging.Bus, store state.Store, logger *slog.Logger) Service {
	return Service{
		cfg:       cfg,
		bus:       bus,
		store:     store,
		processor: domain.NewProcessor(cfg.Rules),
		logger:    logger,
	}
}

func (s Service) Start(ctx context.Context) error {
	taskSub, err := s.bus.Subscribe(s.cfg.TaskSubject, string(s.cfg.Rules.Role), s.handleTask)
	if err != nil {
		return err
	}
	bidSub, err := s.bus.Subscribe(s.cfg.BidSubject, s.cfg.InstanceID, s.handleBid)
	if err != nil {
		return err
	}
	s.logger.Info("agent started", "instance", s.cfg.InstanceID, "role", s.cfg.Rules.Role)
	<-ctx.Done()
	_ = taskSub.Drain()
	_ = bidSub.Drain()
	return nil
}

func (s Service) handleTask(ctx context.Context, data []byte) error {
	tracer := otel.Tracer("supply-agent")
	ctx, span := tracer.Start(ctx, "agent.process."+string(s.cfg.Rules.Role))
	defer span.End()

	var task domain.Task
	if err := json.Unmarshal(data, &task); err != nil {
		s.logger.Error("invalid task", "error", err)
		return err
	}
	result, err := s.processor.Process(task)
	if err != nil {
		result = domain.Result{
			TaskID:  task.ID,
			TraceID: task.TraceID,
			Agent:   s.cfg.Rules.DisplayName,
			Role:    s.cfg.Rules.Role,
			Success: false,
			Error:   err.Error(),
		}
	}
	if _, countErr := s.store.IncrementProcessed(ctx, s.cfg.InstanceID); countErr != nil {
		s.logger.Error("state update failed", "error", countErr)
	}
	if publishErr := s.bus.Publish(ctx, s.cfg.ResultSubject, result); publishErr != nil {
		return publishErr
	}
	s.logger.Info("task processed", "task_id", task.ID, "success", result.Success)
	return err
}

func (s Service) handleBid(ctx context.Context, data []byte) error {
	var request domain.BidRequest
	if err := json.Unmarshal(data, &request); err != nil {
		return err
	}
	count, err := s.store.ProcessedCount(ctx, s.cfg.InstanceID)
	if err != nil && !errors.Is(err, nats.ErrNoResponders) {
		s.logger.Error("bid state read failed", "error", err)
	}
	bid := s.processor.EstimateBid(request, count)
	if err := s.bus.Publish(ctx, s.cfg.BidReplySubject, bid); err != nil {
		return err
	}
	s.logger.Info("bid sent", "task_id", request.TaskID, "cost", bid.Cost)
	return nil
}
