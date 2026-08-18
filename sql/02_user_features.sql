DROP TABLE IF EXISTS user_features_base;

CREATE TABLE user_features_base AS

SELECT
    user_id,

    COUNT(*) AS months_observed,

    AVG(income) AS avg_income,

    AVG(essential_ratio) AS avg_essential_ratio,
    AVG(desire_ratio) AS avg_desire_ratio,
    AVG(repayment_ratio) AS avg_repayment_ratio,
    AVG(investment_ratio) AS avg_investment_ratio,
    AVG(other_ratio) AS avg_other_ratio,

    AVG(expense_to_income_ratio) AS avg_expense_ratio,

    AVG(surplus) AS avg_surplus,
    AVG(surplus_ratio) AS avg_surplus_ratio,

    AVG(transaction_count) AS avg_monthly_transactions,

    SUM(overspending_flag) AS overspending_months,

    CAST(SUM(overspending_flag) AS REAL)
        / COUNT(*) AS overspending_month_ratio

FROM monthly_features

GROUP BY user_id;