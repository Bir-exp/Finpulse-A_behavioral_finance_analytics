from pathlib import Path
import sqlite3

import pandas as pd

from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler


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
# Clustering configuration
# --------------------------------------------------

FEATURE_COLUMNS = [
    "avg_essential_ratio",
    "avg_desire_ratio",
    "avg_repayment_ratio",
    "avg_investment_ratio",
    "avg_expense_ratio",
    "overspending_month_ratio",
    "income_cv",
    "expense_ratio_volatility",
]

N_CLUSTERS = 5
RANDOM_STATE = 42


# --------------------------------------------------
# Segment interpretation
# --------------------------------------------------

SEGMENT_NAMES = {
    0: "Variable-Income Users",
    1: "Lifestyle-Heavy Spenders",
    2: "Consistent Savers",
    3: "Debt-Constrained Users",
    4: "Financially Stretched Users",
}


SEGMENT_DESCRIPTIONS = {
    0:
        "Users in this segment show relatively high income variability "
        "while maintaining comparatively moderate spending patterns.",

    1:
        "Users in this segment allocate a relatively high share of income "
        "to discretionary spending and maintain comparatively low savings.",

    2:
        "Users in this segment consistently allocate a meaningful share "
        "of income toward savings and investments while keeping spending controlled.",

    3:
        "Users in this segment devote a significant share of income "
        "to repayments, limiting flexibility for other financial goals.",

    4:
        "Users in this segment experience high repayment pressure and "
        "frequent months where total outflow exceeds income.",
}


# --------------------------------------------------
# Load features
# --------------------------------------------------

def load_features(connection):
    return pd.read_sql_query(
        """
        SELECT *
        FROM user_features
        ORDER BY user_id
        """,
        connection
    )


# --------------------------------------------------
# Build segmentation
# --------------------------------------------------

def build_segments(features):

    X = features[FEATURE_COLUMNS].copy()

    # Standardize features so different scales
    # do not dominate KMeans distance calculations.
    scaler = StandardScaler()

    X_scaled = scaler.fit_transform(X)

    model = KMeans(
        n_clusters=N_CLUSTERS,
        random_state=RANDOM_STATE,
        n_init=20
    )

    cluster_labels = model.fit_predict(X_scaled)

    segments = pd.DataFrame({
        "user_id": features["user_id"],
        "cluster_id": cluster_labels,
    })

    segments["segment_name"] = (
        segments["cluster_id"]
        .map(SEGMENT_NAMES)
    )

    segments["segment_description"] = (
        segments["cluster_id"]
        .map(SEGMENT_DESCRIPTIONS)
    )

    return segments, model


# --------------------------------------------------
# Cluster profile
# --------------------------------------------------

def build_cluster_profile(features, segments):

    profiled = features[
        ["user_id"] + FEATURE_COLUMNS
    ].merge(
        segments[
            ["user_id", "cluster_id", "segment_name"]
        ],
        on="user_id",
        how="left"
    )

    profile = (
        profiled
        .groupby(
            ["cluster_id", "segment_name"]
        )[FEATURE_COLUMNS]
        .mean()
        .round(4)
        .reset_index()
    )

    return profile


# --------------------------------------------------
# Save tables
# --------------------------------------------------

def save_results(
    connection,
    segments,
    cluster_profile
):

    segments.to_sql(
        "user_segments",
        connection,
        if_exists="replace",
        index=False
    )

    cluster_profile.to_sql(
        "cluster_profiles",
        connection,
        if_exists="replace",
        index=False
    )

    connection.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS
        idx_user_segments_user
        ON user_segments(user_id)
        """
    )

    connection.commit()


# --------------------------------------------------
# Summary
# --------------------------------------------------

def print_summary(segments, profile):

    print("\nSegment distribution:\n")

    print(
        segments["segment_name"]
        .value_counts()
    )

    print("\nCluster profiles:\n")

    print(profile.to_string(index=False))


# --------------------------------------------------
# Main
# --------------------------------------------------

def main():

    print("Loading FinPulse user features...")

    with sqlite3.connect(DATABASE_FILE) as conn:

        features = load_features(conn)

        print(
            f"Loaded {len(features):,} users."
        )

        print("Running behavioral segmentation...")

        segments, _ = build_segments(
            features
        )

        profile = build_cluster_profile(
            features,
            segments
        )

        save_results(
            conn,
            segments,
            profile
        )

    print(
        f"Segmented {len(segments):,} users "
        f"into {N_CLUSTERS} behavioral groups."
    )

    print_summary(
        segments,
        profile
    )


if __name__ == "__main__":
    main()