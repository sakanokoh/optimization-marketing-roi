# Marketing ROI Data Pipeline

Data engineering project that measures the return on investment of marketing campaigns. It brings together ad platform reports, a CRM, budgets, website tracking and shop orders, and computes revenue and ROI per campaign and per channel.

Planned stack: Python, Pandas, Spark, Airflow, Kafka.

## Status

| Step | Status | Documentation |
| --- | --- | --- |
| Data generation | done | [docs/data_generation.md](docs/data_generation.md) |
| Real-time events with Kafka | to do | |
| Batch processing with Spark | to do | |
| Orchestration with Airflow | to do | |
| ROI analysis | to do | |

## Quick start

```bash
git clone <repo-url>
cd marketing-roi
pip install -r requirements.txt
python src/main.py
```

The raw data is written to `raw_data/`. It is not versioned: the command above rebuilds the same files on any machine.

## Structure

```
docs/       documentation of each step
src/        source code
raw_data/   generated data (ignored by git)
```
