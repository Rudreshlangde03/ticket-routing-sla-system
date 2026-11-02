# Data Dictionary

All timestamps use ISO-8601 UTC. IDs are immutable strings. Empty `effective_to` and `ended_at` indicate an open-ended relationship or event.

| Entity | Primary key | Key fields | Cardinality |
|---|---|---|---|
| Customer | customer_id | tier, preferred_language_id, created_at | Customer 1:N Ticket |
| Channel | channel_id | channel_name, calendar_type | Channel 1:N Ticket and Message |
| Ticket | ticket_id | customer_id, channel_id, intent_id, language_id, priority, status | Ticket 1:N Message, AssignmentEvent, Resolution and TicketEvent |
| Message | message_id | ticket_id, sender_type, sent_at, language_id | Message N:1 Ticket |
| Intent | intent_id | intent_name, required_skill | Intent 1:N Ticket and PriorityRule |
| Language | language_id | language_name, language_code | Referenced by Customer, Ticket, Message and Agent |
| PriorityRule | priority_rule_id | intent_id, priority, response/resolution minutes, safety_override | Intent 1:N PriorityRule |
| Agent | agent_id | status, shift hours, concurrency_limit, max_daily_tickets | Agent N:M Skill and Language |
| Skill | skill_id | skill_name | Agent N:M Skill |
| Queue | queue_id | queue_name, required_skill | Queue 1:N AssignmentEvent |
| AssignmentEvent | assignment_id | ticket_id, agent_id, queue_id, event_type | Ticket 1:N AssignmentEvent |
| SLAEvent | sla_id | ticket_id, due timestamps, calendar_type, policy_version | Ticket 1:N SLAEvent |
| Resolution | resolution_id | ticket_id, resolved_at, code, CSAT, reopen_count | Ticket 1:N Resolution |
| TicketEvent | event_id | ticket_id, event_type, event_at, actor_type, details | Ticket 1:N TicketEvent |
| GroundTruth | anomaly_id | ticket_id, issue_type, ground_truth, description | Ticket 1:N GroundTruth |

## Bridge Tables

- `agent_skills` implements Agent N:M Skill.
- `agent_languages` implements Agent N:M Language.
- Both bridge tables include effective dates.

## Ticket Lifecycle

The `ticket_events` table preserves ticket history, including creation, assignment, first response, resolution and reopening.

## Anomaly Labels

The `ground_truth` table stores labelled synthetic anomalies:

- agent_over_capacity
- sla_calendar_mismatch
- reopened_history_missing
- transfer_loop
- priority_safety_conflict

## Validation

Validation intent includes unique primary keys, valid foreign keys, supported priority and status values, CSAT scores from 1 to 5, positive capacities and UTC ISO-8601 timestamps.

The validation script checks file presence, primary-key uniqueness and selected foreign-key relationships. Further lifecycle and chronology checks may be added as the project develops.
