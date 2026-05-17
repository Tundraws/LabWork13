package domain

import "time"

type AgentRole string

const (
	RoleForecast AgentRole = "forecast"
	RoleOrdering AgentRole = "ordering"
	RoleTracking AgentRole = "tracking"
	RoleRisk     AgentRole = "risk"
)

type Task struct {
	ID          string         `json:"id"`
	TraceID     string         `json:"trace_id"`
	Type        AgentRole      `json:"type"`
	Payload     map[string]any `json:"payload"`
	PipelineLog []StepLog      `json:"pipeline_log"`
}

type StepLog struct {
	Agent     string         `json:"agent"`
	Action    string         `json:"action"`
	Input     map[string]any `json:"input,omitempty"`
	Output    map[string]any `json:"output,omitempty"`
	CreatedAt time.Time      `json:"created_at"`
}

type Result struct {
	TaskID      string         `json:"task_id"`
	TraceID     string         `json:"trace_id"`
	Agent       string         `json:"agent"`
	Role        AgentRole      `json:"role"`
	Success     bool           `json:"success"`
	Output      map[string]any `json:"output"`
	Error       string         `json:"error,omitempty"`
	PipelineLog []StepLog      `json:"pipeline_log"`
}

type BidRequest struct {
	TaskID  string         `json:"task_id"`
	Type    AgentRole      `json:"type"`
	Payload map[string]any `json:"payload"`
}

type Bid struct {
	TaskID     string    `json:"task_id"`
	Agent      string    `json:"agent"`
	Role       AgentRole `json:"role"`
	Cost       float64   `json:"cost"`
	Confidence float64   `json:"confidence"`
}

type RoleRules struct {
	Role           AgentRole `yaml:"role"`
	DisplayName    string    `yaml:"display_name"`
	Communication  string    `yaml:"communication"`
	Specialization string    `yaml:"specialization"`
	Rules          []string  `yaml:"rules"`
}
