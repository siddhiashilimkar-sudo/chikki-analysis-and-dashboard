# Power BI data model — inspected MySQL schema

This model is documented from the live `maganlal_chikki_bi` database and `database/views.sql`. It does not change database objects or data. Connect to `localhost:3306`, database `maganlal_chikki_bi`, using a read-only MySQL account in Power BI. Use **Import** mode for the initial report.

## Existing view columns and MySQL types

These are the columns Power BI Navigator will expose in the current database. MySQL `DECIMAL` should be imported as Fixed Decimal/Currency or Decimal Number as appropriate; preserve IDs as whole numbers and dates as Date/DateTime.

| View | Grain | Columns and types |
|---|---|---|
| `vw_daily_sales` | One completed-sale date | `sale_date DATE`; `total_sales BIGINT`; `revenue DECIMAL(36,2)`; `quantity DECIMAL(34,2)`; `cogs DECIMAL(46,4)` |
| `vw_weekly_sales` | ISO-style year/week key | `year_week INTEGER`; `revenue DECIMAL(36,2)`; `total_sales BIGINT` |
| `vw_monthly_sales` | Month | `month_start VARCHAR(10)`; `revenue DECIMAL(36,2)`; `total_sales BIGINT` |
| `vw_product_sales` | Product, lifetime | `product_id INTEGER`; `product_name VARCHAR(160)`; `category VARCHAR(80)`; `quantity DECIMAL(34,2)`; `revenue DECIMAL(46,4)`; `cogs DECIMAL(46,4)` |
| `vw_category_sales` | Category, lifetime | `category VARCHAR(80)`; `quantity DECIMAL(56,2)`; `revenue DECIMAL(65,4)` |
| `vw_inventory_status` | Product, current snapshot | `product_id INTEGER`; `product_name VARCHAR(160)`; `category VARCHAR(80)`; `current_stock DECIMAL(12,2)`; `minimum_stock DECIMAL(12,2)`; `reorder_level DECIMAL(12,2)`; `stock_value DECIMAL(24,4)`; `stock_status VARCHAR(12)` |
| `vw_supplier_purchases` | Supplier, lifetime | `supplier_id INTEGER`; `supplier_name VARCHAR(160)`; `lead_time_days INTEGER`; `purchases BIGINT`; `purchase_value DECIMAL(36,2)`; `purchase_quantity DECIMAL(34,2)` |
| `vw_financial_summary` | One unfiltered summary row | `revenue DECIMAL(36,2)`; `cogs DECIMAL(46,4)`; `operating_expenses DECIMAL(34,2)`; `gross_profit DECIMAL(47,4)`; `net_profit DECIMAL(48,4)` |
| `vw_profit_trend` | Sale date | `sale_date DATE`; `revenue DECIMAL(36,2)`; `cogs DECIMAL(46,4)`; `gross_profit DECIMAL(47,4)` |
| `vw_expense_summary` | Expense date and category | `expense_date DATE`; `category VARCHAR(80)`; `amount DECIMAL(34,2)` |
| `vw_payment_summary` | Payment date and status | `payment_date DATE`; `status VARCHAR(20)`; `amount DECIMAL(34,2)` |
| `vw_returns_summary` | Return date | `return_date DATE`; `return_quantity DECIMAL(34,2)`; `return_value DECIMAL(46,4)` |
| `vw_forecast` | Product, forecast period and horizon | `forecast_id BIGINT`; `product_id INTEGER`; `generated_at DATETIME`; `period_start DATE`; `horizon_days INTEGER`; `forecast_quantity DECIMAL(12,2)`; `method VARCHAR(80)` |
| `vw_reorder_recommendations` | Product, generated recommendation | `recommendation_id BIGINT`; `product_id INTEGER`; `generated_at DATETIME`; `days_of_stock DECIMAL(10,2)`; `suggested_quantity DECIMAL(12,2)`; `lead_time_days INTEGER` |
| `vw_dashboard_summary` | One unfiltered summary row | `revenue DECIMAL(36,2)`; `transactions BIGINT`; `low_stock_items BIGINT`; `inventory_value DECIMAL(46,4)` |

## Recommended Navigator selection

Load the 15 views for reporting, plus these existing tables to enable the requested detail and valid relationships: `products`, `categories`, `sales`, `sale_items`, `purchases`, `purchase_items`, `suppliers`, `expenses`, `payments`, `returns`, `return_items`, `inventory_movements`, and `business_insights`. The base tables are not duplicate views: they provide keys and transaction detail absent from the aggregated views.

If a particular page does not need transaction detail, omit its base tables and use the corresponding summary view. Do not load `vw_financial_summary`/`vw_dashboard_summary` as additive facts; each is a single whole-database snapshot.

## Relationships and filter direction

Create these active relationships with **single-direction filtering from dimension/header to detail**. They are one-to-many except the product snapshot/aggregate views, which have at most one row per product and may be modeled one-to-one:

| One side | Many side | Key | Notes |
|---|---|---|---|
| `categories` | `products` | `category_id` | Verified FK. Product category slicer. |
| `products` | `sale_items` | `product_id` | Verified FK. |
| `sales` | `sale_items` | `sale_id` | Verified FK. The sales date filters its line items through this path. |
| `suppliers` | `purchases` | `supplier_id` | Verified FK. |
| `purchases` | `purchase_items` | `purchase_id` | Verified FK. |
| `products` | `purchase_items` | `product_id` | Verified FK. |
| `products` | `inventory_movements` | `product_id` | Verified FK. |
| `sales` | `returns` | `sale_id` | Verified FK. |
| `returns` | `return_items` | `return_id` | Verified FK. |
| `products` | `return_items` | `product_id` | Verified FK. |
| `products` | `vw_product_sales` | `product_id` | One-to-one for sold products; lifetime aggregate. |
| `products` | `vw_inventory_status` | `product_id` | One-to-one current stock snapshot; validate product ID uniqueness on refresh. |
| `suppliers` | `vw_supplier_purchases` | `supplier_id` | One-to-one lifetime supplier aggregate; no date key. |
| `products` | `vw_forecast` | `product_id` | Estimated quantities; keep distinct from actual sales. |
| `products` | `vw_reorder_recommendations` | `product_id` | Recommendation snapshot. |

Create one Date table and connect its unique Date column (one side) to `sales[sale_date]`, `vw_daily_sales[sale_date]`, `vw_profit_trend[sale_date]`, `expenses[expense_date]`, `vw_expense_summary[expense_date]`, `payments[payment_date]`, `vw_payment_summary[payment_date]`, `returns[return_date]`, and `vw_returns_summary[return_date]`. Keep relationships active and single-direction. Do not relate fact tables to one another except the header-to-lines relationships above.

Also relate Date to `purchases[purchase_date]`, `inventory_movements[movement_date]`, and `vw_forecast[period_start]`. These dates support the purchase, stock movement, and forecast pages. Leave `vw_reorder_recommendations[generated_at]` and `business_insights[generated_at]` as generation timestamps unless a dedicated role-playing Date table is intentionally added.

Do not join `vw_category_sales` to both category and product dimensions: it has only a category label, so doing so can create ambiguous filter paths. Prefer deriving category charts from `products` + `sale_items` (with the transaction caveat below), or use the category view alone on an all-time page. `vw_supplier_purchases` is a lifetime aggregate; use it for supplier profile visuals and use `purchases` / `purchase_items` for date-filtered purchase trends.

`vw_weekly_sales` has an integer `year_week` and `vw_monthly_sales.month_start` is text. Keep them disconnected for their respective aggregate visuals, or create carefully typed Power Query date keys and test month/week boundary filtering before adding relationships. The main trend visuals should use daily-grain views and the Date table.

`payments.related_type`/`related_id` is polymorphic, not a declared FK. Keep payment facts connected to Date only; do not infer a relationship to sales or purchases from the numeric ID. `business_insights.generated_at` is a timestamp; if needed, add a date-only Power Query column before relating it to Date. Do not join expense `category` to product `categories`: those are separate business concepts.

## Dynamic Date table

After loading the listed tables/views, create this calculated table (Modeling → New table). Its range is derived from loaded business dates rather than hard-coded demo dates.

```DAX
DateTable =
VAR AllBusinessDates =
    UNION(
        SELECTCOLUMNS('sales', "BusinessDate", 'sales'[sale_date]),
        SELECTCOLUMNS('expenses', "BusinessDate", 'expenses'[expense_date]),
        SELECTCOLUMNS('payments', "BusinessDate", 'payments'[payment_date]),
        SELECTCOLUMNS('returns', "BusinessDate", 'returns'[return_date]),
        SELECTCOLUMNS('purchases', "BusinessDate", 'purchases'[purchase_date]),
        SELECTCOLUMNS('inventory_movements', "BusinessDate", 'inventory_movements'[movement_date]),
        SELECTCOLUMNS('vw_forecast', "BusinessDate", 'vw_forecast'[period_start])
    )
VAR FirstDate = MINX(AllBusinessDates, [BusinessDate])
VAR LastDate = MAXX(AllBusinessDates, [BusinessDate])
RETURN
    CALENDAR(FirstDate, LastDate)
```

Add calculated columns:

```DAX
Year = YEAR('DateTable'[Date])
Quarter = "Q" & FORMAT('DateTable'[Date], "Q")
Month = FORMAT('DateTable'[Date], "MMMM")
Month Number = MONTH('DateTable'[Date])
Year Month = FORMAT('DateTable'[Date], "YYYY-MM")
Week = WEEKNUM('DateTable'[Date], 2)
Day = DAY('DateTable'[Date])
Day Name = FORMAT('DateTable'[Date], "dddd")
```

Sort Month by Month Number and Day Name by a weekday-number column if used. Choose **Table tools → Mark as date table → Date**. If all source date columns are empty, the dynamic range cannot be created; check source data rather than inserting a fabricated range.

## Grain and filter caveats

- `vw_daily_sales` and `vw_profit_trend` are daily facts. Date slicers affect them; they are separate facts and must not be joined together.
- `vw_product_sales`, `vw_category_sales`, and `vw_supplier_purchases` are lifetime aggregates and have no date key. Do not imply Date slicers affect them.
- `vw_inventory_status` is a current snapshot, not historical inventory. A Date slicer does not reconstruct past stock.
- `vw_forecast` is future-estimated data. Use `period_start` on a forecast axis, and visually distinguish it from actual sales.
- `vw_reorder_recommendations` does not currently expose average demand, safety stock, reorder level, or a reason field; show only its actual fields, enriched with current product/stock attributes where possible.
- Main revenue is `sales.total` through the daily view. Product line revenue (`quantity × unit_price`) can differ because transaction-level discounts, tax, or rounding may exist. Use the transaction header measure for reconciled company revenue and clearly label line-item allocation metrics.
- Currency is INR (₹). Keep precision internally; apply display formats in the Power BI model.
