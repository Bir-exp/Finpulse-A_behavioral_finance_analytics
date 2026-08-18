DROP TABLE IF EXISTS user_trends;

CREATE TABLE user_trends AS

WITH ranked_months AS (

    SELECT
        *,

        ROW_NUMBER() OVER (
            PARTITION BY user_id
            ORDER BY month DESC
        ) AS month_rank

    FROM monthly_features
),

recent_six AS (

    SELECT *
    FROM ranked_months
    WHERE month_rank <= 6
),

trend_metrics AS (

    SELECT
        user_id,

        COUNT(*) AS observed_recent_months,

        AVG(
            CASE
                WHEN month_rank BETWEEN 1 AND 3
                THEN income
            END
        )
        -
        AVG(
            CASE
                WHEN month_rank BETWEEN 4 AND 6
                THEN income
            END
        ) AS income_change_3m,

        AVG(
            CASE
                WHEN month_rank BETWEEN 1 AND 3
                THEN desire_ratio
            END
        )
        -
        AVG(
            CASE
                WHEN month_rank BETWEEN 4 AND 6
                THEN desire_ratio
            END
        ) AS desire_ratio_change_3m,

        AVG(
            CASE
                WHEN month_rank BETWEEN 1 AND 3
                THEN repayment_ratio
            END
        )
        -
        AVG(
            CASE
                WHEN month_rank BETWEEN 4 AND 6
                THEN repayment_ratio
            END
        ) AS repayment_ratio_change_3m,

        AVG(
            CASE
                WHEN month_rank BETWEEN 1 AND 3
                THEN investment_ratio
            END
        )
        -
        AVG(
            CASE
                WHEN month_rank BETWEEN 4 AND 6
                THEN investment_ratio
            END
        ) AS investment_ratio_change_3m,

        AVG(
            CASE
                WHEN month_rank BETWEEN 1 AND 3
                THEN expense_to_income_ratio
            END
        )
        -
        AVG(
            CASE
                WHEN month_rank BETWEEN 4 AND 6
                THEN expense_to_income_ratio
            END
        ) AS expense_ratio_change_3m,

        AVG(
            CASE
                WHEN month_rank BETWEEN 1 AND 3
                THEN surplus_ratio
            END
        )
        -
        AVG(
            CASE
                WHEN month_rank BETWEEN 4 AND 6
                THEN surplus_ratio
            END
        ) AS surplus_ratio_change_3m

    FROM recent_six

    GROUP BY user_id
)

SELECT
    user_id,
    income_change_3m,
    desire_ratio_change_3m,
    repayment_ratio_change_3m,
    investment_ratio_change_3m,
    expense_ratio_change_3m,
    surplus_ratio_change_3m

FROM trend_metrics

WHERE observed_recent_months >= 6;