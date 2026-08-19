from pathlib import Path
import sqlite3

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st


# ==================================================
# CONFIG
# ==================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

DATABASE_FILE = (
    PROJECT_ROOT
    / "database"
    / "finpulse.db"
)

st.set_page_config(
    page_title="FinPulse V2",
    page_icon="💹",
    layout="wide"
)


# ==================================================
# SMALL UI STYLING
# ==================================================

st.markdown(
    """
    <style>

    .block-container {
        padding-top: 1.5rem;
        padding-bottom: 3rem;
    }

    .main-title {
        text-align: center;
        font-size: 3rem;
        font-weight: 750;
        margin-bottom: 0;
    }

    .main-subtitle {
        text-align: center;
        opacity: 0.65;
        margin-bottom: 1.5rem;
    }

    .profile-name {
        text-align: center;
        font-size: 2rem;
        font-weight: 700;
    }

    .profile-summary {
        text-align: center;
        opacity: 0.75;
        max-width: 650px;
        margin: auto;
    }

    .score-number {
        text-align: center;
        font-size: 4rem;
        font-weight: 750;
        line-height: 1;
    }

    .score-caption {
        text-align: center;
        font-size: 1.15rem;
        opacity: 0.75;
    }

    </style>
    """,
    unsafe_allow_html=True
)


# ==================================================
# FRIENDLY SEGMENT LANGUAGE
# ==================================================

SEGMENT_COPY = {

    "Variable-Income Users": (
        "Variable Income Navigator",
        "Your income changes more than most users, so maintaining "
        "flexibility and a financial buffer can be especially useful."
    ),

    "Lifestyle-Heavy Spenders": (
        "Lifestyle-Heavy Spender",
        "You tend to dedicate a larger share of your income to "
        "lifestyle and discretionary spending."
    ),

    "Consistent Savers": (
        "Consistent Saver",
        "You generally maintain controlled spending while putting "
        "a meaningful share of income toward savings and investments."
    ),

    "Debt-Constrained Users": (
        "Repayment-Focused",
        "A meaningful share of your monthly income currently goes "
        "toward repayments, which reduces flexibility elsewhere."
    ),

    "Financially Stretched Users": (
        "Financially Stretched",
        "Your spending and repayment commitments are taking up a "
        "large share of income, leaving relatively little breathing room."
    ),
}


# ==================================================
# LOAD DATA
# ==================================================

@st.cache_data
def load_data():

    with sqlite3.connect(DATABASE_FILE) as conn:

        users = pd.read_sql_query(
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

        monthly = pd.read_sql_query(
            """
            SELECT *
            FROM monthly_features
            ORDER BY user_id, month
            """,
            conn
        )

        signals = pd.read_sql_query(
            """
            SELECT *
            FROM behavioral_signals
            ORDER BY user_id, signal_order
            """,
            conn
        )

        recommendations = pd.read_sql_query(
            """
            SELECT *
            FROM recommendations
            ORDER BY user_id, recommendation_rank
            """,
            conn
        )

    return (
        users,
        monthly,
        signals,
        recommendations
    )


users, monthly, signals, recommendations = load_data()


# ==================================================
# HELPER FUNCTIONS
# ==================================================

def score_message(score):

    if score >= 80:
        return (
            "Looking strong",
            "Your overall financial behavior appears well controlled."
        )

    if score >= 65:
        return (
            "Doing fairly well",
            "Your finances look reasonably balanced with some room to improve."
        )

    if score >= 50:
        return (
            "Worth watching",
            "Some parts of your financial behavior could use more attention."
        )

    if score >= 35:
        return (
            "Under pressure",
            "Several financial pressures are reducing your flexibility."
        )

    return (
        "Needs attention",
        "Your current pattern shows significant financial pressure."
    )


def normalize_trait(score, maximum):

    return round(
        score / maximum * 100,
        1
    )


def spending_control_score(
    expense_ratio,
    overspending_ratio
):

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

    if overspending_ratio >= 0.50:
        score -= 8
    elif overspending_ratio >= 0.30:
        score -= 5
    elif overspending_ratio >= 0.15:
        score -= 2

    return max(
        0,
        min(score, 30)
    )


def savings_score(
    investment_ratio,
    trend
):

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

    if trend >= 0.05:
        score += 2
    elif trend <= -0.05:
        score -= 2

    return max(
        0,
        min(score, 25)
    )


def stability_score(
    income_cv,
    expense_volatility,
    surplus_ratio
):

    score = 20

    if income_cv >= 0.20:
        score -= 10
    elif income_cv >= 0.12:
        score -= 7
    elif income_cv >= 0.07:
        score -= 3

    if expense_volatility >= 0.20:
        score -= 5
    elif expense_volatility >= 0.12:
        score -= 3
    elif expense_volatility >= 0.08:
        score -= 1

    if surplus_ratio < 0:
        score -= 5
    elif surplus_ratio < 0.10:
        score -= 2

    return max(
        0,
        min(score, 20)
    )


# ==================================================
# HEADER
# ==================================================

st.markdown(
    '<div class="main-title">FinPulse</div>',
    unsafe_allow_html=True
)

st.markdown(
    """
    <div class="main-subtitle">
    Your money habits, explained simply.
    </div>
    """,
    unsafe_allow_html=True
)


# ==================================================
# USER SELECTOR
# ==================================================

select_left, select_center, select_right = st.columns(
    [1, 2, 1]
)

with select_center:

    user_id = st.selectbox(
        "Choose a user",
        users["user_id"].tolist()
    )


# ==================================================
# SELECT USER DATA
# ==================================================

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
    .copy()
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


segment_label, segment_summary = (
    SEGMENT_COPY.get(
        user["segment_name"],
        (
            user["segment_name"],
            user["segment_description"]
        )
    )
)


score_title, score_summary = score_message(
    user["finpulse_score"]
)


# ==================================================
# NAVIGATION
# ==================================================

overview_tab, year_tab, compare_tab, improve_tab = st.tabs(
    [
        "🏠 Overview",
        "📈 My Year",
        "👥 Compare",
        "🎯 Improve",
    ]
)


# ==================================================
# TAB 1 — OVERVIEW
# ==================================================

with overview_tab:

    st.subheader(
        f"Hello, {user_id} 👋"
    )

    # ==================================================
    # TOP SUMMARY
    # ==================================================

    profile_left, profile_center = st.columns(
        [1.25, 1],
        gap="large"
    )

    # ----------------------------------------------
    # LEFT — MONEY PERSONALITY WHEEL
    # ----------------------------------------------

    with profile_left:

        st.markdown(
            "### Your Money Personality"
        )

        trait_names = [
            "Spending Control",
            "Saving Habit",
            "Debt Comfort",
            "Income Stability",
        ]

        trait_values = [
            normalize_trait(
                user["spending_control_score"],
                30
            ),
            normalize_trait(
                user["savings_score"],
                25
            ),
            normalize_trait(
                user["debt_management_score"],
                25
            ),
            normalize_trait(
                user["stability_score"],
                20
            ),
        ]

        wheel_fig = go.Figure()

        wheel_fig.add_trace(
            go.Scatterpolar(
                r=trait_values + [trait_values[0]],
                theta=trait_names + [trait_names[0]],
                fill="toself",
                hovertemplate=(
                    "%{theta}: %{r:.0f}/100"
                    "<extra></extra>"
                ),
                name=""
            )
        )

        wheel_fig.update_layout(
            polar=dict(
                radialaxis=dict(
                    visible=True,
                    range=[0, 100],
                    showticklabels=False
                ),
                angularaxis=dict(
                    showticklabels=False
                )
            ),
            showlegend=False,
            margin=dict(
                l=110,
                r=110,
                t=65,
                b=65
            ),
            height=460
        )

        # Center user icon
        wheel_fig.add_annotation(
            text="👤",
            x=0.5,
            y=0.5,
            xref="paper",
            yref="paper",
            showarrow=False,
            font=dict(
                size=46
            )
        )

        # Top label
        wheel_fig.add_annotation(
            text="Saving Habit",
            x=0.5,
            y=1.07,
            xref="paper",
            yref="paper",
            showarrow=False,
            font=dict(
                size=13
            )
        )

        # Bottom label
        wheel_fig.add_annotation(
            text="Income Stability",
            x=0.5,
            y=-0.07,
            xref="paper",
            yref="paper",
            showarrow=False,
            font=dict(
                size=13
            )
        )

        # Left vertical label
        wheel_fig.add_annotation(
            text="Debt Comfort",
            x=-0.055,
            y=0.5,
            xref="paper",
            yref="paper",
            showarrow=False,
            textangle=-90,
            font=dict(
                size=13
            )
        )

        # Right vertical label
        wheel_fig.add_annotation(
            text="Spending Control",
            x=1.055,
            y=0.5,
            xref="paper",
            yref="paper",
            showarrow=False,
            textangle=90,
            font=dict(
                size=13
            )
        )

        st.plotly_chart(
            wheel_fig,
            use_container_width=True,
            config={
                "displayModeBar": False
            }
        )

    # ----------------------------------------------
    # CENTER — PERSONALITY + SCORE
    # ----------------------------------------------

    with profile_center:

        st.markdown(
            "<div style='height:38px;'></div>",
            unsafe_allow_html=True
        )

        st.markdown(
            """
            <div style="
                text-align:center;
                font-size:1rem;
                font-weight:600;
                opacity:0.60;
                margin-bottom:8px;
                letter-spacing:0.03em;
            ">
                Personality Type
            </div>
            """,
            unsafe_allow_html=True
        )

        st.markdown(
            f"""
            <div style="
                text-align:center;
                font-size:2.15rem;
                font-weight:750;
                line-height:1.2;
                margin-bottom:14px;
            ">
                {segment_label}
            </div>
            """,
            unsafe_allow_html=True
        )

        st.markdown(
            f"""
            <div style="
                text-align:center;
                opacity:0.72;
                line-height:1.55;
                font-size:0.98rem;
                max-width:400px;
                margin:0 auto 26px auto;
            ">
                {segment_summary}
            </div>
            """,
            unsafe_allow_html=True
        )

        st.markdown(
            """
            <div style="
                text-align:center;
                font-size:1rem;
                font-weight:600;
                opacity:0.60;
                margin-bottom:7px;
                letter-spacing:0.03em;
            ">
                Your FinPulse Score
            </div>
            """,
            unsafe_allow_html=True
        )

        st.markdown(
            f"""
            <div class="score-number">
                {int(user["finpulse_score"])}
            </div>
            """,
            unsafe_allow_html=True
        )

        st.markdown(
            f"""
            <div class="score-caption"
                 style="margin-top:8px;">
                {score_title}
            </div>
            """,
            unsafe_allow_html=True
        )

        st.markdown(
            "<div style='height:12px;'></div>",
            unsafe_allow_html=True
        )

        st.progress(
            int(user["finpulse_score"])
        )

        st.markdown(
            f"""
            <div style="
                text-align:center;
                opacity:0.65;
                font-size:0.92rem;
                line-height:1.45;
                margin-top:10px;
                max-width:400px;
                margin-left:auto;
                margin-right:auto;
            ">
                {score_summary}
            </div>
            """,
            unsafe_allow_html=True
        )

    # ==================================================
    # WHAT FINPULSE NOTICED
    # ==================================================

    # IMPORTANT:
    # This starts AFTER the profile_center block.
    # Therefore it returns to the full Overview width.

    st.divider()

    st.subheader(
        "What FinPulse noticed"
    )

    st.caption(
        "Key patterns identified from your financial behavior."
    )

    if user_signals.empty:

        st.success(
            "No major behavioral concerns were detected."
        )

    else:

        signal_cols = st.columns(
            2,
            gap="medium"
        )

        for index, signal in enumerate(
            user_signals["signal"]
        ):

            with signal_cols[
                index % 2
            ]:

                with st.container(
                    border=True
                ):

                    st.write(
                        f"💡 **{signal}**"
                    )

    # ==================================================
    # MONEY AT A GLANCE
    # ==================================================

    st.divider()

    st.subheader(
        "Your Money at a Glance"
    )

    glance1, glance2, glance3, glance4 = st.columns(
        4
    )

    with glance1:

        st.metric(
            "💰 You earn",
            f"₹{user['avg_income']:,.0f}",
            help="Average monthly income"
        )

        st.caption(
            "per month on average"
        )

    with glance2:

        st.metric(
            "💳 You spend",
            f"{user['avg_expense_ratio'] * 100:.0f}%"
        )

        st.caption(
            "of your income"
        )

    with glance3:

        st.metric(
            "🌱 You save",
            f"{user['avg_investment_ratio'] * 100:.0f}%"
        )

        st.caption(
            "through savings & investments"
        )

    with glance4:

        st.metric(
            "💵 You keep",
            f"₹{user['avg_surplus']:,.0f}"
        )

        st.caption(
            "average monthly surplus"
        )

    # ==================================================
    # WHERE MONEY GOES
    # ==================================================

    st.divider()

    st.subheader(
        "Where does your money go?"
    )

    allocation_left, allocation_right = st.columns(
        [1.25, 1],
        gap="large"
    )

    with allocation_left:

        allocation_amounts = pd.DataFrame(
            {
                "Category": [
                    "Essentials",
                    "Lifestyle",
                    "Repayments",
                    "Savings & Investments",
                    "Other",
                ],
                "Amount": [
                    user["avg_essential_ratio"]
                    * user["avg_income"],

                    user["avg_desire_ratio"]
                    * user["avg_income"],

                    user["avg_repayment_ratio"]
                    * user["avg_income"],

                    user["avg_investment_ratio"]
                    * user["avg_income"],

                    user["avg_other_ratio"]
                    * user["avg_income"],
                ]
            }
        )

        donut_fig = go.Figure(
            go.Pie(
                labels=allocation_amounts[
                    "Category"
                ],
                values=allocation_amounts[
                    "Amount"
                ],
                hole=0.60,
                hovertemplate=(
                    "<b>%{label}</b><br>"
                    "₹%{value:,.0f}<br>"
                    "%{percent}"
                    "<extra></extra>"
                )
            )
        )

        donut_fig.add_annotation(
            text=(
                f"₹{user['avg_income']:,.0f}"
                "<br>"
                "<span style='font-size:12px'>"
                "monthly income"
                "</span>"
            ),
            x=0.5,
            y=0.5,
            showarrow=False,
            align="center"
        )

        donut_fig.update_layout(
            height=420,
            margin=dict(
                l=20,
                r=20,
                t=20,
                b=20
            )
        )

        st.plotly_chart(
            donut_fig,
            use_container_width=True,
            config={
                "displayModeBar": False
            }
        )

    with allocation_right:

        st.markdown(
            "### In simple terms"
        )

        st.write(
            f"🏠 About **{user['avg_essential_ratio'] * 100:.0f}%** "
            "of your income goes toward essentials."
        )

        st.write(
            f"🛍️ About **{user['avg_desire_ratio'] * 100:.0f}%** "
            "goes toward lifestyle and discretionary spending."
        )

        st.write(
            f"💳 Around **{user['avg_repayment_ratio'] * 100:.0f}%** "
            "goes toward repayments."
        )

        st.write(
            f"🌱 Around **{user['avg_investment_ratio'] * 100:.0f}%** "
            "goes toward savings and investments."
        )

    # ==================================================
    # RECENT STORY
    # ==================================================

    st.divider()

    st.subheader(
        "What's changed recently?"
    )

    recent1, recent2, recent3 = st.columns(
        3
    )

    desire_change = (
        user["desire_ratio_change_3m"]
        * 100
    )

    savings_change = (
        user["investment_ratio_change_3m"]
        * 100
    )

    expense_change = (
        user["expense_ratio_change_3m"]
        * 100
    )

    with recent1:

        st.metric(
            "🛍️ Lifestyle spending",
            f"{user['avg_desire_ratio'] * 100:.0f}%",
            delta=f"{desire_change:+.1f} pp"
        )

    with recent2:

        st.metric(
            "🌱 Saving allocation",
            f"{user['avg_investment_ratio'] * 100:.0f}%",
            delta=f"{savings_change:+.1f} pp"
        )

    with recent3:

        st.metric(
            "💳 Overall spending",
            f"{user['avg_expense_ratio'] * 100:.0f}%",
            delta=f"{expense_change:+.1f} pp"
        )
# ==================================================
# TAB 2 — MY YEAR
# ==================================================

with year_tab:

    st.header(
        "Explore Your Year"
    )

    st.caption(
        "See how your financial behavior changed month by month."
    )


    view = st.radio(
        "What would you like to explore?",
        [
            "Spending",
            "Savings",
            "Repayments",
            "Cash Flow"
        ],
        horizontal=True
    )


    if view == "Spending":

        spending_df = user_monthly[
            [
                "month",
                "essential_ratio",
                "desire_ratio",
                "expense_to_income_ratio"
            ]
        ].copy()

        spending_df[
            "Essentials"
        ] = (
            spending_df[
                "essential_ratio"
            ] * 100
        )

        spending_df[
            "Lifestyle"
        ] = (
            spending_df[
                "desire_ratio"
            ] * 100
        )

        spending_df[
            "Total Spending"
        ] = (
            spending_df[
                "expense_to_income_ratio"
            ] * 100
        )


        spend_fig = px.line(

            spending_df,

            x="month",

            y=[
                "Essentials",
                "Lifestyle",
                "Total Spending"
            ],

            markers=True
        )

        spend_fig.add_hline(
            y=100,
            line_dash="dash",
            annotation_text="Income Limit"
        )

        spend_fig.update_layout(
            yaxis_title="% of income",
            xaxis_title="Month"
        )

        st.plotly_chart(
            spend_fig,
            use_container_width=True
        )


    elif view == "Savings":

        savings_df = user_monthly.copy()

        savings_df[
            "Savings %"
        ] = (
            savings_df[
                "investment_ratio"
            ] * 100
        )

        savings_df[
            "Savings Amount"
        ] = savings_df[
            "investment_savings"
        ]

        savings_fig = px.bar(
            savings_df,
            x="month",
            y="Savings Amount",
            hover_data=[
                "Savings %"
            ]
        )

        savings_fig.update_layout(
            xaxis_title="Month",
            yaxis_title="Savings & Investments (₹)"
        )

        st.plotly_chart(
            savings_fig,
            use_container_width=True
        )


    elif view == "Repayments":

        repayment_df = user_monthly.copy()

        repayment_df[
            "Repayment %"
        ] = (
            repayment_df[
                "repayment_ratio"
            ] * 100
        )

        repayment_fig = px.line(
            repayment_df,
            x="month",
            y="Repayment %",
            markers=True
        )

        repayment_fig.update_layout(
            yaxis_title="% of income",
            xaxis_title="Month"
        )

        st.plotly_chart(
            repayment_fig,
            use_container_width=True
        )


    else:

        cash_df = user_monthly[
            [
                "month",
                "income",
                "total_outflow",
                "surplus"
            ]
        ].copy()

        cash_fig = px.bar(

            cash_df,

            x="month",

            y=[
                "income",
                "total_outflow"
            ],

            barmode="group"
        )

        cash_fig.update_layout(
            xaxis_title="Month",
            yaxis_title="Amount (₹)"
        )

        st.plotly_chart(
            cash_fig,
            use_container_width=True
        )


        surplus_fig = px.line(
            cash_df,
            x="month",
            y="surplus",
            markers=True
        )

        surplus_fig.add_hline(
            y=0,
            line_dash="dash"
        )

        surplus_fig.update_layout(
            yaxis_title="Monthly Surplus (₹)",
            xaxis_title="Month"
        )

        st.plotly_chart(
            surplus_fig,
            use_container_width=True
        )


    # ----------------------------------------------
    # OVERSPENDING TIMELINE
    # ----------------------------------------------

    st.divider()

    st.subheader(
        "Your 12-Month Spending Timeline"
    )

    timeline = user_monthly.copy()

    timeline[
        "Status"
    ] = np.where(
        timeline[
            "overspending_flag"
        ] == 1,
        "Spent above income",
        "Within income"
    )

    timeline[
        "Position"
    ] = 1


    timeline_fig = px.scatter(

        timeline,

        x="month",
        y="Position",

        color="Status",

        size=[
            16
            for _ in range(
                len(timeline)
            )
        ],

        hover_data={
            "income": ":,.0f",
            "total_outflow": ":,.0f",
            "surplus": ":,.0f",
            "Position": False,
        }
    )

    timeline_fig.update_yaxes(
        visible=False
    )

    timeline_fig.update_layout(
        height=230,
        xaxis_title="Month"
    )

    st.plotly_chart(
        timeline_fig,
        use_container_width=True
    )


# ==================================================
# TAB 3 — COMPARE
# ==================================================

with compare_tab:

    st.header(
        "How do you compare?"
    )

    st.caption(
        f"You're being compared with other users in the "
        f"**{segment_label}** group."
    )


    segment_users = users[
        users["segment_name"]
        == user["segment_name"]
    ]


    compare_rows = [

        {
            "Metric":
                "Lifestyle Spending",

            "You":
                user["avg_desire_ratio"]
                * 100,

            "Similar Users":
                segment_users[
                    "avg_desire_ratio"
                ].mean()
                * 100
        },

        {
            "Metric":
                "Repayment Burden",

            "You":
                user["avg_repayment_ratio"]
                * 100,

            "Similar Users":
                segment_users[
                    "avg_repayment_ratio"
                ].mean()
                * 100
        },

        {
            "Metric":
                "Saving & Investing",

            "You":
                user["avg_investment_ratio"]
                * 100,

            "Similar Users":
                segment_users[
                    "avg_investment_ratio"
                ].mean()
                * 100
        },

        {
            "Metric":
                "Overall Spending",

            "You":
                user["avg_expense_ratio"]
                * 100,

            "Similar Users":
                segment_users[
                    "avg_expense_ratio"
                ].mean()
                * 100
        },

        {
            "Metric":
                "Income Variability",

            "You":
                user["income_cv"]
                * 100,

            "Similar Users":
                segment_users[
                    "income_cv"
                ].mean()
                * 100
        },
    ]


    compare_df = pd.DataFrame(
        compare_rows
    )

    compare_long = compare_df.melt(
        id_vars="Metric",
        var_name="Who",
        value_name="Percentage"
    )


    compare_fig = px.bar(
        compare_long,
        x="Metric",
        y="Percentage",
        color="Who",
        barmode="group"
    )

    compare_fig.update_layout(
        yaxis_title="Percentage (%)",
        xaxis_title=""
    )

    st.plotly_chart(
        compare_fig,
        use_container_width=True
    )


    # ----------------------------------------------
    # SIMPLE INSIGHT
    # ----------------------------------------------

    desire_difference = (
        user["avg_desire_ratio"]
        -
        segment_users[
            "avg_desire_ratio"
        ].mean()
    ) * 100


    if desire_difference > 2:

        st.info(
            f"Your lifestyle spending is about "
            f"**{desire_difference:.1f} percentage points higher** "
            "than similar users."
        )

    elif desire_difference < -2:

        st.success(
            f"Your lifestyle spending is about "
            f"**{abs(desire_difference):.1f} percentage points lower** "
            "than similar users."
        )

    else:

        st.info(
            "Your lifestyle spending is close to the average "
            "for users with similar behavior."
        )


    # ----------------------------------------------
    # POPULATION DISTRIBUTION
    # ----------------------------------------------

    st.divider()

    st.subheader(
        "Where do you stand in the wider population?"
    )


    distribution_choice = st.selectbox(
        "Choose a measure",
        [
            "Lifestyle Spending",
            "Saving & Investing",
            "Repayment Burden",
            "Overall Spending",
            "Income Variability",
        ]
    )


    distribution_map = {

        "Lifestyle Spending":
            "avg_desire_ratio",

        "Saving & Investing":
            "avg_investment_ratio",

        "Repayment Burden":
            "avg_repayment_ratio",

        "Overall Spending":
            "avg_expense_ratio",

        "Income Variability":
            "income_cv",
    }


    distribution_column = (
        distribution_map[
            distribution_choice
        ]
    )


    distribution_df = users[
        [distribution_column]
    ].copy()

    distribution_df[
        "Percentage"
    ] = (
        distribution_df[
            distribution_column
        ]
        * 100
    )


    hist_fig = px.histogram(
        distribution_df,
        x="Percentage",
        nbins=35
    )

    hist_fig.add_vline(

        x=(
            user[
                distribution_column
            ]
            * 100
        ),

        line_dash="dash",

        annotation_text="You"
    )

    hist_fig.update_layout(
        xaxis_title=f"{distribution_choice} (%)",
        yaxis_title="Users"
    )

    st.plotly_chart(
        hist_fig,
        use_container_width=True
    )


# ==================================================
# TAB 4 — IMPROVE
# ==================================================

with improve_tab:

    st.header(
        "Your Next Best Moves"
    )

    st.caption(
        "Recommendations are based on the financial patterns "
        "observed in your transaction history."
    )


    if user_recommendations.empty:

        st.info(
            "No specific recommendations are available."
        )

    else:

        for _, rec in user_recommendations.iterrows():

            rank = int(
                rec[
                    "recommendation_rank"
                ]
            )

            priority = int(
                rec[
                    "priority"
                ]
            )

            with st.container(
                border=True
            ):

                top_left, top_right = st.columns(
                    [5, 1]
                )

                with top_left:

                    st.markdown(
                        f"### {rank}. {rec['category']}"
                    )

                with top_right:

                    if priority == 1:
                        st.write(
                            "**High Priority**"
                        )

                    elif priority == 2:
                        st.write(
                            "**Priority**"
                        )

                    else:
                        st.write(
                            "**Suggestion**"
                        )

                st.write(
                    rec[
                        "recommendation"
                    ]
                )


    # ==================================================
    # WHAT-IF SIMULATOR
    # ==================================================

    st.divider()

    st.header(
        "What if I changed my habits?"
    )

    st.caption(
        "Explore a simplified scenario. This is an educational "
        "simulation, not a financial forecast or recommendation."
    )


    current_lifestyle_amount = (
        user["avg_desire_ratio"]
        * user["avg_income"]
    )


    max_reduction = int(
        max(
            0,
            current_lifestyle_amount
        )
    )


    max_savings_increase = int(
        user["avg_income"]
        * 0.20
    )


    simulator_left, simulator_right = st.columns(
        [1, 1.3]
    )


    with simulator_left:

        reduce_lifestyle = st.slider(
            "Reduce monthly lifestyle spending",
            min_value=0,
            max_value=max_reduction,
            value=0,
            step=500,
            format="₹%d"
        )


        increase_savings = st.slider(
            "Increase monthly savings",
            min_value=0,
            max_value=max_savings_increase,
            value=0,
            step=500,
            format="₹%d"
        )


    # ----------------------------------------------
    # SIMULATED RATIOS
    # ----------------------------------------------

    simulated_desire_ratio = max(
        0,
        user["avg_desire_ratio"]
        -
        (
            reduce_lifestyle
            / user["avg_income"]
        )
    )


    simulated_investment_ratio = (
        user["avg_investment_ratio"]
        +
        (
            increase_savings
            / user["avg_income"]
        )
    )


    simulated_expense_ratio = (
        user["avg_expense_ratio"]
        -
        (
            reduce_lifestyle
            / user["avg_income"]
        )
        +
        (
            increase_savings
            / user["avg_income"]
        )
    )


    simulated_surplus_ratio = (
        1
        -
        simulated_expense_ratio
    )


    simulated_spending_score = (
        spending_control_score(
            simulated_expense_ratio,
            user[
                "overspending_month_ratio"
            ]
        )
    )


    simulated_savings_score = (
        savings_score(
            simulated_investment_ratio,
            user[
                "investment_ratio_change_3m"
            ]
        )
    )


    simulated_stability = (
        stability_score(
            user["income_cv"],
            user[
                "expense_ratio_volatility"
            ],
            simulated_surplus_ratio
        )
    )


    simulated_total_score = (

        simulated_spending_score

        + simulated_savings_score

        + user[
            "debt_management_score"
        ]

        + simulated_stability
    )


    current_score = int(
        user["finpulse_score"]
    )


    simulated_total_score = int(
        simulated_total_score
    )


    with simulator_right:

        sim1, sim2 = st.columns(2)

        with sim1:

            st.metric(
                "Current Score",
                current_score
            )

        with sim2:

            st.metric(
                "Scenario Score",
                simulated_total_score,
                delta=(
                    simulated_total_score
                    - current_score
                )
            )


        current_surplus = (
            user["avg_surplus"]
        )


        simulated_surplus = (
            current_surplus
            + reduce_lifestyle
            - increase_savings
        )


        st.metric(
            "Estimated cash left after outflows",
            f"₹{simulated_surplus:,.0f}",
            delta=(
                simulated_surplus
                - current_surplus
            )
        )


        if (
            reduce_lifestyle == 0
            and increase_savings == 0
        ):

            st.info(
                "Move the sliders to explore a scenario."
            )

        else:

            st.write(
                "This scenario illustrates how changing lifestyle "
                "spending and saving allocation could affect the "
                "rule-based FinPulse indicators."
            )


# ==================================================
# TECHNICAL DETAILS
# ==================================================

st.divider()

with st.expander(
    "How FinPulse works behind the scenes"
):

    st.markdown(
        """
        **Transaction analytics**  
        SQLite and SQL transform transaction records into monthly
        and user-level behavioral features.

        **Behavioral segmentation**  
        KMeans clustering groups users with similar financial
        behavior. The user-facing money personality is based on
        this behavioral segment.

        **FinPulse Score**  
        A transparent rule-based framework evaluates spending
        control, savings behavior, repayment burden and financial
        stability.

        **Signals & recommendations**  
        Rule-based logic identifies notable patterns and converts
        them into understandable observations and action-oriented
        recommendations.

        **Important:** clustering, scoring and recommendations are
        separate components. A behavioral segment is not itself a
        financial-health rating.
        """
    )


# ==================================================
# DISCLAIMER
# ==================================================

st.caption(
    "FinPulse is an educational behavioral-finance prototype "
    "built using synthetic transaction-pattern data. The dashboard "
    "does not provide regulated financial, investment or credit advice."
)