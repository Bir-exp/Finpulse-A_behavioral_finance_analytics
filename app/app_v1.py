from pathlib import Path
import sqlite3

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st


# --------------------------------------------------
# Paths
# --------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent

DATABASE_FILE = (
    PROJECT_ROOT
    / "database"
    / "finpulse.db"
)


# --------------------------------------------------
# Page configuration
# --------------------------------------------------

st.set_page_config(
    page_title="FinPulse",
    page_icon="💹",
    layout="wide"
)


# --------------------------------------------------
# Basic styling
# --------------------------------------------------

st.markdown(
    """
    <style>

    .block-container {
        padding-top: 2rem;
        padding-bottom: 3rem;
    }

    .finpulse-title {
        text-align: center;
        font-size: 3rem;
        font-weight: 700;
        margin-bottom: 0;
    }

    .finpulse-subtitle {
        text-align: center;
        color: #777;
        margin-bottom: 2rem;
    }

    .avatar-container {
        text-align: center;
        margin-top: 1rem;
        margin-bottom: 0.5rem;
    }

    .avatar-circle {
        width: 110px;
        height: 110px;
        border-radius: 50%;
        margin: auto;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 3.5rem;
        background: rgba(128, 128, 128, 0.10);
        border: 2px solid rgba(128, 128, 128, 0.25);
    }

    .segment-title {
        text-align: center;
        font-size: 1.7rem;
        font-weight: 700;
        margin-top: 0.6rem;
    }

    .segment-description {
        text-align: center;
        max-width: 620px;
        margin: auto;
        color: #777;
    }

    .signal-card {
        padding: 0.8rem 1rem;
        border-radius: 10px;
        background: rgba(128, 128, 128, 0.08);
        margin-bottom: 0.6rem;
    }



    </style>
    """,
    unsafe_allow_html=True
)


# --------------------------------------------------
# Database loading
# --------------------------------------------------

@st.cache_data
def load_users():

    with sqlite3.connect(DATABASE_FILE) as conn:

        return pd.read_sql_query(
            """
            SELECT
                f.*,

                s.spending_control_score,
                s.savings_score,
                s.debt_management_score,
                s.stability_score,
                s.finpulse_score,
                s.score_band,

                seg.cluster_id,
                seg.segment_name,
                seg.segment_description

            FROM user_features AS f

            JOIN user_scores AS s
                ON f.user_id = s.user_id

            JOIN user_segments AS seg
                ON f.user_id = seg.user_id

            ORDER BY f.user_id
            """,
            conn
        )


@st.cache_data
def load_monthly():

    with sqlite3.connect(DATABASE_FILE) as conn:

        return pd.read_sql_query(
            """
            SELECT *
            FROM monthly_features
            ORDER BY user_id, month
            """,
            conn
        )


@st.cache_data
def load_signals():

    with sqlite3.connect(DATABASE_FILE) as conn:

        return pd.read_sql_query(
            """
            SELECT *
            FROM behavioral_signals
            ORDER BY user_id, signal_order
            """,
            conn
        )


@st.cache_data
def load_recommendations():

    with sqlite3.connect(DATABASE_FILE) as conn:

        return pd.read_sql_query(
            """
            SELECT *
            FROM recommendations
            ORDER BY user_id, recommendation_rank
            """,
            conn
        )


# --------------------------------------------------
# Load data
# --------------------------------------------------

users = load_users()
monthly = load_monthly()
signals = load_signals()
recommendations = load_recommendations()


# --------------------------------------------------
# Header
# --------------------------------------------------

st.markdown(
    '<div class="finpulse-title">FinPulse</div>',
    unsafe_allow_html=True
)

st.markdown(
    """
    <div class="finpulse-subtitle">
    Understand financial behavior through transaction intelligence,
    behavioral segmentation and explainable analytics.
    </div>
    """,
    unsafe_allow_html=True
)


# --------------------------------------------------
# User selector
# --------------------------------------------------

selector_col1, selector_col2, selector_col3 = st.columns(
    [1, 2, 1]
)

with selector_col2:

    user_id = st.selectbox(
        "Select User",
        users["user_id"].tolist()
    )


# --------------------------------------------------
# Selected-user data
# --------------------------------------------------

user = (
    users[
        users["user_id"] == user_id
    ]
    .iloc[0]
)

user_monthly = (
    monthly[
        monthly["user_id"] == user_id
    ]
    .sort_values("month")
)

user_signals = (
    signals[
        signals["user_id"] == user_id
    ]
    .sort_values("signal_order")
)

user_recommendations = (
    recommendations[
        recommendations["user_id"] == user_id
    ]
    .sort_values("recommendation_rank")
)


# --------------------------------------------------
# Hero profile section
# --------------------------------------------------

st.divider()

left, center, right = st.columns(
    [1.2, 1.3, 1.2]
)


# --------------------------------------------------
# Income allocation donut
# --------------------------------------------------

allocation_labels = [
    "Essentials",
    "Desire",
    "Repayment",
    "Investment",
    "Others",
]

allocation_values = [
    user["avg_essential_ratio"],
    user["avg_desire_ratio"],
    user["avg_repayment_ratio"],
    user["avg_investment_ratio"],
    user["avg_other_ratio"],
]


with left:

    st.subheader(
        "Income Allocation"
    )

    allocation_fig = go.Figure(
        data=[
            go.Pie(
                labels=allocation_labels,
                values=allocation_values,
                hole=0.62,
                textinfo="label+percent",
                hovertemplate=(
                    "%{label}<br>"
                    "%{percent}<extra></extra>"
                )
            )
        ]
    )

    allocation_fig.update_layout(
        margin=dict(
            l=10,
            r=10,
            t=20,
            b=10
        ),
        showlegend=False,
        height=330
    )

    st.plotly_chart(
        allocation_fig,
        use_container_width=True
    )


# --------------------------------------------------
# User avatar + segment
# --------------------------------------------------

with center:

    st.markdown(
        """
        <div class="avatar-container">
            <div class="avatar-circle">
                👤
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.markdown(
        f"""
        <div class="segment-title">
        {user['segment_name']}
        </div>
        """,
        unsafe_allow_html=True
    )

    st.markdown(
        f"""
        <div class="segment-description">
        {user['segment_description']}
        </div>
        """,
        unsafe_allow_html=True
    )

    st.write("")

    st.metric(
        "Average Monthly Income",
        f"₹{user['avg_income']:,.0f}"
    )


# --------------------------------------------------
# Score gauge
# --------------------------------------------------

with right:

    st.subheader(
        "FinPulse Score"
    )

    score_fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=user["finpulse_score"],
            number={
                "suffix": "/100"
            },
            title={
                "text": user["score_band"]
            },
            gauge={
                "axis": {
                    "range": [0, 100]
                },
                "bar": {
                    "thickness": 0.25
                },
                "steps": [
                    {
                        "range": [0, 35],
                    },
                    {
                        "range": [35, 50],
                    },
                    {
                        "range": [50, 65],
                    },
                    {
                        "range": [65, 80],
                    },
                    {
                        "range": [80, 100],
                    },
                ],
            }
        )
    )

    score_fig.update_layout(
        height=330,
        margin=dict(
            l=25,
            r=25,
            t=40,
            b=10
        )
    )

    st.plotly_chart(
        score_fig,
        use_container_width=True
    )


# --------------------------------------------------
# Key metrics
# --------------------------------------------------

st.divider()

st.subheader(
    "Financial Snapshot"
)

m1, m2, m3, m4 = st.columns(4)

with m1:
    st.metric(
        "Expense Ratio",
        f"{user['avg_expense_ratio'] * 100:.1f}%"
    )

with m2:
    st.metric(
        "Savings Ratio",
        f"{user['avg_investment_ratio'] * 100:.1f}%"
    )

with m3:
    st.metric(
        "Repayment Ratio",
        f"{user['avg_repayment_ratio'] * 100:.1f}%"
    )

with m4:
    st.metric(
        "Monthly Surplus",
        f"₹{user['avg_surplus']:,.0f}"
    )


m5, m6, m7, m8 = st.columns(4)

with m5:
    st.metric(
        "Essential Spending",
        f"{user['avg_essential_ratio'] * 100:.1f}%"
    )

with m6:
    st.metric(
        "Desire Spending",
        f"{user['avg_desire_ratio'] * 100:.1f}%"
    )

with m7:
    st.metric(
        "Overspending Months",
        int(user["overspending_months"])
    )

with m8:
    st.metric(
        "Income Variability",
        f"{user['income_cv'] * 100:.1f}%"
    )


# --------------------------------------------------
# Score breakdown
# --------------------------------------------------

st.divider()

st.subheader(
    "Score Breakdown"
)

score_data = pd.DataFrame({
    "Component": [
        "Spending Control",
        "Savings Behaviour",
        "Debt Management",
        "Financial Stability",
    ],
    "Score": [
        user["spending_control_score"],
        user["savings_score"],
        user["debt_management_score"],
        user["stability_score"],
    ],
    "Maximum": [
        30,
        25,
        25,
        20,
    ]
})

score_data["Score %"] = (
    score_data["Score"]
    / score_data["Maximum"]
    * 100
)


score_breakdown_fig = px.bar(
    score_data,
    x="Score %",
    y="Component",
    orientation="h",
    text="Score %",
    hover_data=[
        "Score",
        "Maximum"
    ]
)

score_breakdown_fig.update_traces(
    texttemplate="%{text:.0f}%",
    textposition="outside"
)

score_breakdown_fig.update_layout(
    xaxis_title="Score (%)",
    yaxis_title="",
    xaxis_range=[0, 110],
    height=350
)

st.plotly_chart(
    score_breakdown_fig,
    use_container_width=True
)


# --------------------------------------------------
# Behavioral signals
# --------------------------------------------------

st.divider()

st.subheader(
    "Behavioral Signals"
)

if user_signals.empty:

    st.info(
        "No notable behavioral signals detected."
    )

else:

    signal_columns = st.columns(2)

    for index, signal in enumerate(
        user_signals["signal"]
    ):

        target_column = (
            signal_columns[
                index % 2
            ]
        )

        with target_column:

            st.markdown(
                f"""
                <div class="signal-card">
                • {signal}
                </div>
                """,
                unsafe_allow_html=True
            )


# --------------------------------------------------
# Monthly behavior
# --------------------------------------------------

st.divider()

st.subheader(
    "12-Month Financial Behaviour"
)

trend_df = user_monthly[
    [
        "month",
        "essential_ratio",
        "desire_ratio",
        "repayment_ratio",
        "investment_ratio"
    ]
].copy()

trend_df = trend_df.rename(
    columns={
        "essential_ratio":
            "Essentials",

        "desire_ratio":
            "Desire",

        "repayment_ratio":
            "Repayment",

        "investment_ratio":
            "Investment & Savings",
    }
)

trend_long = trend_df.melt(
    id_vars="month",
    var_name="Category",
    value_name="Ratio"
)

trend_long["Percentage"] = (
    trend_long["Ratio"]
    * 100
)


trend_fig = px.line(
    trend_long,
    x="month",
    y="Percentage",
    color="Category",
    markers=True,
    hover_data={
        "Ratio": False,
        "Percentage": ":.1f"
    }
)

trend_fig.update_layout(
    xaxis_title="Month",
    yaxis_title="% of Monthly Income",
    height=430
)

st.plotly_chart(
    trend_fig,
    use_container_width=True
)


# --------------------------------------------------
# Spending pressure
# --------------------------------------------------

st.subheader(
    "Spending Pressure"
)

pressure_df = (
    user_monthly[
        [
            "month",
            "expense_to_income_ratio"
        ]
    ]
    .copy()
)

pressure_df[
    "Expense-to-Income %"
] = (
    pressure_df[
        "expense_to_income_ratio"
    ]
    * 100
)


pressure_fig = px.area(
    pressure_df,
    x="month",
    y="Expense-to-Income %"
)

pressure_fig.add_hline(
    y=100,
    line_dash="dash",
    annotation_text="Income Limit"
)

pressure_fig.update_layout(
    yaxis_title="Expense-to-Income Ratio (%)",
    xaxis_title="Month",
    height=380
)

st.plotly_chart(
    pressure_fig,
    use_container_width=True
)


# --------------------------------------------------
# Recent behavioral changes
# --------------------------------------------------

st.divider()

st.subheader(
    "Recent 3-Month Change"
)

c1, c2, c3, c4 = st.columns(4)

with c1:

    st.metric(
        "Desire Spending",
        f"{user['desire_ratio_change_3m'] * 100:+.1f} pp"
    )

with c2:

    st.metric(
        "Repayment Burden",
        f"{user['repayment_ratio_change_3m'] * 100:+.1f} pp"
    )

with c3:

    st.metric(
        "Savings Allocation",
        f"{user['investment_ratio_change_3m'] * 100:+.1f} pp"
    )

with c4:

    st.metric(
        "Expense Pressure",
        f"{user['expense_ratio_change_3m'] * 100:+.1f} pp"
    )

st.caption(
    "pp = percentage-point change between the latest "
    "three months and the previous three months."
)


# --------------------------------------------------
# User vs segment comparison
# --------------------------------------------------

st.divider()

st.subheader(
    "How This User Compares With Their Segment"
)

segment_users = users[
    users["segment_name"]
    == user["segment_name"]
]

comparison_metrics = {
    "Desire Spending":
        "avg_desire_ratio",

    "Repayment Burden":
        "avg_repayment_ratio",

    "Savings Allocation":
        "avg_investment_ratio",

    "Expense Ratio":
        "avg_expense_ratio",

    "Income Variability":
        "income_cv",
}

comparison_rows = []

for label, column in comparison_metrics.items():

    comparison_rows.append({
        "Metric": label,
        "User": user[column] * 100,
        "Segment Average":
            segment_users[column]
            .mean()
            * 100
    })


comparison_df = pd.DataFrame(
    comparison_rows
)

comparison_long = (
    comparison_df
    .melt(
        id_vars="Metric",
        var_name="Profile",
        value_name="Percentage"
    )
)


comparison_fig = px.bar(
    comparison_long,
    x="Metric",
    y="Percentage",
    color="Profile",
    barmode="group"
)

comparison_fig.update_layout(
    yaxis_title="Percentage (%)",
    xaxis_title="",
    height=420
)

st.plotly_chart(
    comparison_fig,
    use_container_width=True
)


# --------------------------------------------------
# Recommendations
# --------------------------------------------------

st.divider()

st.subheader("Recommended Actions")

if user_recommendations.empty:

    st.info(
        "No recommendations available."
    )

else:

    for _, rec in user_recommendations.iterrows():

        rank = int(
            rec["recommendation_rank"]
        )

        category = rec["category"]
        text = rec["recommendation"]
        priority = int(rec["priority"])

        with st.container(border=True):

            col1, col2 = st.columns(
                [5, 1]
            )

            with col1:

                st.markdown(
                    f"### {rank}. {category}"
                )

            with col2:

                if priority == 1:
                    st.markdown("**High Priority**")

                elif priority == 2:
                    st.markdown("**Priority**")

                else:
                    st.markdown("**Suggestion**")

            st.write(text)

# --------------------------------------------------
# Methodology
# --------------------------------------------------

st.divider()

with st.expander(
    "How FinPulse generates these insights"
):

    st.markdown(
        """
        ### Behavioral Segment
        KMeans clustering groups users with similar financial
        behavior based on standardized transaction-derived features.

        ### FinPulse Score
        An interpretable scoring framework measures spending control,
        savings behaviour, debt management, and financial stability.

        ### Behavioral Signals
        Rule-based conditions identify noteworthy financial patterns,
        including high repayment burden, overspending, low savings,
        income instability, and recent behavioral changes.

        ### Recommendations
        Personalized recommendations are generated from the user's
        observed behavioral metrics and recent trends.

        ### Data Layer
        Transaction data is stored in SQLite and transformed into
        monthly and user-level behavioral features using SQL and Python.
        """
    )


# --------------------------------------------------
# Disclaimer
# --------------------------------------------------

st.divider()

st.caption(
    "FinPulse is an educational behavioral-finance prototype "
    "built using synthetic transaction-pattern data. "
    "Its segments, scores, signals, and recommendations should "
    "not be interpreted as regulated financial advice, investment "
    "advice, or a credit assessment."
)