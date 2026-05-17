package domain

import (
	"errors"
	"fmt"
	"math"
	"time"
)

type Processor struct {
	rules RoleRules
}

func NewProcessor(rules RoleRules) Processor {
	return Processor{rules: rules}
}

func (p Processor) EstimateBid(task BidRequest, processedCount int64) Bid {
	baseCost := 10.0 + float64(processedCount%7)
	if task.Type != p.rules.Role {
		baseCost += 1000
	}
	return Bid{
		TaskID:     task.TaskID,
		Agent:      p.rules.DisplayName,
		Role:       p.rules.Role,
		Cost:       baseCost,
		Confidence: math.Max(0.1, 0.96-float64(processedCount%5)*0.04),
	}
}

func (p Processor) Process(task Task) (Result, error) {
	if task.Type != p.rules.Role {
		return Result{}, fmt.Errorf("agent role %s cannot process task type %s", p.rules.Role, task.Type)
	}

	output, err := p.processByRole(task.Payload)
	if err != nil {
		return Result{}, err
	}

	step := StepLog{
		Agent:     p.rules.DisplayName,
		Action:    string(p.rules.Role),
		Input:     task.Payload,
		Output:    output,
		CreatedAt: time.Now().UTC(),
	}

	return Result{
		TaskID:      task.ID,
		TraceID:     task.TraceID,
		Agent:       p.rules.DisplayName,
		Role:        p.rules.Role,
		Success:     true,
		Output:      output,
		PipelineLog: append(task.PipelineLog, step),
	}, nil
}

func (p Processor) processByRole(payload map[string]any) (map[string]any, error) {
	switch p.rules.Role {
	case RoleForecast:
		return forecastDemand(payload)
	case RoleOrdering:
		return createSupplierOrder(payload)
	case RoleTracking:
		return trackShipment(payload)
	case RoleRisk:
		return evaluateRisk(payload)
	default:
		return nil, errors.New("unsupported agent role")
	}
}

func forecastDemand(payload map[string]any) (map[string]any, error) {
	avgDailySales := number(payload, "avg_daily_sales", 0)
	seasonality := number(payload, "seasonality_index", 1)
	days := number(payload, "planning_days", 14)
	currentStock := number(payload, "current_stock", 0)
	if avgDailySales <= 0 || days <= 0 {
		return nil, errors.New("avg_daily_sales and planning_days must be positive")
	}
	forecast := math.Ceil(avgDailySales * seasonality * days)
	reorderQty := math.Max(0, forecast-currentStock)
	return map[string]any{
		"forecast_units": forecast,
		"reorder_units":  reorderQty,
		"confidence":     0.87,
	}, nil
}

func createSupplierOrder(payload map[string]any) (map[string]any, error) {
	reorderUnits := number(payload, "reorder_units", 0)
	if reorderUnits <= 0 {
		return nil, errors.New("reorder_units must be positive")
	}
	unitPrice := number(payload, "unit_price", 11.5)
	return map[string]any{
		"supplier_id":    "supplier-priority-a",
		"order_id":       fmt.Sprintf("PO-%d", time.Now().UTC().UnixNano()),
		"ordered_units":  reorderUnits,
		"estimated_cost": math.Round(reorderUnits*unitPrice*100) / 100,
		"eta_days":       4,
	}, nil
}

func trackShipment(payload map[string]any) (map[string]any, error) {
	etaDays := number(payload, "eta_days", 4)
	if etaDays < 0 {
		return nil, errors.New("eta_days cannot be negative")
	}
	status := "in_transit"
	if etaDays == 0 {
		status = "delivered"
	}
	return map[string]any{
		"shipment_id": fmt.Sprintf("SHIP-%d", time.Now().UTC().Unix()%100000),
		"status":      status,
		"eta_days":    etaDays,
		"checkpoint":  "regional-hub",
	}, nil
}

func evaluateRisk(payload map[string]any) (map[string]any, error) {
	etaDays := number(payload, "eta_days", 0)
	orderedUnits := number(payload, "ordered_units", number(payload, "reorder_units", 0))
	score := math.Min(1, etaDays*0.08+orderedUnits/10000)
	level := "low"
	if score >= 0.65 {
		level = "high"
	} else if score >= 0.35 {
		level = "medium"
	}
	return map[string]any{
		"risk_score": math.Round(score*100) / 100,
		"risk_level": level,
		"mitigation": "keep safety stock and prepare backup supplier",
	}, nil
}

func number(payload map[string]any, key string, fallback float64) float64 {
	value, ok := payload[key]
	if !ok {
		return fallback
	}
	switch typed := value.(type) {
	case float64:
		return typed
	case float32:
		return float64(typed)
	case int:
		return float64(typed)
	case int64:
		return float64(typed)
	default:
		return fallback
	}
}
