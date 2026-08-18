DROP TABLE IF EXISTS monthly_features;

CREATE TABLE monthly_features AS

WITH monthly_base AS (
    SELECT
        user_id,
        substr(date, 1, 7) AS month,

        SUM(CASE WHEN label = 'Income'
                 THEN amount ELSE 0 END) AS income,

        SUM(CASE WHEN label = 'Essentials'
                 THEN amount ELSE 0 END) AS essentials,

        SUM(CASE WHEN label = 'Desire'
                 THEN amount ELSE 0 END) AS desire,

        SUM(CASE WHEN label = 'Repayment'
                 THEN amount ELSE 0 END) AS repayment,

        SUM(CASE WHEN label = 'Investment_Savings'
                 THEN amount ELSE 0 END) AS investment_savings,

        SUM(CASE WHEN label = 'Others'
                 THEN amount ELSE 0 END) AS others,

        COUNT(*) AS transaction_count,

        SUM(CASE WHEN txn_type = 'credit' THEN 1 ELSE 0 END)
            AS credit_transaction_count,

        SUM(CASE WHEN txn_type = 'debit' THEN 1 ELSE 0 END)
            AS debit_transaction_count

    FROM transactions

    GROUP BY
        user_id,
        substr(date, 1, 7)
),

calculated AS (
    SELECT
        *,

        essentials
        + desire
        + repayment
        + investment_savings
        + others AS total_outflow

    FROM monthly_base
)

SELECT
    *,

    income - total_outflow AS surplus,

    CASE
        WHEN income > 0 THEN essentials / income
        ELSE 0
    END AS essential_ratio,

    CASE
        WHEN income > 0 THEN desire / income
        ELSE 0
    END AS desire_ratio,

    CASE
        WHEN income > 0 THEN repayment / income
        ELSE 0
    END AS repayment_ratio,

    CASE
        WHEN income > 0 THEN investment_savings / income
        ELSE 0
    END AS investment_ratio,

    CASE
        WHEN income > 0 THEN others / income
        ELSE 0
    END AS other_ratio,

    CASE
        WHEN income > 0 THEN total_outflow / income
        ELSE 0
    END AS expense_to_income_ratio,

    CASE
        WHEN income > 0 THEN
            (income - total_outflow) / income
        ELSE 0
    END AS surplus_ratio,

    CASE
        WHEN total_outflow > income THEN 1
        ELSE 0
    END AS overspending_flag

FROM calculated;