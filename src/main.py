"""Generate all raw datasets in one run.

    python src/main.py
    python src/main.py --seed 7 --users 50000 --output /tmp/test_data
"""

import argparse

from generate_ads import generate_ads
from generate_crm import generate_crm, update_customer_status
from generate_traffic import generate_traffic
from utils import RAW_DATA_DIR, SEED, save_csv


def main():
    parser = argparse.ArgumentParser(description="Generate the marketing raw datasets.")
    parser.add_argument("--seed", type=int, default=SEED,
                        help="random seed; same seed = same files (default: %(default)s)")
    parser.add_argument("--users", type=int, default=20000,
                        help="number of CRM contacts (default: %(default)s)")
    parser.add_argument("--output", default=RAW_DATA_DIR,
                        help="output folder (default: raw_data/)")
    args = parser.parse_args()

    # order matters: traffic needs the ads (clicks) and the CRM (visitors),
    # and the CRM status is updated from the orders at the end
    df_crm = generate_crm(n_users=args.users, seed=args.seed)
    df_ads, df_budget = generate_ads(seed=args.seed)
    df_sessions, df_events, df_orders = generate_traffic(df_ads, df_crm, seed=args.seed)
    df_crm = update_customer_status(df_crm, df_orders)

    for df, name in [(df_crm, "crm.csv"), (df_ads, "ads.csv"), (df_budget, "budget.csv"),
                     (df_sessions, "sessions.csv"), (df_events, "events.csv"),
                     (df_orders, "orders.csv")]:
        path = save_csv(df, name, args.output)
        print(f"{name:<13} {len(df):>9} rows -> {path}")


if __name__ == "__main__":
    main()
