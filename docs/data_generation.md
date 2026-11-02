# Data generation

The pipeline needs input data that looks like what a marketing team actually works with. Since no real data is available, it is simulated. Each file mimics the export of a real system:

| File | Source system | Content |
| --- | --- | --- |
| `crm.csv` | CRM (HubSpot, Salesforce...) | known contacts, leads and customers |
| `ads.csv` | ad platforms (Google Ads, Meta Ads, LinkedIn Ads) | daily impressions, clicks and cost |
| `budget.csv` | marketing finance | planned budget per campaign and channel |
| `sessions.csv` | web tracking tool (GA4, Segment...) | one row per website visit, with its traffic source |
| `events.csv` | web tracking tool | one row per action during a visit; streamed through Kafka later |
| `orders.csv` | shop backend database | orders and refunds; the source of truth for revenue |

The files share keys (`campaign_id`, `channel`, `user_id`, `session_id`, `order_id`), so they can be joined to measure the revenue and ROI of each campaign and channel.

## Run it

```bash
pip install -r requirements.txt
python src/main.py
```

The six files are written to `raw_data/`, replacing any previous version. With the default settings this takes about 25 seconds and produces around 200 MB, mostly `events.csv`.

`raw_data/` is listed in `.gitignore`: the files are not committed (`events.csv` is above GitHub's 100 MB limit) and anyone can rebuild them with the command above.

### Options

| Option | Default | Effect |
| --- | --- | --- |
| `--seed` | 42 | starting point of the random generator; same seed, same files |
| `--users` | 20000 | number of CRM contacts; traffic coming from known users grows with it |
| `--output` | `raw_data/` | folder where the files are written |

Example: `python src/main.py --users 5000 --output test_data` builds a smaller dataset in `test_data/`, handy for quick tests.

## Reproducibility

With the same seed and options, the script produces byte-identical files on any machine:

- each generator draws from its own `random.Random` instance, seeded from the global seed and the dataset name (`"42-crm"`, `"42-ads"`, `"42-traffic"`). Editing one generator does not change the output of the others;
- ids (sessions, visitors, orders) come from the seeded generator, never from `uuid.uuid4()`;
- names come from fixed lists in `generate_crm.py` rather than Faker, whose output changes between versions;
- output paths are resolved from the script location, not from the current directory.

To check: generate twice and compare with `sha256sum raw_data/*`.

## Structure

```
src/
  utils.py              seed, period, paths, countries, helpers
  generate_crm.py       crm.csv
  generate_ads.py       ads.csv, budget.csv
  generate_traffic.py   sessions.csv, events.csv, orders.csv
  main.py               runs everything in the right order
raw_data/               generated files (not versioned)
```

Generation order: CRM, then ads, then traffic (which needs the ad clicks and the CRM contacts), then an update of `customer_status` in the CRM from the orders.

Simulated period: Q4 2025 (2025-10-01 to 2025-12-31).

## Datasets

### crm.csv

| Column | Description |
| --- | --- |
| user_id | `U000001`, ... |
| first_name, last_name | from West African name lists, first name consistent with gender |
| email | `first.last<n>@example.com`, unique |
| signup_date | account creation date; empty for a contact without an account (newsletter, form) |
| country | 16 West African countries, weighted (Senegal 20 %, Côte d'Ivoire 12 %, ...) |
| gender | `M` or `F` |
| customer_status | `lead` or `customer`, as of the end of the quarter |

- 70 % of contacts have an account, created between 2024-01-01 and 2025-12-31.
- 35 % of the accounts created before the quarter already belong to customers.
- A lead who places a completed order during the quarter becomes a customer.

### ads.csv

One row per campaign, channel and day, as reported by the ad platforms.

| Column | Description |
| --- | --- |
| campaign_id, campaign_name | `C1` to `C4` |
| channel | `google`, `facebook`, `instagram`, `linkedin` |
| date | day |
| impressions | times the ad was shown |
| clicks | clicks on the ad |
| cost | amount spent that day, EUR |

| Campaign | Dates | Channels |
| --- | --- | --- |
| C1 Winter Sale | Dec 1 - Dec 31 | google, facebook, instagram |
| C2 New Product | Oct 15 - Dec 31 | all four |
| C3 Retargeting | Oct 1 - Dec 31 | google, facebook |
| C4 Brand Awareness | Oct 1 - Nov 30 | facebook, instagram, linkedin |

| Channel | Daily impressions (avg) | CTR | CPM (EUR) |
| --- | --- | --- | --- |
| google | 27,000 | 2.0 - 4.0 % | 14 |
| facebook | 21,000 | 1.0 - 2.5 % | 10 |
| instagram | 18,000 | 1.5 - 3.5 % | 12 |
| linkedin | 7,500 | 0.5 - 1.5 % | 35 |

Impressions vary by ±30 % from day to day and drop by 20 % on weekends. `clicks = impressions × CTR`, `cost = impressions / 1000 × CPM` (±10 %).

### budget.csv

| Column | Description |
| --- | --- |
| campaign_id, channel | campaign and channel |
| total_budget | budget planned for the whole campaign, EUR |

Planned budget = real spend × 1.00 to 1.20, rounded up to the next 100 EUR. Spend never exceeds it.

### sessions.csv

One row per visit.

| Column | Description |
| --- | --- |
| session_id | visit id |
| visitor_id | cookie id of the browser; the same person keeps the same visitor_id |
| user_id | filled only if the visitor is logged in |
| started_at, ended_at | first event, time the visitor left the last page |
| channel | `google`, `facebook`, `instagram`, `linkedin` (paid), `organic`, `direct` (unpaid) |
| campaign_id | campaign of the ad clicked, empty for unpaid traffic |
| device | `mobile` or `desktop` |
| country | user's country if known, otherwise drawn at random |
| landing_page | `/landing/<campaign>`, `/blog` (organic) or `/` (direct) |

Where sessions come from:

- **paid**: 85 to 95 % of the ad clicks of the day become a session. The rest are lost (page too slow, user going back), as in real life, where ad platform clicks and website sessions never match exactly;
- **unpaid**: 900 to 1,300 organic and 400 to 700 direct sessions per day.

Who visits:

- 30 % of sessions come from a CRM contact (70 % for C3 Retargeting, 50 % for direct traffic), the rest from anonymous visitors;
- a CRM contact is identified (`user_id` filled) only if they already have an account that day;
- device depends on the channel: 90 % mobile on instagram, 40 % on linkedin.

### events.csv

One row per action, in chronological order.

| Column | Description |
| --- | --- |
| event_id | sequential, follows time order |
| session_id, visitor_id, user_id | same values as the session |
| event_timestamp | `YYYY-MM-DD HH:MM:SS` |
| event_type | `page_view`, `add_to_cart`, `begin_checkout`, `purchase` |
| page_url | page where the event happened |
| order_id, revenue | only on `purchase` events |

Journey of a session:

1. `page_view` of the landing page;
2. 55 % go on to view 1 to 3 product pages (`/products/p001` to `p040`);
3. 30 % of them add a product to the cart;
4. 60 % of those start the checkout;
5. a logged-in visitor then buys with a probability that depends on the source: C3 75 %, C1 65 %, C2 55 %, C4 25 %, organic 60 %, direct 70 %. It is lowered on some channels (linkedin × 0.5, instagram × 0.85, facebook × 0.9) and raised by 30 % for someone who already bought before. Anonymous visitors cannot pay: an account is required.

Each page adds a few seconds to minutes to the clock, so events of a session are always in order.

### orders.csv

| Column | Description |
| --- | --- |
| order_id | `ORD-` + 10 hex characters |
| user_id | buyer, always a logged-in CRM user |
| session_id | session in which the order was placed |
| created_at | order time |
| amount | EUR, median around 60, capped at 500 |
| status | `completed` or `refunded` (4 %) |

5 % of orders have no `purchase` event in `events.csv`: the tracking script was blocked (ad blocker) but the order went through. Revenue measured from events is therefore slightly lower than revenue in the backend, a gap that the pipeline has to handle.

## Consistency rules

True for every generated dataset; they can be reused as data quality tests in the pipeline:

- every event belongs to an existing session and carries the same `user_id` as the session;
- events of a session lie between `started_at` and `ended_at`;
- every order belongs to a session that went through `begin_checkout`;
- every `purchase` event points to an existing order;
- every order is placed by a logged-in user, on or after their signup date;
- every user with a completed order is a `customer` in the CRM;
- paid sessions per campaign, channel and day never exceed the ad clicks;
- the spend never exceeds the planned budget;
- nothing falls outside 2025-10-01 / 2025-12-31.

## Result with the default settings

| File | Rows |
| --- | --- |
| crm.csv | 20,000 |
| ads.csv | 772 |
| budget.csv | 12 |
| sessions.csv | 443,743 |
| events.csv | 1,055,451 |
| orders.csv | 7,970 |

- 1.8 % of sessions end with an order.
- Ad spend: 196,000 EUR. Revenue from completed orders: 520,000 EUR, a third of it from unpaid traffic.
- ROI is very uneven: C3 Retargeting returns more than 3 times its cost on Google, C1 and C2 are slightly profitable, LinkedIn and C4 Brand Awareness lose money.
- 359 orders (about 24,000 EUR) are missing from the tracked events.

## Next step: streaming the events

`events.csv` is the history. In real time, a Kafka producer reuses `simulate_session()` from `generate_traffic.py` and sends each event as a message, with the same fields as the CSV. Batch and streaming then share one schema.
