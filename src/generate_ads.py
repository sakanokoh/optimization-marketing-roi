"""Ad platform reports (daily, per campaign and channel) and planned budgets."""

import math
from datetime import date, timedelta

import pandas as pd

from utils import END_DATE, SEED, START_DATE, make_rng

# Each campaign has its own flight dates and its own channel mix.
CAMPAIGNS = {
    "C1": {"name": "Winter Sale", "start": date(2025, 12, 1), "end": date(2025, 12, 31),
           "channels": ["google", "facebook", "instagram"]},
    "C2": {"name": "New Product", "start": date(2025, 10, 15), "end": END_DATE,
           "channels": ["google", "facebook", "instagram", "linkedin"]},
    "C3": {"name": "Retargeting", "start": START_DATE, "end": END_DATE,
           "channels": ["google", "facebook"]},
    "C4": {"name": "Brand Awareness", "start": START_DATE, "end": date(2025, 11, 30),
           "channels": ["facebook", "instagram", "linkedin"]},
}

# Per channel: average daily impressions, CTR range (share of impressions
# that get a click) and CPM in EUR (cost per 1000 impressions).
CHANNELS = {
    "google":    {"daily_impressions": 27000, "ctr": (0.020, 0.040), "cpm": 14.0},
    "facebook":  {"daily_impressions": 21000, "ctr": (0.010, 0.025), "cpm": 10.0},
    "instagram": {"daily_impressions": 18000, "ctr": (0.015, 0.035), "cpm": 12.0},
    "linkedin":  {"daily_impressions": 7500,  "ctr": (0.005, 0.015), "cpm": 35.0},
}

WEEKEND_FACTOR = 0.8          # less traffic on Saturdays and Sundays
BUDGET_MARGIN = (1.00, 1.20)  # planned budget = actual spend x margin


def daterange(start: date, end: date):
    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)


def generate_ads(seed: int = SEED):
    rng = make_rng(seed, "ads")
    ads = []
    budget = []

    for campaign_id, campaign in CAMPAIGNS.items():
        for channel in campaign["channels"]:
            params = CHANNELS[channel]
            spend = 0.0

            for day in daterange(campaign["start"], campaign["end"]):
                volume = params["daily_impressions"] * rng.uniform(0.7, 1.3)
                if day.weekday() >= 5:
                    volume *= WEEKEND_FACTOR
                impressions = int(volume)

                clicks = int(impressions * rng.uniform(*params["ctr"]))
                cost = round(impressions / 1000 * params["cpm"] * rng.uniform(0.9, 1.1), 2)
                spend += cost

                ads.append({
                    "campaign_id": campaign_id,
                    "campaign_name": campaign["name"],
                    "channel": channel,
                    "date": day,
                    "impressions": impressions,
                    "clicks": clicks,
                    "cost": cost,
                })

            # Budget is decided upfront; we derive it from the spend so the
            # two stay consistent, and round it up to the next 100 EUR.
            planned = spend * rng.uniform(*BUDGET_MARGIN)
            budget.append({
                "campaign_id": campaign_id,
                "channel": channel,
                "total_budget": float(math.ceil(planned / 100) * 100),
            })

    return pd.DataFrame(ads), pd.DataFrame(budget)
