"""CRM: one row per known contact (lead or customer)."""

from datetime import date, timedelta

import pandas as pd

from utils import END_DATE, SEED, START_DATE, make_rng, random_country

# Local name lists instead of Faker: the output no longer depends on the
# Faker version installed, and names match the West African user base.
MALE_FIRST_NAMES = [
    "Mamadou", "Ousmane", "Ibrahima", "Moussa", "Abdoulaye", "Cheikh", "Amadou",
    "Seydou", "Boubacar", "Lamine", "Souleymane", "Modou", "Kwame", "Kofi",
    "Yaw", "Chinedu", "Emeka", "Tunde", "Issa", "Adama", "Karim", "Babacar",
]
FEMALE_FIRST_NAMES = [
    "Aminata", "Fatou", "Awa", "Mariama", "Aissatou", "Khady", "Ndeye", "Binta",
    "Kadiatou", "Rokia", "Oumou", "Ramatoulaye", "Adjoa", "Ama", "Akosua",
    "Ngozi", "Chioma", "Funmilayo", "Salimata", "Hawa", "Coumba", "Astou",
]
LAST_NAMES = [
    "Diallo", "Ndiaye", "Diop", "Fall", "Sow", "Ba", "Sy", "Gueye", "Traore",
    "Keita", "Coulibaly", "Kone", "Toure", "Camara", "Sylla", "Cisse", "Sakho",
    "Kante", "Ouedraogo", "Sawadogo", "Mensah", "Owusu", "Boateng", "Okafor",
    "Adeyemi", "Balde", "Barry", "Bah", "Sane", "Dembele", "Sanogo", "Kaba",
]

SIGNUP_RATE = 0.70           # contacts who created an account
PRIOR_CUSTOMER_RATE = 0.35   # accounts created before the quarter that already bought

# The CRM holds history: accounts exist since 2024.
SIGNUP_START = date(2024, 1, 1)


def random_date(rng, start: date, end: date) -> date:
    return start + timedelta(days=rng.randint(0, (end - start).days))


def generate_crm(n_users: int = 20000, seed: int = SEED) -> pd.DataFrame:
    """CRM before the quarter. customer_status is updated later from the orders."""
    rng = make_rng(seed, "crm")

    users = []
    for i in range(n_users):
        gender = rng.choice(["M", "F"])
        first_name = rng.choice(MALE_FIRST_NAMES if gender == "M" else FEMALE_FIRST_NAMES)
        last_name = rng.choice(LAST_NAMES)

        signup_date = None
        if rng.random() < SIGNUP_RATE:
            signup_date = random_date(rng, SIGNUP_START, END_DATE)

        prior_customer = (signup_date is not None and signup_date < START_DATE
                          and rng.random() < PRIOR_CUSTOMER_RATE)

        users.append({
            "user_id": f"U{i + 1:06d}",
            "first_name": first_name,
            "last_name": last_name,
            # the index keeps emails unique even when two users share a name
            "email": f"{first_name.lower()}.{last_name.lower()}{i + 1}@example.com",
            "signup_date": signup_date,
            "country": random_country(rng),
            "gender": gender,
            "customer_status": "customer" if prior_customer else "lead",
        })

    return pd.DataFrame(users)


def update_customer_status(df_crm: pd.DataFrame, df_orders: pd.DataFrame) -> pd.DataFrame:
    """A lead who placed a completed order during the quarter becomes a customer."""
    buyers = set(df_orders.loc[df_orders["status"] == "completed", "user_id"])
    df = df_crm.copy()
    df.loc[df["user_id"].isin(buyers), "customer_status"] = "customer"
    return df
