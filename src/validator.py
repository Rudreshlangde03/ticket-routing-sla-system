import csv
from pathlib import Path
from src.schema import COLUMNS
from datetime import datetime
def validate(folder=Path("data/generated")):
    folder=Path(folder); errors=[]; data={}; counts={}
    for table,cols in COLUMNS.items():
        path=folder/(table+".csv")
        if not path.exists(): errors.append("Missing "+str(path)); continue
        with path.open(newline="",encoding="utf-8") as f: rows=list(csv.DictReader(f))
        data[table] = rows
        counts[table] = len(rows)

        if not rows:
            errors.append(f"{table}: CSV file is empty")
            continue

        if any(c not in rows[0] for c in cols):
            errors.append(f"{table}: missing columns")
    pk={"customers":"customer_id","channels":"channel_id","tickets":"ticket_id","messages":"message_id","intents":"intent_id","languages":"language_id","priority_rules":"priority_rule_id","agents":"agent_id","skills":"skill_id","queues":"queue_id","assignment_events":"assignment_id","sla_events":"sla_id","resolutions":"resolution_id","ticket_events": "event_id","ground_truth": "anomaly_id",}
    for t,k in pk.items():
        vals=[x[k] for x in data.get(t,[])]
        if len(vals)!=len(set(vals)): errors.append(f"Duplicate primary key: {t}.{k}")
    # Check duplicate agent-skill combinations
    skill_pairs = [
        (row["agent_id"], row["skill_id"])
        for row in data.get("agent_skills", [])
    ]

    if len(skill_pairs) != len(set(skill_pairs)):
        errors.append("Duplicate agent-skill combinations detected")

    # Check duplicate agent-language combinations
    language_pairs = [
        (row["agent_id"], row["language_id"])
        for row in data.get("agent_languages", [])
    ]

    if len(language_pairs) != len(set(language_pairs)):
        errors.append("Duplicate agent-language combinations detected")
    fks=[("customers","preferred_language_id","languages","language_id"),("tickets","customer_id","customers","customer_id"),("tickets","channel_id","channels","channel_id"),("tickets","intent_id","intents","intent_id"),("tickets","language_id","languages","language_id"),("messages","ticket_id","tickets","ticket_id"),("messages","channel_id","channels","channel_id"),("messages","language_id","languages","language_id"),("priority_rules","intent_id","intents","intent_id"),("agent_skills","agent_id","agents","agent_id"),("agent_skills","skill_id","skills","skill_id"),("agent_languages","agent_id","agents","agent_id"),("agent_languages","language_id","languages","language_id"),("assignment_events","ticket_id","tickets","ticket_id"),("assignment_events","agent_id","agents","agent_id"),("assignment_events","queue_id","queues","queue_id"),("sla_events","ticket_id","tickets","ticket_id"),("resolutions","ticket_id","tickets","ticket_id")]
    for child,field,parent,pfield in fks:
        valid={r[pfield] for r in data.get(parent,[])}
        for row in data.get(child,[]):
            if row[field] not in valid: errors.append(f"Invalid FK {child}.{field}: {row[field]}"); break
    # Validate ticket dates
    for ticket in data.get("tickets", []):
        try:
            created = datetime.fromisoformat(ticket["created_at"])
            updated = datetime.fromisoformat(ticket["updated_at"])

            if updated < created:
                errors.append(
                    f"Ticket {ticket['ticket_id']}: "
                    "updated_at is before created_at"
                )

        except (ValueError, TypeError):
            errors.append(
                f"Ticket {ticket['ticket_id']}: invalid date format"
            )
    # Validate ticket lifecycle
    resolution_ids = {
        row["ticket_id"] for row in data.get("resolutions", [])
    }

    event_types = {}
    for event in data.get("ticket_events", []):
        event_types.setdefault(event["ticket_id"], set()).add(
            event["event_type"]
        )

    intentional_anomalies = {
        row["ticket_id"]
        for row in data.get("ground_truth", [])
        if row["issue_type"] == "reopened_history_missing"
    }

    for ticket in data.get("tickets", []):
        ticket_id = ticket["ticket_id"]
        status = ticket["status"]
        events = event_types.get(ticket_id, set())

        if status == "resolved":
            if ticket_id not in resolution_ids:
                errors.append(
                    f"{ticket_id}: resolved ticket has no resolution record"
                )

            if "resolved" not in events:
                errors.append(
                    f"{ticket_id}: missing resolved event"
                )

        elif status == "reopened":
            if "reopened" not in events:
                errors.append(
                    f"{ticket_id}: missing reopened event"
                )

            if ticket_id not in resolution_ids:
                if ticket_id not in intentional_anomalies:
                    errors.append(
                        f"{ticket_id}: reopened ticket has no resolution history"
                    )
    return errors,counts
