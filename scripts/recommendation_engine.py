from pathlib import Path
import sqlite3

import pandas as pd


# --------------------------------------------------
# Project paths
# --------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent

DATABASE_FILE = (
    PROJECT_ROOT
    / "database"
    / "finpulse.db"
)


# --------------------------------------------------
# Recommendation generation
# --------------------------------------------------

def generate_recommendations(row):
    recommendations = []

    # --------------------------------------------------
    # 1. Overspending / spending pressure
    # --------------------------------------------------

    if row["avg_expense_ratio"] >= 1.0:
        recommendations.append({
            "priority": 1,
            "category": "Spending",
            "recommendation":
                "Your average outflow is at or above your income. "
                "Prioritize bringing monthly spending below income "
                "to rebuild a positive cash buffer."
        })

    elif row["avg_expense_ratio"] >= 0.90:
        recommendations.append({
            "priority": 2,
            "category": "Spending",
            "recommendation":
                "Your spending consumes most of your monthly income. "
                "Try creating more room between income and outflow "
                "so unexpected expenses are easier to absorb."
        })

    # --------------------------------------------------
    # 2. Desire / discretionary spending
    # --------------------------------------------------

    if row["avg_desire_ratio"] >= 0.30:
        recommendations.append({
            "priority": 2,
            "category": "Discretionary Spending",
            "recommendation":
                "A high share of your income goes toward discretionary "
                "spending. Consider setting a monthly limit for non-essential "
                "purchases and redirecting part of that amount toward savings."
        })

    elif row["avg_desire_ratio"] >= 0.25:
        recommendations.append({
            "priority": 3,
            "category": "Discretionary Spending",
            "recommendation":
                "Your discretionary spending is relatively high. "
                "Review recurring lifestyle expenses and identify areas "
                "where small reductions could increase monthly surplus."
        })

    if row["desire_ratio_change_3m"] >= 0.05:
        recommendations.append({
            "priority": 2,
            "category": "Spending Trend",
            "recommendation":
                "Your discretionary spending has increased compared with "
                "the previous three months. Review what changed recently "
                "before the higher spending level becomes habitual."
        })

    # --------------------------------------------------
    # 3. Repayment burden
    # --------------------------------------------------

    if row["avg_repayment_ratio"] >= 0.35:
        recommendations.append({
            "priority": 1,
            "category": "Repayment",
            "recommendation":
                "Repayments consume a large share of your income. "
                "Avoid adding unnecessary new repayment obligations and "
                "focus available surplus on improving debt flexibility."
        })

    elif row["avg_repayment_ratio"] >= 0.25:
        recommendations.append({
            "priority": 2,
            "category": "Repayment",
            "recommendation":
                "Your repayment burden is significant. Keep discretionary "
                "spending controlled so repayments do not crowd out savings "
                "and essential expenses."
        })

    if row["repayment_ratio_change_3m"] >= 0.05:
        recommendations.append({
            "priority": 2,
            "category": "Repayment Trend",
            "recommendation":
                "Your repayment burden has risen recently. Check whether "
                "this increase is temporary or likely to continue and adjust "
                "other spending accordingly."
        })

    # --------------------------------------------------
    # 4. Savings / investments
    # --------------------------------------------------

    if row["avg_investment_ratio"] < 0.03:
        recommendations.append({
            "priority": 2,
            "category": "Savings",
            "recommendation":
                "Very little of your observed income is currently going "
                "toward savings or investments. If your essential expenses "
                "and repayments are manageable, begin with a small regular allocation."
        })

    elif row["avg_investment_ratio"] < 0.08:
        recommendations.append({
            "priority": 3,
            "category": "Savings",
            "recommendation":
                "Your savings and investment allocation is relatively low. "
                "Consider gradually redirecting part of your monthly surplus "
                "toward longer-term savings."
        })

    if row["investment_ratio_change_3m"] <= -0.05:
        recommendations.append({
            "priority": 2,
            "category": "Savings Trend",
            "recommendation":
                "Your savings allocation has declined recently. Review whether "
                "this reflects a temporary expense or a longer-term change "
                "in spending behavior."
        })

    # --------------------------------------------------
    # 5. Income volatility
    # --------------------------------------------------

    if row["income_cv"] >= 0.15:
        recommendations.append({
            "priority": 2,
            "category": "Income Stability",
            "recommendation":
                "Your income varies substantially from month to month. "
                "Base recurring spending on a conservative income level "
                "and preserve stronger-income months as a buffer."
        })

    elif row["income_cv"] >= 0.10:
        recommendations.append({
            "priority": 3,
            "category": "Income Stability",
            "recommendation":
                "Your income shows noticeable variation. Maintaining a cash "
                "buffer can reduce the impact of weaker-income months."
        })

    # --------------------------------------------------
    # 6. Overspending frequency
    # --------------------------------------------------

    if row["overspending_month_ratio"] >= 0.50:
        recommendations.append({
            "priority": 1,
            "category": "Cash Flow",
            "recommendation":
                "You spend more than your income in at least half of observed "
                "months. Reducing recurring outflows should be the immediate priority."
        })

    elif row["overspending_month_ratio"] >= 0.30:
        recommendations.append({
            "priority": 2,
            "category": "Cash Flow",
            "recommendation":
                "Overspending occurs frequently. Track which categories are "
                "responsible in those months and set limits before the month begins."
        })

    # --------------------------------------------------
    # 7. Positive reinforcement
    # --------------------------------------------------

    if (
        row["avg_investment_ratio"] >= 0.12
        and row["avg_expense_ratio"] <= 0.85
        and row["overspending_month_ratio"] == 0
    ):
        recommendations.append({
            "priority": 4,
            "category": "Positive Behaviour",
            "recommendation":
                "Your spending remains controlled while savings allocation "
                "is strong. Maintain this balance and continue monitoring "
                "for changes in income or repayment obligations."
        })

    # --------------------------------------------------
    # Fallback
    # --------------------------------------------------

    if not recommendations:
        recommendations.append({
            "priority": 4,
            "category": "Maintain",
            "recommendation":
                "Your current financial behavior appears relatively balanced. "
                "Continue monitoring spending, savings, and monthly surplus "
                "for meaningful changes."
        })

    recommendations = sorted(
        recommendations,
        key=lambda item: item["priority"]
    )

    return recommendations


# --------------------------------------------------
# Build normalized recommendation table
# --------------------------------------------------

def build_recommendation_table(df):
    rows = []

    for _, row in df.iterrows():
        recommendations = generate_recommendations(row)

        # Keep top 3 recommendations for each user
        for rank, recommendation in enumerate(
            recommendations[:3],
            start=1
        ):
            rows.append({
                "user_id": row["user_id"],
                "recommendation_rank": rank,
                "priority": recommendation["priority"],
                "category": recommendation["category"],
                "recommendation": recommendation["recommendation"],
            })

    return pd.DataFrame(rows)


# --------------------------------------------------
# Main
# --------------------------------------------------

def main():
    print("Loading FinPulse user features and scores...")

    with sqlite3.connect(DATABASE_FILE) as conn:

        df = pd.read_sql_query(
            """
            SELECT
                f.*,
                s.spending_control_score,
                s.savings_score,
                s.debt_management_score,
                s.stability_score,
                s.finpulse_score,
                s.score_band
            FROM user_features AS f
            JOIN user_scores AS s
                ON f.user_id = s.user_id
            ORDER BY f.user_id
            """,
            conn
        )

        print(
            f"Loaded {len(df):,} users."
        )

        print("Generating personalized recommendations...")

        recommendations = build_recommendation_table(df)

        recommendations.to_sql(
            "recommendations",
            conn,
            if_exists="replace",
            index=False
        )

        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_recommendations_user
            ON recommendations(user_id)
            """
        )

        conn.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS
            idx_recommendations_user_rank
            ON recommendations(
                user_id,
                recommendation_rank
            )
            """
        )

        conn.commit()

    print(
        f"Generated {len(recommendations):,} recommendations "
        f"for {len(df):,} users."
    )


if __name__ == "__main__":
    main()