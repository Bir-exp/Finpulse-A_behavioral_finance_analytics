from pathlib import Path
import sqlite3

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parent.parent

DATABASE_FILE = (
    PROJECT_ROOT
    / "database"
    / "finpulse.db"
)


# --------------------------------------------------
# Signal generation
# --------------------------------------------------

def generate_signals(row):
    signals = []

    if row["avg_expense_ratio"] >= 1.0:
        signals.append(
            "Average outflow meets or exceeds income"
        )

    elif row["avg_expense_ratio"] >= 0.90:
        signals.append(
            "High overall spending relative to income"
        )

    if row["overspending_month_ratio"] >= 0.30:
        signals.append(
            "Frequent overspending months"
        )

    elif row["overspending_month_ratio"] > 0:
        signals.append(
            "Occasional overspending months"
        )

    if row["avg_repayment_ratio"] >= 0.25:
        signals.append(
            "High repayment burden"
        )

    elif row["avg_repayment_ratio"] >= 0.18:
        signals.append(
            "Moderate repayment burden"
        )

    if row["avg_desire_ratio"] >= 0.28:
        signals.append(
            "High discretionary spending"
        )

    elif row["avg_desire_ratio"] >= 0.20:
        signals.append(
            "Moderate discretionary spending"
        )

    if row["avg_investment_ratio"] >= 0.12:
        signals.append(
            "Strong savings and investment allocation"
        )

    elif row["avg_investment_ratio"] < 0.05:
        signals.append(
            "Low savings and investment allocation"
        )

    if row["income_cv"] >= 0.12:
        signals.append(
            "Income is highly variable"
        )

    elif row["income_cv"] >= 0.07:
        signals.append(
            "Income shows moderate variability"
        )

    if row["desire_ratio_change_3m"] >= 0.05:
        signals.append(
            "Discretionary spending is rising"
        )

    elif row["desire_ratio_change_3m"] <= -0.05:
        signals.append(
            "Discretionary spending is declining"
        )

    if row["repayment_ratio_change_3m"] >= 0.05:
        signals.append(
            "Repayment burden is rising"
        )

    elif row["repayment_ratio_change_3m"] <= -0.05:
        signals.append(
            "Repayment burden is declining"
        )

    if row["investment_ratio_change_3m"] >= 0.04:
        signals.append(
            "Savings allocation is improving"
        )

    elif row["investment_ratio_change_3m"] <= -0.04:
        signals.append(
            "Savings allocation is declining"
        )

    if row["expense_ratio_change_3m"] >= 0.05:
        signals.append(
            "Overall spending pressure is increasing"
        )

    elif row["expense_ratio_change_3m"] <= -0.05:
        signals.append(
            "Overall spending pressure is improving"
        )

    return signals


# --------------------------------------------------
# Build normalized signal table
# --------------------------------------------------

def build_signal_table(features):

    rows = []

    for _, row in features.iterrows():

        signals = generate_signals(row)

        for position, signal in enumerate(
            signals,
            start=1
        ):
            rows.append({
                "user_id": row["user_id"],
                "signal_order": position,
                "signal": signal,
            })

    return pd.DataFrame(rows)


# --------------------------------------------------
# Main
# --------------------------------------------------

def main():

    with sqlite3.connect(DATABASE_FILE) as conn:

        features = pd.read_sql_query(
            """
            SELECT *
            FROM user_features
            """,
            conn
        )

        signals = build_signal_table(
            features
        )

        signals.to_sql(
            "behavioral_signals",
            conn,
            if_exists="replace",
            index=False
        )

        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_behavioral_signals_user
            ON behavioral_signals(user_id)
            """
        )

        conn.commit()

    print(
        f"Generated {len(signals):,} "
        "behavioral signals."
    )


if __name__ == "__main__":
    main()