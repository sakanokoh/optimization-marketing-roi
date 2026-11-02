# Marketing ROI Data Pipeline

This project measures the return on investment of marketing campaigns. It brings together ad performance, budgets, CRM contacts, website activity and orders, then computes the revenue and ROI of each campaign and channel.

## Data

The project works on six sources that share common keys (`campaign_id`, `channel`, `user_id`, `session_id`, `order_id`):

| File | Content |
| --- | --- |
| `crm.csv` | contacts, leads and customers |
| `ads.csv` | daily impressions, clicks and cost per campaign and channel |
| `budget.csv` | planned budget per campaign and channel |
| `sessions.csv` | website visits and their traffic source |
| `events.csv` | user actions during each visit |
| `orders.csv` | orders and refunds |

The data is simulated and reproducible. How it is built is described in [docs/data_generation.md](docs/data_generation.md).

## Getting started

Requires Python 3.10 or later.

```bash
git clone https://github.com/sakanokoh/optimization-marketing-roi.git
cd marketing-roi
pip install -r requirements.txt
python src/main.py
```

The files are written to `raw_data/` (about 200 MB, around 25 seconds). This folder is not versioned: the command rebuilds exactly the same files on any machine.

Options:

| Option | Default | Effect |
| --- | --- | --- |
| `--seed` | 42 | seed of the random generator; same seed, same files |
| `--users` | 20000 | number of CRM contacts |
| `--output` | `raw_data/` | output folder |

For a lighter dataset during development:

```bash
python src/main.py --users 5000 --output test_data
```

## Project structure

```
docs/       documentation
src/        source code
raw_data/   generated data, not versioned
```
