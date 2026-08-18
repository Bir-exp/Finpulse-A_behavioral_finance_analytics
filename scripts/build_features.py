from pathlib import Path
import sqlite3

import numpy as np
import pandas as pd


# --------------------------------------------------
# Paths
# --------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent

DATABASE_FILE = (
    PROJECT_ROOT
    / "database"
    / "finpulse.db"
)

SQL_DIR = PROJECT_ROOT / "sql"


# --------------------------------------------------
# Run SQL pipeline
# --------------------------------------------------

def run_sql_file(connection, filename):
    sql_path = SQL_DIR / filename

    sql = sql_path.read_text(
        encoding="utf-8"
    )

    connection.executescript(sql)


# --------------------------------------------------
# Python-only features
# --------------------------------------------------

def build_python_features(monthly):
    """
    Features that are more convenient to calculate
    in Pandas than SQLite.
    """

    monthly = monthly.copy()

    # --------------------------------------------------
    # Median income
    # --------------------------------------------------

    median_income = (
        monthly
        .groupby("user_id")["income"]
        .median()
        .rename("median_income")
        .reset_index()
    )

    # --------------------------------------------------
    # Volatility features
    # --------------------------------------------------

    volatility = (
        monthly
        .groupby("user_id")
        .agg(
            income_std=("income", "std"),

            expense_ratio_volatility=(
                "expense_to_income_ratio",
                "std"
            ),

            desire_volatility=(
                "desire_ratio",
                "std"
            ),

            repayment_volatility=(
                "repayment_ratio",
                "std"
            ),

            investment_volatility=(
                "investment_ratio",
                "std"
            ),
        )
        .reset_index()
    )

    return median_income, volatility


# --------------------------------------------------
# Build final user feature table
# --------------------------------------------------

def build_final_user_features(connection):

    monthly = pd.read_sql_query(
        """
        SELECT *
        FROM monthly_features
        ORDER BY user_id, month
        """,
        connection
    )

    base = pd.read_sql_query(
        """
        SELECT *
        FROM user_features_base
        ORDER BY user_id
        """,
        connection
    )

    trends = pd.read_sql_query(
        """
        SELECT *
        FROM user_trends
        ORDER BY user_id
        """,
        connection
    )

    median_income, volatility = (
        build_python_features(monthly)
    )

    features = (
        base
        .merge(
            median_income,
            on="user_id",
            how="left"
        )
        .merge(
            volatility,
            on="user_id",
            how="left"
        )
        .merge(
            trends,
            on="user_id",
            how="left"
        )
    )

    # --------------------------------------------------
    # Income coefficient of variation
    # --------------------------------------------------

    features["income_cv"] = np.where(
        features["avg_income"] > 0,
        features["income_std"]
        / features["avg_income"],
        0.0
    )

    # --------------------------------------------------
    # Clean numeric values
    # --------------------------------------------------

    numeric_columns = (
        features
        .select_dtypes(include=[np.number])
        .columns
    )

    features[numeric_columns] = (
        features[numeric_columns]
        .round(4)
    )

    return features


# --------------------------------------------------
# Save final table to SQLite
# --------------------------------------------------

def save_user_features(connection, features):

    features.to_sql(
        "user_features",
        connection,
        if_exists="replace",
        index=False
    )

    connection.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS
        idx_user_features_user
        ON user_features(user_id)
        """
    )

    connection.commit()


# --------------------------------------------------
# Main
# --------------------------------------------------

def main():

    print("Connecting to FinPulse database...")

    with sqlite3.connect(DATABASE_FILE) as conn:

        print("Building monthly features...")
        run_sql_file(
            conn,
            "01_monthly_features.sql"
        )

        print("Building user-level aggregates...")
        run_sql_file(
            conn,
            "02_user_features.sql"
        )

        print("Building behavioral trends...")
        run_sql_file(
            conn,
            "03_user_trends.sql"
        )

        print("Building Python volatility features...")

        user_features = (
            build_final_user_features(conn)
        )

        print("Saving user_features table...")

        save_user_features(
            conn,
            user_features
        )

        monthly_count = conn.execute(
            """
            SELECT COUNT(*)
            FROM monthly_features
            """
        ).fetchone()[0]

        user_count = conn.execute(
            """
            SELECT COUNT(*)
            FROM user_features
            """
        ).fetchone()[0]

    print("\nFeature pipeline complete.")

    print(
        f"Monthly feature rows: "
        f"{monthly_count:,}"
    )

    print(
        f"User feature rows: "
        f"{user_count:,}"
    )


if __name__ == "__main__":
    main()