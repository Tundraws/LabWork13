package domain

import "testing"

func TestProcessorProcessForecast(t *testing.T) {
	processor := NewProcessor(RoleRules{Role: RoleForecast, DisplayName: "forecast"})
	result, err := processor.Process(Task{
		ID:      "task-1",
		TraceID: "trace-1",
		Type:    RoleForecast,
		Payload: map[string]any{
			"avg_daily_sales":   12,
			"seasonality_index": 1.25,
			"planning_days":     10,
			"current_stock":     50,
		},
	})
	if err != nil {
		t.Fatalf("expected success, got %v", err)
	}
	if !result.Success {
		t.Fatal("expected successful result")
	}
	if result.Output["forecast_units"].(float64) != 150 {
		t.Fatalf("unexpected forecast: %v", result.Output["forecast_units"])
	}
	if result.Output["reorder_units"].(float64) != 100 {
		t.Fatalf("unexpected reorder: %v", result.Output["reorder_units"])
	}
}

func TestProcessorRejectsWrongRole(t *testing.T) {
	processor := NewProcessor(RoleRules{Role: RoleRisk, DisplayName: "risk"})
	_, err := processor.Process(Task{ID: "task-1", Type: RoleForecast, Payload: map[string]any{}})
	if err == nil {
		t.Fatal("expected role mismatch error")
	}
}

func TestOrderingRequiresPositiveReorderQuantity(t *testing.T) {
	processor := NewProcessor(RoleRules{Role: RoleOrdering, DisplayName: "ordering"})
	_, err := processor.Process(Task{
		ID:      "task-1",
		TraceID: "trace-1",
		Type:    RoleOrdering,
		Payload: map[string]any{"reorder_units": 0},
	})
	if err == nil {
		t.Fatal("expected validation error")
	}
}

func TestBidCostPenalizesWrongRole(t *testing.T) {
	processor := NewProcessor(RoleRules{Role: RoleTracking, DisplayName: "tracking"})
	bid := processor.EstimateBid(BidRequest{TaskID: "task-1", Type: RoleRisk}, 1)
	if bid.Cost < 1000 {
		t.Fatalf("expected high cost for wrong role, got %v", bid.Cost)
	}
}
