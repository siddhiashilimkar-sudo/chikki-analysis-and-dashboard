-- Read-only reconciliation checks for the Power BI model.
-- Connect to maganlal_chikki_bi using a reporting account with SELECT privileges.
-- These queries do not create or modify objects/data.

USE maganlal_chikki_bi;

-- Core executive values. Keep each scalar at its stated business grain
SELECT
  (SELECT COALESCE(SUM(total), 0) FROM sales WHERE status = 'completed') AS total_revenue,
  (SELECT COUNT(*) FROM sales WHERE status = 'completed') AS total_sales_transactions,
  (SELECT COALESCE(SUM(si.quantity), 0)
   FROM sale_items si JOIN sales s ON s.sale_id = si.sale_id
   WHERE s.status = 'completed') AS total_quantity_sold,
  (SELECT COALESCE(SUM(si.quantity * si.unit_cost), 0)
   FROM sale_items si JOIN sales s ON s.sale_id = si.sale_id
   WHERE s.status = 'completed') AS total_cogs,
  (SELECT COALESCE(SUM(amount), 0) FROM expenses) AS operating_expenses,
  (SELECT COALESCE(SUM(current_stock * purchase_price), 0) FROM products) AS inventory_value,
  (SELECT COUNT(*) FROM vw_inventory_status
   WHERE stock_status IN ('Low', 'Critical', 'Out of stock')) AS low_stock_products,
  (SELECT COALESCE(SUM(amount), 0) FROM payments WHERE status = 'paid') AS paid_recorded_payments,
  (SELECT COALESCE(SUM(amount), 0) FROM payments WHERE status = 'pending') AS pending_recorded_payments;

-- Profit formulas must reconcile with the measures and financial view
SELECT revenue, cogs, operating_expenses, gross_profit, net_profit,
       gross_profit / NULLIF(revenue, 0) AS gross_margin,
       net_profit / NULLIF(revenue, 0) AS net_margin
FROM vw_financial_summary;

-- Daily view reconciles to completed sale headers and sale-item costs/quantities
SELECT SUM(total_sales) AS transactions,
       SUM(revenue) AS revenue,
       SUM(quantity) AS quantity_sold,
       SUM(cogs) AS cogs
FROM vw_daily_sales;

-- Return metrics: the date summary intentionally has no return-count/product/reason grain
SELECT COUNT(*) AS return_count,
       (SELECT COALESCE(SUM(quantity), 0) FROM return_items) AS returned_quantity,
       (SELECT COALESCE(SUM(quantity * unit_value), 0) FROM return_items) AS return_value
FROM returns;

-- Confirm the model objects remain present without modifying them
SHOW FULL TABLES WHERE Table_type = 'VIEW';
