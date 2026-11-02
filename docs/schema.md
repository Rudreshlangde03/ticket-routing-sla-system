# Schema and Relationship Notes

## Core Relationships

- Customer 1:N Ticket.
- Channel 1:N Ticket and Message.
- Ticket 1:N Message, AssignmentEvent, Resolution and TicketEvent.
- Intent 1:N Ticket and PriorityRule.
- Agent N:M Skill through `agent_skills`.
- Agent N:M Language through `agent_languages`.
- Queue 1:N AssignmentEvent.
- Ticket 1:N SLAEvent.
- Ticket 1:N Resolution supports reopened cases without deleting earlier resolutions.

## Ticket Lifecycle

The `ticket_events` table stores ticket lifecycle history, including:

- Ticket creation.
- Assignment.
- First response.
- Resolution.
- Reopening.

Previous events are retained to preserve the ticket's history.

## Ground Truth

The `ground_truth` table stores labelled synthetic anomalies for testing and verification.

Five injected anomaly types:

- Agent assigned beyond concurrency capacity.
- SLA calendar mismatch.
- Reopened ticket missing resolution history.
- Ticket transfer loop.
- Priority conflicting with a safety rule.

## Relationship and History Rules

- Agent-skill and agent-language relationships carry `effective_from` and optional `effective_to`.
- Assignment and resolution history must be retained.
- Reopened tickets should preserve previous resolution and assignment records.
- Ticket events are stored as historical records rather than overwriting previous events.
