"""Website traffic: sessions and events (tracking tool) and orders (shop backend).

Two systems record the same activity, as in a real company:
- the tracking tool (GA4, Segment...) sends sessions and events. Later on,
  events go through Kafka in real time;
- the shop backend stores orders. It is the source of truth for revenue.

The two do not match exactly: ad blockers cause some purchase events to be
lost, while the order exists in the backend.

simulate_session() builds one visit. It will be reused by the Kafka producer.
"""

from datetime import datetime, timedelta

import pandas as pd

from generate_ads import daterange
from utils import END_DATE, SEED, START_DATE, make_rng, make_uuid, random_country

# Unpaid traffic per day: search engines (organic) and typed URL / bookmarks (direct).
UNPAID_DAILY_SESSIONS = {"organic": (900, 1300), "direct": (400, 700)}

# Share of ad clicks that turn into a session (slow page, user goes back...).
CLICK_TO_SESSION = (0.85, 0.95)

# Share of sessions coming from a contact known by the CRM. Retargeting
# targets people who already visited, so it brings more known users.
KNOWN_VISITOR_SHARE = {"C3": 0.70, "direct": 0.50}
DEFAULT_KNOWN_SHARE = 0.30
ANONYMOUS_VISITORS_PER_USER = 3   # size of the anonymous visitor pool

# Funnel step probabilities.
PRODUCT_VIEW_RATE = 0.55      # landing -> at least one product page
ADD_TO_CART_RATE = 0.30       # product page -> add to cart
CHECKOUT_RATE = 0.60          # cart -> checkout
# checkout -> purchase, for a logged-in user. Depends on the traffic source.
PURCHASE_RATE = {"C1": 0.65, "C2": 0.55, "C3": 0.75, "C4": 0.25,
                 "organic": 0.60, "direct": 0.70}
CHANNEL_QUALITY = {"google": 1.0, "facebook": 0.9, "instagram": 0.85, "linkedin": 0.5,
                   "organic": 1.0, "direct": 1.0}
PRIOR_CUSTOMER_BOOST = 1.3    # people who already bought buy more easily

TRACKING_LOSS_RATE = 0.05     # purchase events lost (ad blockers)
REFUND_RATE = 0.04

MOBILE_SHARE = {"google": 0.60, "facebook": 0.75, "instagram": 0.90, "linkedin": 0.40,
                "organic": 0.60, "direct": 0.50}

PRODUCTS = [f"p{n:03d}" for n in range(1, 41)]
TIME_FORMAT = "%Y-%m-%d %H:%M:%S"

SESSION_COLUMNS = ["session_id", "visitor_id", "user_id", "started_at", "ended_at",
                   "channel", "campaign_id", "device", "country", "landing_page"]
EVENT_COLUMNS = ["session_id", "visitor_id", "user_id", "event_timestamp",
                 "event_type", "page_url", "order_id", "revenue"]
ORDER_COLUMNS = ["order_id", "user_id", "session_id", "created_at", "amount", "status"]


def simulate_session(rng, day, channel, campaign_id, visitor):
    """Simulate one visit.

    visitor = (visitor_id, user_id, signup_date, prior_customer, country);
    user_id, signup_date and country are None for an anonymous visitor.
    Returns (session, events, order); order is None when nothing was bought.
    """
    visitor_id, crm_user_id, signup_date, prior_customer, country = visitor

    # the user is identified only if logged in, i.e. has an account on that day
    logged_in = signup_date is not None and signup_date <= day
    user_id = crm_user_id if logged_in else None

    session_id = make_uuid(rng)
    device = "mobile" if rng.random() < MOBILE_SHARE[channel] else "desktop"
    country = country or random_country(rng)

    # sessions start before 23:00 so the whole visit stays on the same day
    t = datetime(day.year, day.month, day.day) + timedelta(seconds=rng.randint(0, 23 * 3600 - 1))
    started_at = t

    if campaign_id:
        landing_page = f"/landing/{campaign_id}"
    else:
        landing_page = "/" if channel == "direct" else "/blog"

    events = []

    def add_event(event_type, page_url, min_s, max_s, order_id=None, revenue=None):
        nonlocal t
        events.append((session_id, visitor_id, user_id, t.strftime(TIME_FORMAT),
                       event_type, page_url, order_id, revenue))
        t += timedelta(seconds=rng.randint(min_s, max_s))   # time spent on the page

    add_event("page_view", landing_page, 5, 60)
    order = None

    if rng.random() < PRODUCT_VIEW_RATE:
        viewed = rng.sample(PRODUCTS, rng.randint(1, 3))
        for product in viewed:
            add_event("page_view", f"/products/{product}", 10, 120)

        if rng.random() < ADD_TO_CART_RATE:
            add_event("add_to_cart", f"/products/{viewed[-1]}", 2, 10)

            if rng.random() < CHECKOUT_RATE:
                add_event("begin_checkout", "/checkout", 30, 240)

                rate = PURCHASE_RATE[campaign_id or channel] * CHANNEL_QUALITY[channel]
                if prior_customer:
                    rate *= PRIOR_CUSTOMER_BOOST

                # an account is required to pay
                if logged_in and rng.random() < rate:
                    order_id = f"ORD-{rng.getrandbits(40):010X}"
                    amount = round(min(rng.lognormvariate(4.1, 0.5), 500.0), 2)
                    status = "refunded" if rng.random() < REFUND_RATE else "completed"
                    order = (order_id, user_id, session_id, t.strftime(TIME_FORMAT), amount, status)

                    if rng.random() >= TRACKING_LOSS_RATE:
                        add_event("purchase", "/checkout/confirmation", 5, 30, order_id, amount)

    # the session ends when the visitor leaves the last page
    session = (session_id, visitor_id, user_id, started_at.strftime(TIME_FORMAT),
               t.strftime(TIME_FORMAT), channel, campaign_id, device, country, landing_page)
    return session, events, order


def generate_traffic(df_ads: pd.DataFrame, df_crm: pd.DataFrame, seed: int = SEED):
    rng = make_rng(seed, "traffic")

    # each CRM contact browses with one visitor_id (cookie)
    signup = pd.to_datetime(df_crm["signup_date"]).dt.date
    known_visitors = [
        (make_uuid(rng), uid, None if pd.isna(s) else s, status == "customer", country)
        for uid, s, status, country in zip(df_crm["user_id"], signup,
                                           df_crm["customer_status"], df_crm["country"])
    ]
    anonymous_visitors = [
        (make_uuid(rng), None, None, False, None)
        for _ in range(len(df_crm) * ANONYMOUS_VISITORS_PER_USER)
    ]

    def pick_visitor(source):
        if rng.random() < KNOWN_VISITOR_SHARE.get(source, DEFAULT_KNOWN_SHARE):
            return rng.choice(known_visitors)
        return rng.choice(anonymous_visitors)

    sessions, events, orders = [], [], []

    def run(day, channel, campaign_id):
        session, session_events, order = simulate_session(
            rng, day, channel, campaign_id, pick_visitor(campaign_id or channel))
        sessions.append(session)
        events.extend(session_events)
        if order:
            orders.append(order)

    # paid traffic: sessions come from the ad clicks
    for row in df_ads.itertuples(index=False):
        day = pd.Timestamp(row.date).date()
        for _ in range(int(row.clicks * rng.uniform(*CLICK_TO_SESSION))):
            run(day, row.channel, row.campaign_id)

    # unpaid traffic
    for day in daterange(START_DATE, END_DATE):
        for channel, (low, high) in UNPAID_DAILY_SESSIONS.items():
            for _ in range(rng.randint(low, high)):
                run(day, channel, None)

    # chronological order, as the data would arrive from the tracking tool
    df_sessions = (pd.DataFrame(sessions, columns=SESSION_COLUMNS)
                   .sort_values(["started_at", "session_id"], kind="mergesort")
                   .reset_index(drop=True))
    df_events = (pd.DataFrame(events, columns=EVENT_COLUMNS)
                 .sort_values(["event_timestamp", "session_id"], kind="mergesort")
                 .reset_index(drop=True))
    df_events.insert(0, "event_id", range(1, len(df_events) + 1))
    df_orders = (pd.DataFrame(orders, columns=ORDER_COLUMNS)
                 .sort_values(["created_at", "order_id"], kind="mergesort")
                 .reset_index(drop=True))

    return df_sessions, df_events, df_orders
