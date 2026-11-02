"""Shared settings and helpers for the data generation step."""

import random
import uuid
from datetime import date
from pathlib import Path

# Global seed. Same seed + same code = same CSV files, on any machine.
SEED = 42

# Simulation period (the marketing quarter we analyse).
START_DATE = date(2025, 10, 1)
END_DATE = date(2025, 12, 31)

# raw_data/ is resolved from this file's location, so the scripts work
# no matter which directory they are launched from.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_DATA_DIR = PROJECT_ROOT / "raw_data"

# Countries of the user base and their weight.
COUNTRY_WEIGHTS = {
    "Senegal": 0.20, "Cote d'Ivoire": 0.12, "Mali": 0.10, "Nigeria": 0.10,
    "Ghana": 0.08, "Guinea": 0.07, "Burkina Faso": 0.07, "Benin": 0.05,
    "Togo": 0.05, "Niger": 0.04, "Mauritania": 0.03, "Gambia": 0.03,
    "Guinea-Bissau": 0.02, "Sierra Leone": 0.02, "Liberia": 0.01,
    "Cape Verde": 0.01,
}


def make_rng(seed: int, name: str) -> random.Random:
    """Return an independent random generator for one dataset.

    Each generator gets its own stream derived from the global seed and a
    name ("crm", "ads", "traffic"). Changing the logic of one generator does
    not shift the random numbers drawn by the others.
    """
    return random.Random(f"{seed}-{name}")


def make_uuid(rng: random.Random) -> str:
    """UUID4 built from the seeded generator (uuid.uuid4() is not reproducible)."""
    return str(uuid.UUID(int=rng.getrandbits(128), version=4))


def random_country(rng: random.Random) -> str:
    return rng.choices(list(COUNTRY_WEIGHTS), weights=list(COUNTRY_WEIGHTS.values()))[0]


def save_csv(df, filename: str, out_dir: Path = RAW_DATA_DIR) -> Path:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / filename
    df.to_csv(path, index=False)
    return path
