import csv
import random
import sqlite3
from datetime import date
from pathlib import Path

import numpy as np


# --------------------------------------------------
# Project configuration
# --------------------------------------------------

SEED = 42
N_USERS = 1000
YEAR = 2023

PROJECT_ROOT = Path(__file__).resolve().parent.parent

RAW_FILE = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "MyTransaction.csv"
)

VALIDATION_DIR = (
    PROJECT_ROOT
    / "data"
    / "validation"
)

DATABASE_FILE = (
    PROJECT_ROOT
    / "database"
    / "finpulse.db"
)


# --------------------------------------------------
# Random generators
# --------------------------------------------------

rng = np.random.default_rng(SEED)
random.seed(SEED)


# --------------------------------------------------
# Synthetic behavioral profiles
# --------------------------------------------------

PROFILE_PROBS = [
    ("profile_A", 0.30),
    ("profile_B", 0.27),
    ("profile_C", 0.21),
    ("profile_D", 0.22),
]


PROFILE_CFG = {

    "profile_A": {
        "income_vol": (0.015, 0.055),
        "essentials": (0.27, 0.39),
        "desire": (0.07, 0.19),
        "repayment": (0.00, 0.16),
        "investment": (0.10, 0.24),
        "others": (0.015, 0.055),
    },

    "profile_B": {
        "income_vol": (0.025, 0.075),
        "essentials": (0.30, 0.43),
        "desire": (0.25, 0.43),
        "repayment": (0.03, 0.18),
        "investment": (0.00, 0.06),
        "others": (0.025, 0.075),
    },

    "profile_C": {
        "income_vol": (0.030, 0.085),
        "essentials": (0.29, 0.41),
        "desire": (0.08, 0.21),
        "repayment": (0.28, 0.50),
        "investment": (0.00, 0.035),
        "others": (0.02, 0.07),
    },

    "profile_D": {
        "income_vol": (0.16, 0.34),
        "essentials": (0.30, 0.43),
        "desire": (0.10, 0.25),
        "repayment": (0.02, 0.18),
        "investment": (0.00, 0.09),
        "others": (0.025, 0.08),
    },
}


INCOME_BANDS = [
    (22000, 35000, 0.34),
    (35000, 50000, 0.31),
    (50000, 75000, 0.22),
    (75000, 120000, 0.13),
]


# --------------------------------------------------
# Helpers
# --------------------------------------------------

def weighted_choice(items):

    names = [
        item[0]
        for item in items
    ]

    probabilities = np.array(
        [
            item[1]
            for item in items
        ],
        dtype=float
    )

    probabilities /= probabilities.sum()

    return str(
        rng.choice(
            names,
            p=probabilities
        )
    )


def month_days(year, month):

    if month == 12:
        return (
            date(year + 1, 1, 1)
            - date(year, 12, 1)
        ).days

    return (
        date(year, month + 1, 1)
        - date(year, month, 1)
    ).days


def random_date(year, month):

    day = int(
        rng.integers(
            1,
            month_days(year, month) + 1
        )
    )

    return date(
        year,
        month,
        day
    ).isoformat()


def split_amount(
    total,
    n,
    minimum=20.0
):

    total = max(
        float(total),
        0.0
    )

    if n <= 0 or total < minimum:
        return []

    n = max(
        1,
        min(
            n,
            int(total // minimum)
        )
    )

    weights = rng.dirichlet(
        np.ones(n) * 1.8
    )

    values = np.round(
        total * weights,
        2
    )

    values[-1] = round(
        total
        - float(values[:-1].sum()),
        2
    )

    return [
        float(max(value, 0.01))
        for value in values
    ]


def source_salary_median(path):

    values = []

    with open(
        path,
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as file:

        reader = csv.DictReader(file)

        for row in reader:

            if (
                row.get("Category") or ""
            ).strip() != "Salary":
                continue

            try:
                value = float(
                    row.get("Deposit") or 0
                )
            except ValueError:
                continue

            if value > 0:
                values.append(value)

    if values:
        return float(
            np.median(values)
        )

    return 34800.0


def choose_income(anchor):

    random_value = rng.random()

    cumulative_probability = 0.0

    for low, high, probability in INCOME_BANDS:

        cumulative_probability += probability

        if random_value <= cumulative_probability:

            mode = min(
                max(anchor, low),
                high
            )

            return float(
                rng.triangular(
                    low,
                    mode,
                    high
                )
            )

    return float(
        rng.uniform(
            75000,
            120000
        )
    )


def write_csv(
    path,
    rows,
    fields
):

    with open(
        path,
        "w",
        encoding="utf-8",
        newline=""
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=fields
        )

        writer.writeheader()
        writer.writerows(rows)


# --------------------------------------------------
# Database writer
# --------------------------------------------------

def build_database(
    users,
    transactions
):

    DATABASE_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    if DATABASE_FILE.exists():
        DATABASE_FILE.unlink()

    with sqlite3.connect(
        DATABASE_FILE
    ) as conn:

        conn.execute(
            """
            CREATE TABLE users (
                user_id TEXT PRIMARY KEY,
                base_monthly_income REAL NOT NULL
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE transactions (
                transaction_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                date TEXT NOT NULL,
                amount REAL NOT NULL,
                txn_type TEXT NOT NULL,
                label TEXT NOT NULL,
                FOREIGN KEY(user_id)
                    REFERENCES users(user_id)
            )
            """
        )

        conn.executemany(
            """
            INSERT INTO users (
                user_id,
                base_monthly_income
            )
            VALUES (?, ?)
            """,
            [
                (
                    user["user_id"],
                    user["base_monthly_income"]
                )
                for user in users
            ]
        )

        conn.executemany(
            """
            INSERT INTO transactions (
                transaction_id,
                user_id,
                date,
                amount,
                txn_type,
                label
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    row["transaction_id"],
                    row["user_id"],
                    row["date"],
                    row["amount"],
                    row["txn_type"],
                    row["label"],
                )
                for row in transactions
            ]
        )

        conn.execute(
            """
            CREATE INDEX
            idx_transactions_user_date
            ON transactions(
                user_id,
                date
            )
            """
        )

        conn.execute(
            """
            CREATE INDEX
            idx_transactions_label
            ON transactions(label)
            """
        )

        conn.commit()


# --------------------------------------------------
# Main generation
# --------------------------------------------------

def main():

    VALIDATION_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    anchor = source_salary_median(
        RAW_FILE
    )

    users = []
    audit = []
    transactions = []
    monthly_validation = []

    transaction_id = 1

    # --------------------------------------------------
    # Generate users
    # --------------------------------------------------

    for user_number in range(
        1,
        N_USERS + 1
    ):

        user_id = (
            f"U{user_number:04d}"
        )

        profile = weighted_choice(
            PROFILE_PROBS
        )

        config = PROFILE_CFG[
            profile
        ]

        base_income = choose_income(
            anchor
        )

        parameters = {

            "essential_ratio":
                float(
                    rng.uniform(
                        *config["essentials"]
                    )
                ),

            "desire_ratio":
                float(
                    rng.uniform(
                        *config["desire"]
                    )
                ),

            "repayment_ratio":
                float(
                    rng.uniform(
                        *config["repayment"]
                    )
                ),

            "investment_ratio":
                float(
                    rng.uniform(
                        *config["investment"]
                    )
                ),

            "other_ratio":
                float(
                    rng.uniform(
                        *config["others"]
                    )
                ),

            "income_volatility":
                float(
                    rng.uniform(
                        *config["income_vol"]
                    )
                ),
        }

        users.append({
            "user_id": user_id,
            "base_monthly_income":
                round(base_income, 2)
        })

        audit.append({

            "user_id": user_id,

            "generation_profile":
                profile,

            "base_monthly_income":
                round(base_income, 2),

            **{
                key: round(value, 4)
                for key, value
                in parameters.items()
            }
        })

        # --------------------------------------------------
        # Generate monthly behavior
        # --------------------------------------------------

        for month in range(
            1,
            13
        ):

            income_factor = max(
                0.45,
                rng.normal(
                    1.0,
                    parameters[
                        "income_volatility"
                    ]
                )
            )

            if (
                profile == "profile_D"
                and rng.random() < 0.18
            ):
                income_factor *= float(
                    rng.uniform(
                        0.65,
                        1.35
                    )
                )

            income = max(
                8000.0,
                base_income
                * income_factor
            )

            essential_ratio = max(
                0.18,
                parameters[
                    "essential_ratio"
                ]
                * rng.normal(
                    1,
                    0.08
                )
            )

            desire_ratio = max(
                0.0,
                parameters[
                    "desire_ratio"
                ]
                * rng.normal(
                    1,
                    0.15
                )
            )

            repayment_ratio = max(
                0.0,
                parameters[
                    "repayment_ratio"
                ]
                * rng.normal(
                    1,
                    0.08
                )
            )

            investment_ratio = max(
                0.0,
                parameters[
                    "investment_ratio"
                ]
                * rng.normal(
                    1,
                    0.18
                )
            )

            other_ratio = max(
                0.0,
                parameters[
                    "other_ratio"
                ]
                * rng.normal(
                    1,
                    0.25
                )
            )

            if rng.random() < 0.07:
                desire_ratio *= float(
                    rng.uniform(
                        1.15,
                        1.60
                    )
                )

            if rng.random() < 0.04:
                other_ratio += float(
                    rng.uniform(
                        0.05,
                        0.14
                    )
                )

            if (
                profile != "profile_A"
                and rng.random() < 0.20
            ):
                investment_ratio = 0.0

            amounts = {

                "Essentials":
                    income
                    * essential_ratio,

                "Desire":
                    income
                    * desire_ratio,

                "Repayment":
                    income
                    * repayment_ratio,

                "Investment_Savings":
                    income
                    * investment_ratio,

                "Others":
                    income
                    * other_ratio,
            }

            total_outflow = sum(
                amounts.values()
            )

            cap = income * (
                1.30
                if profile == "profile_C"
                else 1.18
            )

            if total_outflow > cap:

                flexible = (
                    amounts["Desire"]
                    + amounts[
                        "Investment_Savings"
                    ]
                    + amounts["Others"]
                )

                excess = (
                    total_outflow
                    - cap
                )

                if flexible > excess:

                    scale = max(
                        0,
                        (
                            flexible
                            - excess
                        )
                        / flexible
                    )

                    for category in [
                        "Desire",
                        "Investment_Savings",
                        "Others",
                    ]:
                        amounts[
                            category
                        ] *= scale

                else:

                    scale = (
                        cap
                        / total_outflow
                    )

                    for category in amounts:
                        amounts[
                            category
                        ] *= scale

            # --------------------------------------------------
            # Income transaction
            # --------------------------------------------------

            transactions.append({

                "transaction_id":
                    f"T{transaction_id:07d}",

                "user_id":
                    user_id,

                "date":
                    random_date(
                        YEAR,
                        month
                    ),

                "amount":
                    round(income, 2),

                "txn_type":
                    "credit",

                "label":
                    "Income",
            })

            transaction_id += 1

            # --------------------------------------------------
            # Debit transactions
            # --------------------------------------------------

            transaction_specs = [

                (
                    "Essentials",
                    int(
                        rng.integers(
                            8,
                            16
                        )
                    )
                ),

                (
                    "Desire",
                    int(
                        rng.integers(
                            5,
                            11
                        )
                    )
                ),

                (
                    "Repayment",
                    0
                    if amounts[
                        "Repayment"
                    ] < 100
                    else int(
                        rng.integers(
                            1,
                            4
                        )
                    )
                ),

                (
                    "Investment_Savings",
                    0
                    if amounts[
                        "Investment_Savings"
                    ] < 100
                    else int(
                        rng.integers(
                            1,
                            4
                        )
                    )
                ),

                (
                    "Others",
                    0
                    if amounts[
                        "Others"
                    ] < 80
                    else int(
                        rng.integers(
                            2,
                            6
                        )
                    )
                ),
            ]

            for (
                label,
                transaction_count
            ) in transaction_specs:

                values = split_amount(
                    round(
                        amounts[label],
                        2
                    ),
                    transaction_count
                )

                for value in values:

                    transactions.append({

                        "transaction_id":
                            f"T{transaction_id:07d}",

                        "user_id":
                            user_id,

                        "date":
                            random_date(
                                YEAR,
                                month
                            ),

                        "amount":
                            round(
                                value,
                                2
                            ),

                        "txn_type":
                            "debit",

                        "label":
                            label,
                    })

                    transaction_id += 1

            # --------------------------------------------------
            # Validation row
            # --------------------------------------------------

            monthly_validation.append({

                "user_id":
                    user_id,

                "month":
                    f"{YEAR}-{month:02d}",

                "income":
                    round(income, 2),

                "essentials":
                    round(
                        amounts[
                            "Essentials"
                        ],
                        2
                    ),

                "desire":
                    round(
                        amounts[
                            "Desire"
                        ],
                        2
                    ),

                "repayment":
                    round(
                        amounts[
                            "Repayment"
                        ],
                        2
                    ),

                "investment_savings":
                    round(
                        amounts[
                            "Investment_Savings"
                        ],
                        2
                    ),

                "others":
                    round(
                        amounts[
                            "Others"
                        ],
                        2
                    ),
            })

    # --------------------------------------------------
    # Sort transactions
    # --------------------------------------------------

    transactions.sort(
        key=lambda row: (
            row["user_id"],
            row["date"],
            row["transaction_id"]
        )
    )

    # --------------------------------------------------
    # Save validation artifacts
    # --------------------------------------------------

    write_csv(
        VALIDATION_DIR
        / "finpulse_generation_audit.csv",
        audit,
        [
            "user_id",
            "generation_profile",
            "base_monthly_income",
            "essential_ratio",
            "desire_ratio",
            "repayment_ratio",
            "investment_ratio",
            "other_ratio",
            "income_volatility",
        ]
    )

    write_csv(
        VALIDATION_DIR
        / "finpulse_monthly_generation_validation.csv",
        monthly_validation,
        [
            "user_id",
            "month",
            "income",
            "essentials",
            "desire",
            "repayment",
            "investment_savings",
            "others",
        ]
    )

    # --------------------------------------------------
    # Build SQLite database
    # --------------------------------------------------

    build_database(
        users,
        transactions
    )

    print(
        f"Generated {len(transactions):,} transactions "
        f"for {N_USERS:,} users."
    )

    print(
        f"Database saved to:\n{DATABASE_FILE}"
    )

    print(
        f"Validation outputs saved to:\n{VALIDATION_DIR}"
    )


if __name__ == "__main__":
    main()