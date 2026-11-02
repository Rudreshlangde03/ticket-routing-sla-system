
COLUMNS = {
    "customers": [
        "customer_id", "customer_name", "customer_tier",
        "preferred_language_id", "created_at"
    ],
    "channels": [
        "channel_id", "channel_name", "calendar_type"
    ],
    "tickets": [
        "ticket_id", "customer_id", "channel_id", "intent_id",
        "language_id", "priority", "status", "created_at",
        "updated_at", "subject", "issue_type"
    ],
    "messages": [
        "message_id", "ticket_id", "channel_id", "sender_type",
        "sent_at", "language_id", "message_text", "is_internal"
    ],
    "intents": [
        "intent_id", "intent_name", "required_skill"
    ],
    "languages": [
        "language_id", "language_name", "language_code"
    ],
    "priority_rules": [
        "priority_rule_id", "intent_id", "priority",
        "first_response_minutes", "resolution_minutes",
        "safety_override"
    ],
    "agents": [
        "agent_id", "agent_name", "status",
        "shift_start_hour_utc", "shift_end_hour_utc",
        "concurrency_limit", "max_daily_tickets",
        "effective_from", "effective_to"
    ],
    "skills": [
        "skill_id", "skill_name"
    ],
    "queues": [
        "queue_id", "queue_name", "required_skill"
    ],
    "assignment_events": [
        "assignment_id", "ticket_id", "agent_id", "queue_id",
        "assigned_at", "ended_at", "event_type", "reason"
    ],
    "sla_events": [
        "sla_id", "ticket_id", "first_response_due_at",
        "resolution_due_at", "calendar_type", "sla_status",
        "policy_version"
    ],
    "resolutions": [
        "resolution_id", "ticket_id", "resolved_at",
        "resolution_code", "csat_score", "reopen_count",
        "resolution_notes"
    ],
    "agent_skills": [
        "agent_id", "skill_id", "effective_from", "effective_to"
    ],
    "agent_languages": [
        "agent_id", "language_id", "effective_from", "effective_to"
    ],
    "ticket_events": [
        "event_id", "ticket_id", "event_type",
        "event_at", "actor_type", "details"
    ],
    "ground_truth": [
        "anomaly_id", "ticket_id", "issue_type",
        "ground_truth", "description"
    ]
}
