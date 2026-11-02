
import csv
import json
import random
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

from src.schema import COLUMNS

BASE = datetime(2026, 11, 1, tzinfo=timezone.utc)


def iso(value):
    return value.isoformat()


def write_csv(path, rows, columns):
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def add_sla_minutes(start, minutes, calendar_type):
    """Add elapsed minutes using the channel's SLA calendar."""
    current = start
    remaining = minutes

    if calendar_type == "24x7":
        return current + timedelta(minutes=remaining)

    # Email business calendar: Monday-Friday, 09:00-17:00 UTC.
    while remaining > 0:
        if current.weekday() >= 5:
            current = (current + timedelta(days=1)).replace(
                hour=9, minute=0, second=0, microsecond=0
            )
            continue

        if current.hour < 9:
            current = current.replace(hour=9, minute=0, second=0, microsecond=0)

        if current.hour >= 17:
            current = (current + timedelta(days=1)).replace(
                hour=9, minute=0, second=0, microsecond=0
            )
            continue

        available = int(
            (current.replace(hour=17, minute=0, second=0, microsecond=0)
             - current).total_seconds() // 60
        )

        if remaining <= available:
            current += timedelta(minutes=remaining)
            remaining = 0
        else:
            remaining -= available
            current = (current + timedelta(days=1)).replace(
                hour=9, minute=0, second=0, microsecond=0
            )

    return current


def on_shift(agent, moment):
    hour = moment.hour
    start = int(agent["shift_start_hour_utc"])
    end = int(agent["shift_end_hour_utc"])

    if start < end:
        return start <= hour < end

    return hour >= start or hour < end


def generate(
    ticket_count=500,
    message_count=1500,
    agent_count=100,
    seed=20261022,
    output=Path("data/generated")
):
    if ticket_count < 10:
        raise ValueError("Use at least 10 tickets for anomaly generation.")
    if message_count < ticket_count or agent_count < 1:
        raise ValueError("Messages must be >= tickets and agents must be >= 1.")

    r = random.Random(seed)
    out = Path(output)
    out.mkdir(parents=True, exist_ok=True)

    # ---------------- MASTER DATA ----------------

    languages = [
        {"language_id": f"LANG-{code}", "language_name": name,
         "language_code": code.lower()}
        for code, name in [
            ("EN", "English"), ("HI", "Hindi"), ("MR", "Marathi"),
            ("ES", "Spanish"), ("DE", "German")
        ]
    ]

    channels = [
        {"channel_id": "CH-EMAIL", "channel_name": "email",
         "calendar_type": "business_hours"},
        {"channel_id": "CH-CHAT", "channel_name": "chat",
         "calendar_type": "24x7"},
        {"channel_id": "CH-PHONE", "channel_name": "phone",
         "calendar_type": "24x7"}
    ]

    intent_definitions = [
        ("account_access", "identity"),
        ("billing", "billing"),
        ("technical_issue", "technical"),
        ("network_outage", "network"),
        ("general_query", "general"),
        ("security_incident", "security")
    ]

    intents = [
        {"intent_id": f"INT-{i:03d}", "intent_name": name,
         "required_skill": skill}
        for i, (name, skill) in enumerate(intent_definitions, 1)
    ]

    skills = [
        {"skill_id": f"SK-{skill.upper()}", "skill_name": skill}
        for _, skill in intent_definitions
    ]

    queues = [
        {"queue_id": f"QUE-{skill.upper()}",
         "queue_name": f"{skill.title()} Queue",
         "required_skill": skill}
        for _, skill in intent_definitions
    ]

    targets = {
        "security_incident": ("critical", 5, 60, 1),
        "network_outage": ("high", 15, 240, 0),
        "technical_issue": ("normal", 60, 1440, 0),
        "billing": ("normal", 60, 1440, 0),
        "account_access": ("normal", 60, 1440, 0),
        "general_query": ("low", 240, 2880, 0)
    }

    priorities = []
    for i, intent in enumerate(intents, 1):
        priority, first_response, resolution, safety = targets[
            intent["intent_name"]
        ]
        priorities.append({
            "priority_rule_id": f"PR-{i:03d}",
            "intent_id": intent["intent_id"],
            "priority": priority,
            "first_response_minutes": first_response,
            "resolution_minutes": resolution,
            "safety_override": safety
        })

    customers = []
    for i in range(1, max(101, ticket_count // 3) + 1):
        customers.append({
            "customer_id": f"CUS-{i:06d}",
            "customer_name": f"Fictional Customer {i:06d}",
            "customer_tier": r.choice(
                ["standard", "silver", "gold", "enterprise"]
            ),
            "preferred_language_id": r.choice(languages)["language_id"],
            "created_at": iso(BASE - timedelta(days=r.randint(90, 900)))
        })

    agents = []
    agent_skills = []
    agent_languages = []

    for i in range(1, agent_count + 1):
        aid = f"AGT-{i:06d}"
        start = r.choice([0, 6, 8, 9, 12, 14, 16])

        agents.append({
            "agent_id": aid,
            "agent_name": f"Support Agent {i:03d}",
            "status": "active" if r.random() > 0.05 else "inactive",
            "shift_start_hour_utc": start,
            "shift_end_hour_utc": (start + 8) % 24,
            "concurrency_limit": r.choice([2, 3, 4, 5]),
            "max_daily_tickets": r.choice([15, 20, 25, 30]),
            "effective_from": iso(BASE - timedelta(days=120)),
            "effective_to": ""
        })

        for skill in r.sample(skills, k=r.randint(1, 3)):
            agent_skills.append({
                "agent_id": aid,
                "skill_id": skill["skill_id"],
                "effective_from": iso(BASE - timedelta(days=120)),
                "effective_to": ""
            })

        language_ids = {"LANG-EN"} | set(
            r.sample(
                [x["language_id"] for x in languages
                 if x["language_id"] != "LANG-EN"],
                k=r.randint(0, 2)
            )
        )

        for language_id in language_ids:
            agent_languages.append({
                "agent_id": aid,
                "language_id": language_id,
                "effective_from": iso(BASE - timedelta(days=120)),
                "effective_to": ""
            })

    # ---------------- TICKET GENERATION ----------------

    counts = [1] * ticket_count
    for _ in range(message_count - ticket_count):
        counts[r.randrange(ticket_count)] += 1

    tickets = []
    messages = []
    assignments = []
    slas = []
    resolutions = []
    ticket_events = []
    ground_truth = []

    agent_skill_map = defaultdict(set)
    agent_language_map = defaultdict(set)

    for row in agent_skills:
        agent_skill_map[row["agent_id"]].add(row["skill_id"])

    for row in agent_languages:
        agent_language_map[row["agent_id"]].add(row["language_id"])

    daily_load = defaultdict(int)
    active_agents = [a for a in agents if a["status"] == "active"]

    for i in range(1, ticket_count + 1):
        tid = f"TKT-2026-{i:06d}"
        customer = r.choice(customers)
        channel = r.choice(channels)
        intent = r.choice(intents)
        rule = priorities[int(intent["intent_id"][-3:]) - 1]

        created = BASE - timedelta(
            days=r.randint(0, 89),
            minutes=r.randint(0, 1439)
        )

        language = customer["preferred_language_id"]
        if r.random() < 0.08:
            language = r.choice(languages)["language_id"]

        age_days = (BASE - created).days

        if age_days > 7:
            status = "resolved"
        else:
            status = r.choices(
                ["open", "in_progress", "resolved", "reopened"],
                [0.20, 0.25, 0.50, 0.05]
        )[0]

        # Force known conditions for labelled anomaly examples.
        if i == 2:
            channel = channels[0]
        if i == 3:
            status = "reopened"
        if i == 5:
            intent = intents[5]
            rule = priorities[5]
        # Keep the ticket timeline internally consistent.
        assigned_at = created + timedelta(minutes=r.randint(1, 15))
        first_response_at = assigned_at + timedelta(minutes=r.randint(2, 30))
        resolution_at = first_response_at + timedelta(
            minutes=r.randint(30, 1500)
        )
        reopened_at = resolution_at + timedelta(minutes=r.randint(30, 240))

        if status == "open":
            updated = created + timedelta(minutes=r.randint(1, 10))
        elif status == "in_progress":
            updated = first_response_at
        elif status == "resolved":
            updated = resolution_at
        else:
            updated = reopened_at

        tickets.append({
            "ticket_id": tid,
            "customer_id": customer["customer_id"],
            "channel_id": channel["channel_id"],
            "intent_id": intent["intent_id"],
            "language_id": language,
            "priority": rule["priority"],
            "status": status,
            "created_at": iso(created),
            "updated_at": iso(updated),
            "subject": intent["intent_name"].replace("_", " ").title()
                       + f" request {i:06d}",
            "issue_type": "baseline"
        })

        ticket_events.append({
            "event_id": f"EVT-{tid}-001",
            "ticket_id": tid,
            "event_type": "created",
            "event_at": iso(created),
            "actor_type": "customer",
            "details": "Ticket created"
        })

        # SLA due times respect channel calendars.
        first_due = add_sla_minutes(
            created, rule["first_response_minutes"], channel["calendar_type"]
        )
        resolution_due = add_sla_minutes(
            created, rule["resolution_minutes"], channel["calendar_type"]
        )

        slas.append({
            "sla_id": f"SLA-{tid}",
            "ticket_id": tid,
            "first_response_due_at": iso(first_due),
            "resolution_due_at": iso(resolution_due),
            "calendar_type": channel["calendar_type"],
            "sla_status": "met" if status == "resolved" else "pending",
            "policy_version": "1.0"
        })

        # Find agents with the required skill, language and shift.
        required_skill = "SK-" + intent["required_skill"].upper()
        eligible = []

        for agent in active_agents:
            if required_skill not in agent_skill_map[agent["agent_id"]]:
                continue
            if language not in agent_language_map[agent["agent_id"]]:
                continue
            if not on_shift(agent, assigned_at):
                continue

            day_key = (agent["agent_id"], assigned_at.date())
            if daily_load[day_key] >= int(agent["max_daily_tickets"]):
                continue

            eligible.append(agent)

        selected_agent = None
        if eligible:
            eligible.sort(
                key=lambda a: daily_load[
                    (a["agent_id"], assigned_at.date())
                ]
            )
            selected_agent = eligible[0]
            daily_load[
                (selected_agent["agent_id"], assigned_at.date())
            ] += 1

        if selected_agent:
            assignment_end = (
                resolution_at if status == "resolved"
                else reopened_at if status == "reopened"
                else updated if status == "in_progress"
                else ""
            )

            assignments.append({
                "assignment_id": f"ASN-{tid}-001",
                "ticket_id": tid,
                "agent_id": selected_agent["agent_id"],
                "queue_id": "QUE-" + intent["required_skill"].upper(),
                "assigned_at": iso(assigned_at),
                "ended_at": iso(assignment_end) if assignment_end else "",
                "event_type": "assigned",
                "reason": "skill_language_shift_eligible"
            })

            ticket_events.append({
                "event_id": f"EVT-{tid}-002",
                "ticket_id": tid,
                "event_type": "assigned",
                "event_at": iso(assigned_at),
                "actor_type": "system",
                "details": f"Assigned to {selected_agent['agent_id']}"
            })

        if status in ("in_progress", "resolved", "reopened"):
            ticket_events.append({
                "event_id": f"EVT-{tid}-003",
                "ticket_id": tid,
                "event_type": "first_response",
                "event_at": iso(first_response_at),
                "actor_type": "agent",
                "details": "First agent response"
            })

        if status in ("resolved", "reopened"):
            resolutions.append({
                "resolution_id": f"RES-{i:06d}",
                "ticket_id": tid,
                "resolved_at": iso(resolution_at),
                "resolution_code": r.choice(
                    ["fixed", "guidance_provided", "workaround"]
                ),
                "csat_score": r.randint(1, 5),
                "reopen_count": 1 if status == "reopened" else 0,
                "resolution_notes": "Synthetic resolution record"
            })

            ticket_events.append({
                "event_id": f"EVT-{tid}-004",
                "ticket_id": tid,
                "event_type": "resolved",
                "event_at": iso(resolution_at),
                "actor_type": "agent",
                "details": "Ticket resolved"
            })

        if status == "reopened":
            ticket_events.append({
                "event_id": f"EVT-{tid}-005",
                "ticket_id": tid,
                "event_type": "reopened",
                "event_at": iso(reopened_at),
                "actor_type": "customer",
                "details": "Customer reopened the ticket"
            })

        # Generate messages within the ticket's timeline.
        message_time = created
        for m in range(1, counts[i - 1] + 1):
            if m > 1:
                message_time += timedelta(minutes=r.randint(2, 30))

            # Do not place messages after the ticket's last known update.
            if message_time > updated:
                message_time = updated

            messages.append({
                "message_id": f"MSG-{tid}-{m:03d}",
                "ticket_id": tid,
                "channel_id": channel["channel_id"],
                "sender_type": "customer" if m % 2 else "agent",
                "sent_at": iso(message_time),
                "language_id": language,
                "message_text": f"Synthetic message {m} for {tid}",
                "is_internal": 0
            })

    # ---------------- LABELLED ANOMALIES ----------------
    # Each anomaly is intentional and recorded in ground_truth.csv.

    anomaly_types = [
        "agent_over_capacity",
        "sla_calendar_mismatch",
        "reopened_history_missing",
        "transfer_loop",
        "priority_safety_conflict"
    ]

    for index, issue in enumerate(anomaly_types, start=1):
        if issue == "agent_over_capacity":
            tid = "TKT-2026-000240"
            ticket = next(t for t in tickets if t["ticket_id"] == tid)
        else:
            tid = f"TKT-2026-{index:06d}"
            ticket = tickets[index - 1]

        ticket["issue_type"] = issue

        if issue == "agent_over_capacity":
            # Inject three overlapping tickets for one agent.
            if active_agents:
                agent = active_agents[0]
                assigned_at = "2026-10-12T13:03:00+00:00"

                anomaly_tickets = [
                    next(t for t in tickets if t["ticket_id"] == tid)
                    for tid in [
                        "TKT-2026-000002",
                        "TKT-2026-000240",
                        "TKT-2026-000312"
                    ]
                ]

                for n, anomaly_ticket in enumerate(anomaly_tickets, start=1):
                    anomaly_tid = anomaly_ticket["ticket_id"]

                    assignments.append({
                        "assignment_id": f"ASN-{anomaly_tid}-999",
                        "ticket_id": anomaly_tid,
                        "agent_id": agent["agent_id"],
                        "queue_id": "QUE-GENERAL",
                        "assigned_at": assigned_at,
                        "ended_at": "",
                        "event_type": "assigned",
                        "reason": "ANOMALY_INJECTED_OVER_CAPACITY"
                    })

        elif issue == "sla_calendar_mismatch":
            # Deliberately calculate an email SLA as 24x7.
            sla = next(x for x in slas if x["ticket_id"] == tid)
            sla["calendar_type"] = "24x7"
            sla["first_response_due_at"] = iso(
                datetime.fromisoformat(ticket["created_at"])
                + timedelta(minutes=60)
            )

        elif issue == "reopened_history_missing":
            # Deliberately remove the earlier resolution history.
            resolutions[:] = [
                x for x in resolutions if x["ticket_id"] != tid
            ]

        elif issue == "transfer_loop":
            original_assignment = next(
                (
                    a for a in assignments
                    if a["ticket_id"] == tid
                    and a["event_type"] == "assigned"
                ),
                None
            )

            if original_assignment:
                base_time = (
                    datetime.fromisoformat(original_assignment["assigned_at"])
                    + timedelta(minutes=5)
                )

                for n, queue in enumerate(
                    ["QUE-TECHNICAL", "QUE-GENERAL", "QUE-TECHNICAL"],
                    start=2
                ):
                    assignments.append({
                        "assignment_id": f"ASN-{tid}-{n:03d}",
                        "ticket_id": tid,
                        "agent_id": original_assignment["agent_id"],
                        "queue_id": queue,
                        "assigned_at": iso(base_time + timedelta(minutes=n)),
                        "ended_at": "",
                        "event_type": "transferred",
                        "reason": "ANOMALY_INJECTED_TRANSFER_LOOP"
                    })
        elif issue == "priority_safety_conflict":
            # Security incidents must remain critical.
            ticket["intent_id"] = "INT-006"
            ticket["priority"] = "low"

        ground_truth.append({
            "anomaly_id": f"ANOM-{index:03d}",
            "ticket_id": tid,
            "issue_type": issue,
            "ground_truth": "anomaly",
            "description": {
                "agent_over_capacity":
                    "Agent receives an additional assignment beyond normal capacity.",
                "sla_calendar_mismatch":
                    "Email ticket SLA incorrectly uses a 24x7 calendar.",
                "reopened_history_missing":
                    "Reopened ticket has no earlier resolution record.",
                "transfer_loop":
                    "Ticket transfers repeatedly between two queues.",
                "priority_safety_conflict":
                    "Security incident has low priority instead of critical."
            }[issue]
        })

    # ---------------- EXPORT ----------------

    tables = {
        "customers": customers,
        "channels": channels,
        "tickets": tickets,
        "messages": messages,
        "intents": intents,
        "languages": languages,
        "priority_rules": priorities,
        "agents": agents,
        "skills": skills,
        "queues": queues,
        "assignment_events": assignments,
        "sla_events": slas,
        "resolutions": resolutions,
        "agent_skills": agent_skills,
        "agent_languages": agent_languages,
        "ticket_events": ticket_events,
        "ground_truth": ground_truth
    }

    for name, rows in tables.items():
        write_csv(out / f"{name}.csv", rows, COLUMNS[name])

    manifest = {
        "seed": seed,
        "parameters": {
            "tickets": ticket_count,
            "messages": message_count,
            "agents": agent_count
        },
        "row_counts": {
            name: len(rows) for name, rows in tables.items()
        },
        "provenance": "Synthetic data only; no external or personal data.",
        "anomalies_injected": anomaly_types
    }

    (out / "manifest.json").write_text(
        json.dumps(manifest, indent=2),
        encoding="utf-8"
    )

    return manifest
