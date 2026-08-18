from pathlib import Path
import sqlite3

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parent.parent

DATABASE_FILE = (
    PROJECT_ROOT
    / "database"
    / "finpulse.db"
)


def clamp(value, minimum, maximum):
    return max(minimum, min(value, maximum))


# --------------------------------------------------
# Spending Control Score
# Maximum = 30
# --------------------------------------------------

def spending_control_score(row):
    expense_ratio = row["avg_expense_ratio"]

    if expense_ratio <= 0.70:
        score = 30
    elif expense_ratio <= 0.80:
        score = 27
    elif expense_ratio <= 0.90:
        score = 23
    elif expense_ratio <= 1.00:
        score = 16
    elif expense_ratio <= 1.10:
        score = 8
    else:
        score = 3

    overspending_ratio = row["overspending_month_ratio"]

    if overspending_ratio >= 0.50:
        score -= 8
    elif overspending_ratio >= 0.30:
        score -= 5
    elif overspending_ratio >= 0.15:
        score -= 2

    return clamp(score, 0, 30)


# --------------------------------------------------
# Savings Score
# Maximum = 25
# --------------------------------------------------

def savings_score(row):
    investment_ratio = row["avg_investment_ratio"]

    if investment_ratio >= 0.20:
        score = 25
    elif investment_ratio >= 0.15:
        score = 22
    elif investment_ratio >= 0.10:
        score = 18
    elif investment_ratio >= 0.05:
        score = 12
    elif investment_ratio > 0:
        score = 6
    else:
        score = 0

    trend = row["investment_ratio_change_3m"]

    if trend >= 0.05:
        score += 2
    elif trend <= -0.05:
        score -= 2

    return clamp(score, 0, 25)


# --------------------------------------------------
# Debt Score
# Maximum = 25
# --------------------------------------------------

def debt_score(row):
    repayment_ratio = row["avg_repayment_ratio"]

    if repayment_ratio <= 0.05:
        score = 25
    elif repayment_ratio <= 0.10:
        score = 23
    elif repayment_ratio <= 0.20:
        score = 19
    elif repayment_ratio <= 0.30:
        score = 13
    elif repayment_ratio <= 0.40:
        score = 7
    else:
        score = 3

    trend = row["repayment_ratio_change_3m"]

    if trend >= 0.05:
        score -= 2
    elif trend <= -0.05:
        score += 2

    return clamp(score, 0, 25)


# --------------------------------------------------
# Stability Score
# Maximum = 20
# --------------------------------------------------

def stability_score(row):
    score = 20

    income_cv = row["income_cv"]

    if income_cv >= 0.20:
        score -= 10
    elif income_cv >= 0.12:
        score -= 7
    elif income_cv >= 0.07:
        score -= 3

    expense_volatility = row["expense_ratio_volatility"]

    if expense_volatility >= 0.20:
        score -= 5
    elif expense_volatility >= 0.12:
        score -= 3
    elif expense_volatility >= 0.08:
        score -= 1

    if row["avg_surplus_ratio"] < 0:
        score -= 5
    elif row["avg_surplus_ratio"] < 0.10:
        score -= 2

    return clamp(score, 0, 20)


# --------------------------------------------------
# Score Band
# --------------------------------------------------

def score_band(score):
    if score >= 80:
        return "Strong"
    elif score >= 65:
        return "Stable"
    elif score >= 50:
        return "Watchful"
    elif score >= 35:
        return "Strained"
    else:
        return "High Pressure"


# --------------------------------------------------
# Calculate Scores
# --------------------------------------------------

def calculate_scores(features):
    results = pd.DataFrame()

    results["user_id"] = features["user_id"]

    results["spending_control_score"] = features.apply(
        spending_control_score,
        axis=1
    )

    results["savings_score"] = features.apply(
        savings_score,
        axis=1
    )

    results["debt_management_score"] = features.apply(
        debt_score,
        axis=1
    )

    results["stability_score"] = features.apply(
        stability_score,
        axis=1
    )

    results["finpulse_score"] = (
        results["spending_control_score"]
        + results["savings_score"]
        + results["debt_management_score"]
        + results["stability_score"]
    )

    results["score_band"] = (
        results["finpulse_score"]
        .apply(score_band)
    )

    return results


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

        scores = calculate_scores(features)

        scores.to_sql(
            "user_scores",
            conn,
            if_exists="replace",
            index=False
        )

        conn.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS
            idx_user_scores_user
            ON user_scores(user_id)
            """
        )

        conn.commit()

    print(
        f"Calculated scores for {len(scores):,} users."
    )


if __name__ == "__main__":
    main()