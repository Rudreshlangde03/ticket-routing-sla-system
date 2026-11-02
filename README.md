# Ticket Routing \& SLA Management System

A Python-based synthetic-data and ticket-routing system developed for the YottaFlex AI candidate project.

## Requirements

* Python 3.10+
* Uses Python standard library; no external services required.

## Installation and Execution

Generate a sample dataset:

```bash
python main.py generate --tickets 500 --messages 1500 --agents 100 --seed 20261022
```

Validate the generated dataset:

```bash
python main.py validate
```

Run the ticket-routing engine:

```bash
python src/routing.py
```

\## SQLite Database



The project creates a relational SQLite database at:



`data/generated/tickets.db`



The database contains 17 tables with primary-key and foreign-key constraints.



To create or rebuild the database:



```bash

python main.py database

## Full Baseline Dataset

Generate the required baseline dataset:

```bash
python main.py generate --tickets 30000 --messages 100000 --agents 100 --seed 20261022
python main.py validate
```

## Implemented Features

* Deterministic synthetic data generation using a fixed random seed.
* Linked records for customers, tickets, messages, agents, skills and languages.
* Ticket lifecycle event tracking, including resolution and reopening.
* SLA event generation with channel-based calendar logic.
* Ticket routing based on agent skills, language, shift and capacity.
* Agent workload balancing and concurrency-limit checks.
* Injection of five labelled data anomalies.
* Ground-truth anomaly records.
* Dataset validation and generation manifest.

## Routing Output

The routing engine generates:

* `routing\_results.csv`
* `routing\_summary.json`

## Generated Data

All generated CSV files and the generation manifest are stored in:

```text
data/generated/
```

## Data and Reproducibility

The project uses synthetic data only. A fixed seed ensures reproducible data generation. No external or personal customer data is used.

## Current Limitations

* The routing engine is a simulation using generated ticket lifecycle events.
* The project does not currently include a hosted production service or dashboard.
* Analytics and dashboard functionality remain future enhancements.

