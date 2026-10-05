# Power BI report construction guide

This is the page-by-page specification for the existing MySQL database. It is prepared for a manual Power BI Desktop build because Power BI Desktop is not installed/running in this environment. It does not claim that a `.pbix` was created. Follow `data_model.md` first, then create the report pages below. Use `dax_measures.md` for measures and `validation_queries.sql` to check source totals.

## Connection and model setup

1. Open Power BI Desktop and choose **Home → Get data → More → Database → MySQL database**.
2. Enter server `localhost:3306` and database `maganlal_chikki_bi` (if the dialog accepts server and port separately, use `localhost` and `3306`).
3. Choose **Import**. Authenticate locally using a read-only MySQL reporting credential. Never paste a database password into a report, source file, or chat.
4. Select the 15 existing reporting views and the optional existing dimension/transaction tables listed in `data_model.md`. Do not import the legacy database.
5. Apply data types and INR formatting; create `DateTable`, mark it as the date table, and add the verified relationships in `data_model.md`.
6. Create the measures from `dax_measures.md`. Add an “All time” label to visuals using lifetime aggregate views.
7. Add a small note to the report canvas: **Source: MySQL — maganlal_chikki_bi | Mode: Import / refresh-based | Data classification: DEMO DATA**. The note describes the source and mode; it must not contain a fabricated refresh timestamp.

## Shared design system

- Canvas: 16:9 widescreen. Use a consistent header with the Maganlal Chikki name and page title.
- Suggested restrained palette: deep green `#14532D` for primary, warm saffron `#D97706` for highlight, cream `#FFF9ED` for canvas, charcoal `#1F2937` for text, muted grey `#64748B` for labels, red `#B91C1C` for out-of-stock/error state.
- Use one sans-serif font, consistent 16–24 px page titles, compact visual titles, aligned KPI cards, and moderate white space. Avoid 3D charts.
- Currency: ₹ with two decimals. Percentages: two decimals. Quantity/stock: up to two decimals. Hide technical IDs from end-user visuals.
- Format conditional status colors consistently: Healthy green, Low/Critical amber, Out of stock red; paid green, partial amber, pending red. Retain text labels so color is not the only cue.
- Put a discreet footer note on every page: **Power BI is refreshed from MySQL; this report is not an instant live feed.**

## Page 1 — Executive Overview

**Title:** Maganlal Chikki — Executive Business Overview

KPI cards: Total Revenue, Total Sales Transactions, Total Quantity Sold, Average Order Value, Gross Profit, Net Profit, Gross Margin %, Net Margin %, Inventory Value, Low Stock Products, Pending Payments.

Visuals:

1. Line chart: DateTable[Date] by Total Revenue.
2. Line chart: DateTable[Date] by Total Sales Transactions.
3. Line chart: DateTable[Date] by Gross Profit (use `vw_profit_trend` or daily revenue/COGS; avoid combining duplicate fact sources in one sum).
4. Bar chart: `vw_category_sales[category]` by its revenue; title it **Category Revenue — All Time**.
5. Bar chart: `vw_product_sales[product_name]` by Product Revenue (All Time), Top N filter; title **Highest Revenue Products — All Time**.
6. Donut/stacked bar: `vw_inventory_status[stock_status]` with product count.

Slicers: Date (date-based visuals), Category and Product (product visuals). Because category/product summary views have no date field, clearly mark those visuals All Time and do not imply the Date slicer changes them. Source/mode note as above.

## Page 2 — Sales Analysis

Daily revenue/transaction trend line from `vw_daily_sales`; column chart for `vw_weekly_sales` by year_week; monthly column chart for `vw_monthly_sales` by month_start; category and product revenue using their views; KPI cards for AOV and transactions; optional transaction table from `sales` with sale_code, sale_date, status, total.

Slicers: Date for daily/header transaction visuals, Product/Category for product-level visuals. Keep weekly/monthly aggregate charts labeled separately and disconnected until their keys are transformed and boundary behavior tested. `vw_product_sales` has lifetime grain; title corresponding charts **All Time**. Do not show daily quantity from an aggregate view unless its grain supports the chosen axis.

## Page 3 — Product Analysis

Build a product table using `products` attributes (product name/code, category, net weight, unit, selling price, purchase price, current stock) with `vw_product_sales` quantity, revenue, COGS, and calculated gross profit. Add bar charts for quantity/revenue/profit, contribution by product, and a factual **Lowest Sales Quantity — All Time** table; avoid arbitrary “best” or “worst” judgments. Include a product slicer and a category slicer. These sales metrics are lifetime totals because the view has no sale date. For a date-sensitive product view, use `sales` → `sale_items` with Product and Date dimensions; label line-item revenue separately from the reconciled header revenue.

## Page 4 — Inventory Intelligence

KPI cards: Inventory Value, Low Stock Products, Out of Stock Products. Table from `vw_inventory_status` plus product details: product, category, current stock, minimum stock, reorder level, stock value, stock status. Bar chart: stock and value by product/category. Add `inventory_movements` by movement date/type for movement trends. Include a **Data-driven Reorder Recommendations** table from `vw_reorder_recommendations`: product, current stock and reorder level from `products`, days of stock, suggested quantity, lead time, generated time.

The present recommendation view does not contain average demand, safety stock, or reason. Do not add invented values. Current inventory status is a snapshot; a date slicer does not reconstruct historical stock.

## Page 5 — Purchases & Supplier Analysis

KPI cards: Purchase Value, Purchase Quantity, distinct purchase count. Use `purchases` and `purchase_items` for date trend, supplier/category product detail, and status; use `suppliers` for supplier name and lead time. Use `vw_supplier_purchases` for a supplier lifetime summary table with purchase count, purchase value, and purchase quantity. Include Date, Supplier, and Product slicers on the transaction-based visuals. Do not label a supplier winner or rank its overall quality; present factual metric values. Do not combine the supplier lifetime aggregate with dated purchase totals.

## Page 6 — Finance & Profitability

KPI cards: Revenue, COGS, Gross Profit, Gross Margin %, Operating Expenses, Net Profit, Net Margin %, Payments, Pending Payments. Use Date-based lines for revenue/COGS/profit via `vw_profit_trend`; expenses by category and date via `vw_expense_summary`; payment totals/status by date via `vw_payment_summary`. Use `vw_financial_summary` only as an unfiltered single-row reconciliation. Payment facts are polymorphically associated and include more than customer sale collections; title them **Recorded Payments** and **Pending Recorded Payments**, not “cash collected from sales” unless filtered and reconciled by related_type.

## Page 7 — Sales & Demand Forecast

Use `vw_forecast`: product, period_start, horizon_days, forecast_quantity, method, generated_at. Chart forecast quantity by period_start and product. If actual sales are included, use an explicit legend/series and distinct line style/color; do not blend forecast and actual into one measure. Add prominent label **FORECAST / ESTIMATED** and note: **Forecast values are estimates based on historical data and should not be treated as actual sales.** Use Product and forecast period filters. If no forecast records exist after refresh, show an informative empty state rather than a zero forecast line.

## Page 8 — Data-Driven Business Insights

Use existing `business_insights` columns `generated_at`, `type`, `title`, `description`, `severity`, `related_metric`, `supporting_value`, plus dashboard summary metrics. Show insights as a filterable table/card list and use supporting-value charts only when measures share meaningful units. Label anomalies **Potential anomaly** and forecasts estimated. Do not make fraud, theft, employee misconduct, or guaranteed outcome claims. Use generated_at as the insight creation timestamp only; do not label it a database/report refresh time.

## Page 9 — Returns Analysis

KPI cards: Return Count (`returns` table), Returned Quantity, Return Value from `vw_returns_summary`. Use a DateTable trend by return date; use `returns` and `return_items` for product, reason, and sale detail. Add product/category visuals through `products`; use reason as factual recorded text, grouping blank reasons as **Not provided**. Optional return quantity rate = return quantity / quantity sold; state the numerator/denominator and date context. `vw_returns_summary` is date aggregate and has no product/reason columns; don’t fabricate those breakdowns from it.

## Optional drill-through and tooltips

- **Product Details** drill-through: product attributes, lifetime sales, current inventory, purchases, returns, forecast/reorder records. Keep each figure labeled by its grain/time context.
- Product tooltip: category, net weight, selling price, current stock, all-time quantity/revenue.
- Inventory tooltip: status, stock, minimum/reorder level, value, lead time/suggestion where available.
- Avoid relationships added solely to enable a tooltip; follow model cardinalities.

## Validation workflow

1. Run the read-only SQL checks in `validation_queries.sql` against `maganlal_chikki_bi`.
2. Refresh the Power BI Import model and compare unfiltered KPI results to SQL. The previous direct MySQL validation for this project returned revenue ₹378,579.98; 1,500 completed transactions; quantity 3,915; COGS ₹242,116.00; gross profit ₹136,463.98; operating expenses ₹99,156.61; net profit ₹37,307.37; gross margin 36.05%; net margin 9.85%; inventory value ₹187,789.00; 6 products at/below reorder level; pending recorded payments ₹283,756.25; 60 returns; returned quantity 116; return value ₹13,110.63. These are observed demo-source validation values only, not values to encode in DAX or visuals.
3. Check selected date slices against the same date-filtered SQL. Confirm that Date filters do not appear to change lifetime aggregates or current-stock snapshots.
4. Test Category and Product slicers on product/detail visuals; test Supplier on purchase visuals. Check that no ambiguous relationship warnings appear.
5. Reconcile sales header totals against product line revenue and document any tax/discount/rounding difference. Do not change the business definition just to force equality.
6. Confirm empty forecast and return-reason states remain clear if source data is absent.

## Refresh and publication

In Desktop use **Home → Refresh** after the source database is updated. Save the report and include a visible **Import / refresh-based** note. No refresh timestamp should be displayed unless implemented from a trustworthy refresh metadata source.

For Power BI Service, publish only after the organization approves the report and credential method. If the MySQL host is only on a shop LAN, configure a supported on-premises data gateway on an always-on reachable machine, map the data source/credentials in the Service, and test a refresh there. Licensing/capacity and connector support determine available schedule and latency. Desktop refresh and Service scheduled refresh are not instant streaming.
