/*
Credit Portfolio Risk & Strategy Simulator - SQL Query Library

This file contains optimized SQL queries for portfolio analysis and reporting.
Queries are organized by functional area and include performance optimization hints.

Database Support: SQLite (primary), PostgreSQL (secondary)
Author: Credit Risk Analytics Team
Date: 2024
*/

-- =============================================================================
-- PORTFOLIO OVERVIEW QUERIES
-- =============================================================================

-- Query 1: Portfolio Summary Statistics
-- Usage: Dashboard overview, executive reporting
-- Returns: Key portfolio metrics across all approved customers
SELECT 
    COUNT(*) as total_customers,
    COUNT(CASE WHEN acceptance_decision = 'Approved' THEN 1 END) as approved_customers,
    ROUND(COUNT(CASE WHEN acceptance_decision = 'Approved' THEN 1 END) * 100.0 / COUNT(*), 2) as approval_rate_pct,
    ROUND(SUM(CASE WHEN acceptance_decision = 'Approved' THEN balance ELSE 0 END) / 1000000.0, 2) as portfolio_balance_millions,
    ROUND(SUM(CASE WHEN acceptance_decision = 'Approved' THEN credit_limit ELSE 0 END) / 1000000.0, 2) as total_limits_millions,
    ROUND(AVG(CASE WHEN acceptance_decision = 'Approved' THEN utilization_rate END), 1) as avg_utilization_pct,
    ROUND(AVG(CASE WHEN acceptance_decision = 'Approved' THEN application_score END), 0) as avg_credit_score,
    COUNT(CASE WHEN acceptance_decision = 'Approved' AND delinquency_status > 0 THEN 1 END) * 100.0 / 
        NULLIF(COUNT(CASE WHEN acceptance_decision = 'Approved' THEN 1 END), 0) as delinquency_rate_pct
FROM credit_portfolio;

-- Query 2: Portfolio Balance Distribution by Credit Limit Bands
-- Usage: Risk appetite analysis, limit optimization
SELECT 
    CASE 
        WHEN credit_limit < 1000 THEN '£0-1k'
        WHEN credit_limit < 5000 THEN '£1k-5k'
        WHEN credit_limit < 10000 THEN '£5k-10k'
        WHEN credit_limit < 20000 THEN '£10k-20k'
        ELSE '£20k+'
    END as limit_band,
    COUNT(*) as customer_count,
    ROUND(SUM(balance) / 1000000.0, 2) as total_balance_millions,
    ROUND(AVG(balance), 0) as avg_balance,
    ROUND(AVG(utilization_rate), 1) as avg_utilization_pct,
    COUNT(CASE WHEN delinquency_status > 0 THEN 1 END) * 100.0 / COUNT(*) as delinquency_rate_pct
FROM credit_portfolio 
WHERE acceptance_decision = 'Approved'
GROUP BY 
    CASE 
        WHEN credit_limit < 1000 THEN '£0-1k'
        WHEN credit_limit < 5000 THEN '£1k-5k'
        WHEN credit_limit < 10000 THEN '£5k-10k'
        WHEN credit_limit < 20000 THEN '£10k-20k'
        ELSE '£20k+'
    END
ORDER BY MIN(credit_limit);

-- =============================================================================
-- RISK ANALYSIS QUERIES
-- =============================================================================

-- Query 3: Top 10 Delinquent Customer Segments
-- Usage: Risk monitoring, collection prioritization
-- Returns: Highest risk segments by customer count and exposure
SELECT 
    region,
    income_band,
    CASE 
        WHEN application_score < 500 THEN 'Subprime'
        WHEN application_score < 650 THEN 'Near Prime'
        WHEN application_score < 750 THEN 'Prime'
        ELSE 'Super Prime'
    END as credit_grade,
    COUNT(*) as customers,
    ROUND(SUM(balance) / 1000.0, 0) as total_balance_thousands,
    COUNT(CASE WHEN delinquency_status > 0 THEN 1 END) as delinquent_customers,
    ROUND(COUNT(CASE WHEN delinquency_status > 0 THEN 1 END) * 100.0 / COUNT(*), 1) as delinquency_rate_pct,
    ROUND(SUM(CASE WHEN delinquency_status > 0 THEN balance ELSE 0 END) / 1000.0, 0) as delinquent_balance_thousands
FROM credit_portfolio 
WHERE acceptance_decision = 'Approved'
GROUP BY region, income_band, 
    CASE 
        WHEN application_score < 500 THEN 'Subprime'
        WHEN application_score < 650 THEN 'Near Prime'
        WHEN application_score < 750 THEN 'Prime'
        ELSE 'Super Prime'
    END
HAVING COUNT(CASE WHEN delinquency_status > 0 THEN 1 END) > 0
ORDER BY delinquency_rate_pct DESC, total_balance_thousands DESC
LIMIT 10;

-- Query 4: Regional Delinquency Analysis
-- Usage: Geographic risk assessment, regional strategy
-- Returns: Risk metrics by UK region
SELECT 
    region,
    COUNT(*) as total_customers,
    ROUND(SUM(balance) / 1000000.0, 2) as portfolio_balance_millions,
    ROUND(AVG(application_score), 0) as avg_credit_score,
    ROUND(AVG(utilization_rate), 1) as avg_utilization_pct,
    COUNT(CASE WHEN delinquency_status > 0 THEN 1 END) as delinquent_customers,
    ROUND(COUNT(CASE WHEN delinquency_status > 0 THEN 1 END) * 100.0 / COUNT(*), 2) as delinquency_rate_pct,
    COUNT(CASE WHEN delinquency_status >= 30 THEN 1 END) as dpd_30_plus,
    COUNT(CASE WHEN delinquency_status >= 90 THEN 1 END) as dpd_90_plus
FROM credit_portfolio 
WHERE acceptance_decision = 'Approved'
GROUP BY region
ORDER BY delinquency_rate_pct DESC;

-- Query 5: Credit Score Distribution and Risk Profile
-- Usage: Underwriting analysis, score threshold optimization
-- Returns: Portfolio quality metrics by credit score bands
SELECT 
    CASE 
        WHEN application_score < 500 THEN '300-499'
        WHEN application_score < 600 THEN '500-599'
        WHEN application_score < 650 THEN '600-649'
        WHEN application_score < 700 THEN '650-699'
        WHEN application_score < 750 THEN '700-749'
        ELSE '750+'
    END as score_band,
    COUNT(*) as customers,
    ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM credit_portfolio WHERE acceptance_decision = 'Approved'), 1) as portfolio_pct,
    ROUND(SUM(balance) / 1000000.0, 2) as balance_millions,
    ROUND(AVG(credit_limit), 0) as avg_credit_limit,
    ROUND(AVG(utilization_rate), 1) as avg_utilization_pct,
    COUNT(CASE WHEN delinquency_status > 0 THEN 1 END) * 100.0 / COUNT(*) as delinquency_rate_pct,
    COUNT(CASE WHEN marketing_offer_response = 'Yes' THEN 1 END) * 100.0 / COUNT(*) as response_rate_pct
FROM credit_portfolio 
WHERE acceptance_decision = 'Approved'
GROUP BY 
    CASE 
        WHEN application_score < 500 THEN '300-499'
        WHEN application_score < 600 THEN '500-599'
        WHEN application_score < 650 THEN '600-649'
        WHEN application_score < 700 THEN '650-699'
        WHEN application_score < 750 THEN '700-749'
        ELSE '750+'
    END
ORDER BY MIN(application_score);

-- =============================================================================
-- RISK METRICS WITH ADVANCED CALCULATIONS
-- =============================================================================

-- Query 6: Portfolio Expected Loss Analysis (requires risk metrics table)
-- Usage: Economic capital calculation, IFRS9 reporting
-- Returns: PD/LGD/EAD breakdown by customer segments
SELECT 
    income_band,
    risk_segment,
    COUNT(*) as customers,
    ROUND(SUM(ead) / 1000000.0, 2) as total_ead_millions,
    ROUND(AVG(pd_12m) * 100, 2) as avg_pd_pct,
    ROUND(AVG(lgd) * 100, 1) as avg_lgd_pct,
    ROUND(SUM(expected_loss) / 1000.0, 0) as total_expected_loss_thousands,
    ROUND(SUM(expected_loss) / SUM(ead) * 100, 3) as loss_rate_pct
FROM portfolio_with_risk_metrics 
WHERE ead > 0
GROUP BY income_band, risk_segment
ORDER BY loss_rate_pct DESC;

-- Query 7: High Risk Customer Alert List
-- Usage: Collections workflow, account management prioritization  
-- Returns: Customers requiring immediate attention
SELECT 
    p.customer_id,
    p.region,
    p.income_band,
    p.application_score,
    p.credit_limit,
    p.balance,
    p.utilization_rate,
    p.delinquency_status,
    r.risk_score,
    r.risk_segment,
    r.expected_loss,
    ROUND(r.pd_12m * 100, 1) as pd_12m_pct
FROM credit_portfolio p
JOIN portfolio_with_risk_metrics r ON p.customer_id = r.customer_id
WHERE r.risk_segment IN ('High Risk', 'Very High Risk')
    AND p.acceptance_decision = 'Approved'
    AND p.balance > 1000  -- Focus on material balances
ORDER BY r.risk_score DESC, r.expected_loss DESC
LIMIT 100;

-- =============================================================================
-- PORTFOLIO PROFITABILITY QUERIES  
-- =============================================================================

-- Query 8: Portfolio Profitability Summary
-- Usage: Management reporting, strategy assessment
-- Returns: Revenue, costs, and profit by customer segments
SELECT 
    income_band,
    COUNT(*) as customers,
    ROUND(SUM(balance) / 1000000.0, 2) as portfolio_balance_millions,
    -- Estimated monthly revenue (18% APR)
    ROUND(SUM(balance) * 0.18 / 12 / 1000.0, 0) as monthly_revenue_thousands,
    -- Estimated monthly expected loss
    ROUND(SUM(COALESCE(r.expected_loss, 0)) / 1000.0, 0) as monthly_expected_loss_thousands,
    -- Net income estimate
    ROUND((SUM(balance) * 0.18 / 12 - SUM(COALESCE(r.expected_loss, 0))) / 1000.0, 0) as monthly_net_income_thousands,
    -- ROA calculation
    ROUND((SUM(balance) * 0.18 / 12 - SUM(COALESCE(r.expected_loss, 0))) / SUM(balance) * 100, 2) as roa_pct
FROM credit_portfolio p
LEFT JOIN portfolio_with_risk_metrics r ON p.customer_id = r.customer_id
WHERE p.acceptance_decision = 'Approved' AND p.balance > 0
GROUP BY income_band
ORDER BY roa_pct DESC;

-- =============================================================================
-- STRATEGY SIMULATION SUPPORT QUERIES
-- =============================================================================

-- Query 9: Score Threshold Impact Analysis
-- Usage: Strategy simulation, acceptance criteria optimization
-- Returns: Portfolio metrics under different score thresholds
WITH score_thresholds AS (
    SELECT 500 as min_score UNION ALL
    SELECT 550 UNION ALL
    SELECT 600 UNION ALL 
    SELECT 650 UNION ALL
    SELECT 700
)
SELECT 
    st.min_score as score_threshold,
    COUNT(*) as eligible_applications,
    COUNT(CASE WHEN p.acceptance_decision = 'Approved' THEN 1 END) as would_approve,
    ROUND(COUNT(CASE WHEN p.acceptance_decision = 'Approved' THEN 1 END) * 100.0 / COUNT(*), 1) as approval_rate_pct,
    ROUND(SUM(CASE WHEN p.acceptance_decision = 'Approved' THEN p.balance ELSE 0 END) / 1000000.0, 2) as portfolio_balance_millions,
    ROUND(AVG(CASE WHEN p.acceptance_decision = 'Approved' THEN p.application_score END), 0) as avg_approved_score,
    COUNT(CASE WHEN p.acceptance_decision = 'Approved' AND p.delinquency_status > 0 THEN 1 END) * 100.0 / 
        NULLIF(COUNT(CASE WHEN p.acceptance_decision = 'Approved' THEN 1 END), 0) as delinquency_rate_pct
FROM score_thresholds st
CROSS JOIN credit_portfolio p
WHERE p.application_score >= st.min_score
GROUP BY st.min_score
ORDER BY st.min_score;

-- Query 10: Income Band Targeting Analysis  
-- Usage: Customer segmentation strategy, marketing focus
-- Returns: Performance metrics by income targeting scenarios
SELECT 
    'All Bands' as strategy,
    COUNT(*) as customers,
    ROUND(SUM(balance) / 1000000.0, 2) as balance_millions,
    ROUND(AVG(application_score), 0) as avg_score,
    COUNT(CASE WHEN delinquency_status > 0 THEN 1 END) * 100.0 / COUNT(*) as delinquency_rate_pct,
    ROUND(AVG(utilization_rate), 1) as avg_utilization_pct
FROM credit_portfolio 
WHERE acceptance_decision = 'Approved'

UNION ALL

SELECT 
    'High Income Only' as strategy,
    COUNT(*) as customers,
    ROUND(SUM(balance) / 1000000.0, 2) as balance_millions,
    ROUND(AVG(application_score), 0) as avg_score,
    COUNT(CASE WHEN delinquency_status > 0 THEN 1 END) * 100.0 / COUNT(*) as delinquency_rate_pct,
    ROUND(AVG(utilization_rate), 1) as avg_utilization_pct
FROM credit_portfolio 
WHERE acceptance_decision = 'Approved' AND income_band = 'High'

UNION ALL

SELECT 
    'Medium & High Income' as strategy,
    COUNT(*) as customers,
    ROUND(SUM(balance) / 1000000.0, 2) as balance_millions,
    ROUND(AVG(application_score), 0) as avg_score,
    COUNT(CASE WHEN delinquency_status > 0 THEN 1 END) * 100.0 / COUNT(*) as delinquency_rate_pct,
    ROUND(AVG(utilization_rate), 1) as avg_utilization_pct
FROM credit_portfolio 
WHERE acceptance_decision = 'Approved' AND income_band IN ('Medium', 'High');

-- =============================================================================
-- OPERATIONAL QUERIES
-- =============================================================================

-- Query 11: Daily Risk Monitoring Dashboard
-- Usage: Operations dashboard, daily risk reporting
-- Returns: Key risk indicators for monitoring
SELECT 
    'Portfolio Overview' as metric_category,
    'Total Customers' as metric_name,
    COUNT(*) as metric_value,
    '' as metric_unit
FROM credit_portfolio WHERE acceptance_decision = 'Approved'

UNION ALL

SELECT 
    'Portfolio Overview',
    'Portfolio Balance',
    ROUND(SUM(balance) / 1000000.0, 2),
    '£M'
FROM credit_portfolio WHERE acceptance_decision = 'Approved'

UNION ALL

SELECT 
    'Risk Metrics',
    'Delinquency Rate',
    ROUND(COUNT(CASE WHEN delinquency_status > 0 THEN 1 END) * 100.0 / COUNT(*), 2),
    '%'
FROM credit_portfolio WHERE acceptance_decision = 'Approved'

UNION ALL

SELECT 
    'Risk Metrics',
    '30+ DPD Rate', 
    ROUND(COUNT(CASE WHEN delinquency_status >= 30 THEN 1 END) * 100.0 / COUNT(*), 2),
    '%'
FROM credit_portfolio WHERE acceptance_decision = 'Approved'

UNION ALL

SELECT 
    'Risk Metrics',
    '90+ DPD Rate',
    ROUND(COUNT(CASE WHEN delinquency_status >= 90 THEN 1 END) * 100.0 / COUNT(*), 2), 
    '%'
FROM credit_portfolio WHERE acceptance_decision = 'Approved';

-- Query 12: Portfolio Vintage Analysis (Simulated)
-- Usage: Portfolio performance trending, cohort analysis
-- Returns: Delinquency rates by simulated origination periods
WITH vintage_months AS (
    SELECT 
        customer_id,
        CASE 
            WHEN customer_id % 12 = 0 THEN '2024-01'
            WHEN customer_id % 12 = 1 THEN '2024-02' 
            WHEN customer_id % 12 = 2 THEN '2024-03'
            WHEN customer_id % 12 = 3 THEN '2024-04'
            WHEN customer_id % 12 = 4 THEN '2024-05'
            WHEN customer_id % 12 = 5 THEN '2024-06'
            WHEN customer_id % 12 = 6 THEN '2024-07'
            WHEN customer_id % 12 = 7 THEN '2024-08'
            WHEN customer_id % 12 = 8 THEN '2024-09'
            WHEN customer_id % 12 = 9 THEN '2024-10'
            WHEN customer_id % 12 = 10 THEN '2024-11'
            ELSE '2024-12'
        END as vintage_month
    FROM credit_portfolio
    WHERE acceptance_decision = 'Approved'
)
SELECT 
    v.vintage_month,
    COUNT(*) as customers,
    ROUND(SUM(p.balance) / 1000000.0, 2) as balance_millions,
    ROUND(AVG(p.application_score), 0) as avg_score,
    COUNT(CASE WHEN p.delinquency_status > 0 THEN 1 END) as delinquent_count,
    ROUND(COUNT(CASE WHEN p.delinquency_status > 0 THEN 1 END) * 100.0 / COUNT(*), 2) as delinquency_rate_pct
FROM vintage_months v
JOIN credit_portfolio p ON v.customer_id = p.customer_id
GROUP BY v.vintage_month
ORDER BY v.vintage_month;

-- =============================================================================
-- DATA VALIDATION QUERIES
-- =============================================================================

-- Query 13: Data Quality Checks
-- Usage: Data validation, ETL monitoring
-- Returns: Data quality metrics and anomaly flags
SELECT 
    'Data Completeness' as check_category,
    'Total Records' as check_name,
    COUNT(*) as check_value,
    CASE WHEN COUNT(*) > 0 THEN 'PASS' ELSE 'FAIL' END as status
FROM credit_portfolio

UNION ALL

SELECT 
    'Data Completeness',
    'Records with Customer ID',
    COUNT(*),
    CASE WHEN COUNT(*) = (SELECT COUNT(*) FROM credit_portfolio) THEN 'PASS' ELSE 'FAIL' END
FROM credit_portfolio WHERE customer_id IS NOT NULL

UNION ALL

SELECT 
    'Data Quality',
    'Valid Credit Scores',
    COUNT(*),
    CASE WHEN COUNT(*) > 0 THEN 'PASS' ELSE 'FAIL' END
FROM credit_portfolio WHERE application_score BETWEEN 300 AND 900

UNION ALL

SELECT 
    'Data Quality', 
    'Negative Balances',
    COUNT(*),
    CASE WHEN COUNT(*) = 0 THEN 'PASS' ELSE 'FAIL' END  
FROM credit_portfolio WHERE balance < 0 AND acceptance_decision = 'Approved'

UNION ALL

SELECT 
    'Business Rules',
    'Utilization > 100%',
    COUNT(*),
    CASE WHEN COUNT(*) = 0 THEN 'PASS' ELSE 'FAIL' END
FROM credit_portfolio WHERE utilization_rate > 100 AND acceptance_decision = 'Approved';

-- =============================================================================
-- PERFORMANCE OPTIMIZATION HINTS
-- =============================================================================

/*
INDEX RECOMMENDATIONS:
1. CREATE INDEX idx_credit_portfolio_acceptance_decision ON credit_portfolio(acceptance_decision);
2. CREATE INDEX idx_credit_portfolio_delinquency_status ON credit_portfolio(delinquency_status);  
3. CREATE INDEX idx_credit_portfolio_region ON credit_portfolio(region);
4. CREATE INDEX idx_credit_portfolio_income_band ON credit_portfolio(income_band);
5. CREATE INDEX idx_credit_portfolio_application_score ON credit_portfolio(application_score);
6. CREATE INDEX idx_portfolio_risk_metrics_risk_segment ON portfolio_with_risk_metrics(risk_segment);

QUERY OPTIMIZATION TIPS:
- Use WHERE clauses to filter early in the query execution
- Consider partitioning large tables by date or region
- Use appropriate data types (INTEGER vs TEXT for IDs)
- Regularly analyze query execution plans
- Consider materialized views for complex aggregations
*/