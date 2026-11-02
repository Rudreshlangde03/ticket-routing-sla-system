
import csv
import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path

DATA_DIR = Path("data/generated")


def read_csv(filename):
    with (DATA_DIR / filename).open(
        "r", newline="", encoding="utf-8"
    ) as file:
        return list(csv.DictReader(file))


def write_csv(filename, rows):
    if not rows:
        return

    with (DATA_DIR / filename).open(
        "w", newline="", encoding="utf-8"
    ) as file:
        writer = csv.DictWriter(file, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)


def is_on_shift(agent, ticket_time):
    hour = ticket_time.hour
    start = int(agent["shift_start_hour_utc"])
    end = int(agent["shift_end_hour_utc"])

    if start < end:
        return start <= hour < end

    return hour >= start or hour < end

def get_active_intervals(ticket, events):
    start = datetime.fromisoformat(ticket["created_at"])
    intervals = []
    is_active = True

    for event in events:
        event_time = datetime.fromisoformat(event["event_at"])

        if event_time <= start:
            continue

        if event["event_type"] == "resolved" and is_active:
            intervals.append((start, event_time))
            is_active = False

        elif event["event_type"] == "reopened" and not is_active:
            start = event_time
            is_active = True

    if is_active:
        intervals.append((start, None))

    return intervals


def route_tickets():
    tickets = read_csv("tickets.csv")
    agents = read_csv("agents.csv")
    intents = read_csv("intents.csv")
    agent_skills = read_csv("agent_skills.csv")
    agent_languages = read_csv("agent_languages.csv")
    ticket_events = read_csv("ticket_events.csv")

    # Build agent skill and language lookup tables.
    skills_by_agent = defaultdict(set)
    languages_by_agent = defaultdict(set)

    for row in agent_skills:
        skills_by_agent[row["agent_id"]].add(row["skill_id"])

    for row in agent_languages:
        languages_by_agent[row["agent_id"]].add(row["language_id"])

    # Map each intent to its required skill.
    intent_skill = {
        row["intent_id"]: "SK-" + row["required_skill"].upper()
        for row in intents
    }

     # Track agent workload.
    active_load = defaultdict(int)
    daily_load = defaultdict(int)

    # Store ticket lifecycle events in chronological order.
    events_by_ticket = defaultdict(list)

    for event in ticket_events:
        events_by_ticket[event["ticket_id"]].append(event)

    for ticket_id in events_by_ticket:
        events_by_ticket[ticket_id].sort(
            key=lambda event: event["event_at"]
        )
        # Store active time intervals for each assigned agent.
    active_intervals_by_agent = defaultdict(list)
    results = []

    # Process tickets in chronological order.
    tickets.sort(key=lambda t: t["created_at"])

    active_statuses = {"open", "in_progress", "reopened"}
    rejection_counts = defaultdict(int)

    for ticket in tickets:
        ticket_time = datetime.fromisoformat(ticket["created_at"])
        required_skill = intent_skill[ticket["intent_id"]]

        eligible_agents = []

        for agent in agents:
            aid = agent["agent_id"]

            if agent["status"] != "active":
                rejection_counts["inactive"] += 1
                continue

            if required_skill not in skills_by_agent[aid]:
                rejection_counts["skill_mismatch"] += 1
                continue

            if ticket["language_id"] not in languages_by_agent[aid]:
                rejection_counts["language_mismatch"] += 1
                continue

            if not is_on_shift(agent, ticket_time):
                rejection_counts["off_shift"] += 1
                continue

            current_active_load = sum(
                1
                for start, end in active_intervals_by_agent[aid]
                if start <= ticket_time and (end is None or ticket_time < end)
            )

            if current_active_load >= int(agent["concurrency_limit"]):
                rejection_counts["capacity_limit"] += 1
                continue

            date_key = (aid, ticket_time.date())

            if daily_load[date_key] >= int(agent["max_daily_tickets"]):
                rejection_counts["daily_limit"] += 1
                continue

            eligible_agents.append(agent)

        if not eligible_agents:
            results.append({
                "ticket_id": ticket["ticket_id"],
                "agent_id": "",
                "queue_id": "QUE-" + required_skill[3:],
                "assigned_at": ticket["created_at"],
                "assignment_status": "unassigned",
                "reason": "No agent met all eligibility conditions"
            })
            continue

        # Select the agent with the lowest current workload.
        selected = min(
            eligible_agents,
            key=lambda a: (
                sum(
                    1
                    for start, end in active_intervals_by_agent[a["agent_id"]]
                    if start <= ticket_time and (end is None or ticket_time < end)
                ),
                daily_load[(a["agent_id"], ticket_time.date())]
            )
        )

        aid = selected["agent_id"]

        active_intervals_by_agent[aid].extend(
            get_active_intervals(
                ticket,
                events_by_ticket.get(ticket["ticket_id"], [])
            )
        )

        daily_load[(aid, ticket_time.date())] += 1

        results.append({
            "ticket_id": ticket["ticket_id"],
            "agent_id": aid,
            "queue_id": "QUE-" + required_skill[3:],
            "assigned_at": ticket["created_at"],
            "assignment_status": "assigned",
            "reason": "Skill, language, shift and capacity matched"
        })

    write_csv("routing_results.csv", results)

    assigned = sum(
        1 for row in results
        if row["assignment_status"] == "assigned"
    )

    unassigned = len(results) - assigned

    summary = {
        "total_tickets": len(results),
        "assigned_tickets": assigned,
        "unassigned_tickets": unassigned,
        "assignment_rate_percent": round(
            assigned / len(results) * 100, 2
        ) if results else 0
    }

    (DATA_DIR / "routing_summary.json").write_text(
        json.dumps(summary, indent=4),
        encoding="utf-8"
    )

    print("Agent rejection breakdown:")
    print(json.dumps(dict(rejection_counts), indent=4))
    print("Ticket routing completed!")
    print(json.dumps(summary, indent=4))


if __name__ == "__main__":
    route_tickets()
