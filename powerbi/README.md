# Maganlal Chikki Power BI layer

This folder contains the build package for a Power BI report backed by the existing MySQL database `maganlal_chikki_bi`. It reuses the existing 15 reporting views and documents their actual MySQL column names, types, and grains. The existing FastAPI/React dashboard remains the near-real-time operational UI. Power BI Desktop uses Import/refresh; it is not an instant live feed.

## Files

- `data_model.md` — inspected view schemas, dimensions, keys, relationship/filter direction, dynamic Date table DAX, and grain caveats.
- `dax_measures.md` — sales, profitability, inventory, payments, returns, purchases, and period comparison measures.
- `report_build_guide.md` — manual connection steps, design rules, all nine report pages, visuals, slicers, validation, and publication notes.
- `validation_queries.sql` — read-only MySQL reconciliation checks.

## Connect from Power BI Desktop

1. Open Power BI Desktop. Choose **Home → Get data → More → Database → MySQL database**.
2. Server: `localhost:3306` (if shown as separate fields, enter server `localhost` and port `3306`). Database: `maganlal_chikki_bi`.
3. Select **Import** mode. Use a locally configured MySQL reporting account with SELECT access; do not put a database password in documentation or a report. If Power BI prompts for the MySQL client/connector, install the supported connector for that Desktop installation.
4. Select the 15 existing views and the optional dimension/transaction tables listed in `data_model.md`.
5. Apply the documented relationships, dynamic Date table, data types, formats, and measures. Follow `report_build_guide.md` page-by-page.
6. Refresh with **Home → Refresh** after MySQL has received a new successful ETL load.

Use read-only permissions for reporting. The setup instructions do not create users or change the database. Do not select or connect to legacy database `maganlal_bi_dashboard`.

## Existing reporting views

`vw_daily_sales`, `vw_weekly_sales`, `vw_monthly_sales`, `vw_product_sales`, `vw_category_sales`, `vw_inventory_status`, `vw_supplier_purchases`, `vw_financial_summary`, `vw_profit_trend`, `vw_expense_summary`, `vw_payment_summary`, `vw_returns_summary`, `vw_forecast`, `vw_reorder_recommendations`, and `vw_dashboard_summary`.

The live MySQL metadata inspection confirmed all 15 views and their columns/types. A read-only `SELECT * ... LIMIT 1` check succeeded for each view. See `data_model.md` for complete results and caveats. No reporting views were created, renamed, or changed for this phase.

## Pages prepared

The manual build guide specifies:

1. Executive Overview
2. Sales Analysis
3. Product Analysis
4. Inventory Intelligence
5. Purchases & Supplier Analysis
6. Finance & Profitability
7. Sales & Demand Forecast
8. Data-Driven Business Insights
9. Returns Analysis

It includes visual fields, slicer scope, KPI choices, conditional status colors, formatting, notes, and empty-state guidance. The guides distinguish current inventory snapshots, lifetime aggregates, transaction details, and estimated forecasts so visuals do not imply unsupported filters or time context.

## Freshness and architecture

```text
Shop Excel → Watchdog → validated ETL → MySQL maganlal_chikki_bi
                                      ├→ FastAPI → React operational dashboard
                                      └→ Power BI Import → refreshed reporting
```

React polls freshness and reflects the latest successful ETL after its API refresh. Power BI Desktop must be manually refreshed. Power BI Service can use scheduled refresh only after the organization configures the supported MySQL data source, credentials, and capacity. When a shop-local MySQL server is not reachable from the Service, deploy/configure an appropriate on-premises data gateway on a reachable, maintained machine and test Service refresh. Refresh frequency depends on connector and tenant/capacity limits. Do not call either Desktop Import or scheduled Service refresh instant real-time.

Use a report note: **Source: MySQL — maganlal_chikki_bi | Mode: Import / refresh-based | Data classification: DEMO DATA**. Do not fabricate a last-refresh timestamp. If a trustworthy model refresh timestamp is later implemented, label its meaning and timezone.

## Validation snapshot

The read-only MySQL checks and API comparison previously verified the following demo-source totals. These are validation references only; DAX remains data-driven and does not contain these constants.

| Metric | Observed value |
|---|---:|
| Revenue | ₹378,579.98 |
| Completed transactions | 1,500 |
| Quantity sold | 3,915 |
| COGS | ₹242,116.00 |
| Gross profit | ₹136,463.98 |
| Operating expenses | ₹99,156.61 |
| Net profit | ₹37,307.37 |
| Gross / net margin | 36.05% / 9.85% |
| Inventory value | ₹187,789.00 |
| Low stock products | 6 |
| Pending recorded payments | ₹283,756.25 |
| Returns / quantity / value | 60 / 116 / ₹13,110.63 |

Use `validation_queries.sql` to recalculate from source. Payment amounts include polymorphic recorded payments; do not interpret them as customer sales collections without filtering and reconciliation. Product and supplier aggregate views lack dates; do not imply Date slicers filter them.

## Current build status

Power BI Desktop was not found installed or running in the available Windows environment. No `.pbix`, published dataset, gateway, or Service refresh was created or verified. The exact manual report build assets and steps are prepared in these files; creating and visually validating the report pages still requires Power BI Desktop.

All work in this phase is confined to `powerbi/`. No backend, frontend, ETL, watchdog, schema, workbook, SQLite, or MySQL data was modified.
