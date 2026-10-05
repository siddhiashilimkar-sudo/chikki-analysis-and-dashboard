# Power BI DAX measures

Create these as **measures** (Modeling → New measure), not calculated columns. They use the existing MySQL objects and respond to relationships and slicers described in `data_model.md`. Format currency measures as Indian Rupees (₹) with two decimals and percentage measures as percentage with two decimals. No demo totals are embedded in the formulas.

## Sales and profitability

Use the daily-grain sales view for time-filtered sales KPIs. It contains one row per sale date and its numeric columns are additive across dates.

```DAX
Total Revenue = SUM('vw_daily_sales'[revenue])
Total Sales Transactions = SUM('vw_daily_sales'[total_sales])
Total Quantity Sold = SUM('vw_daily_sales'[quantity])
Average Order Value = DIVIDE([Total Revenue], [Total Sales Transactions], 0)
Total COGS = SUM('vw_daily_sales'[cogs])
Gross Profit = [Total Revenue] - [Total COGS]
Operating Expenses = SUM('vw_expense_summary'[amount])
Net Profit = [Gross Profit] - [Operating Expenses]
Gross Margin % = DIVIDE([Gross Profit], [Total Revenue], 0)
Net Margin % = DIVIDE([Net Profit], [Total Revenue], 0)
```

`vw_financial_summary` is a single, unfiltered summary row. It is useful for a source reconciliation card/table, but do not sum it across date/category contexts. The measures above are intended to respond to the Date table.

## Product, inventory and replenishment

```DAX
Product Revenue (All Time) = SUM('vw_product_sales'[revenue])
Product Quantity Sold (All Time) = SUM('vw_product_sales'[quantity])
Product COGS (All Time) = SUM('vw_product_sales'[cogs])
Product Gross Profit (All Time) = [Product Revenue (All Time)] - [Product COGS (All Time)]
Inventory Value = SUM('vw_inventory_status'[stock_value])
Low Stock Products = CALCULATE(COUNTROWS('vw_inventory_status'), 'vw_inventory_status'[stock_status] IN {"Low", "Critical"})
Out of Stock Products = CALCULATE(COUNTROWS('vw_inventory_status'), 'vw_inventory_status'[stock_status] = "Out of stock")
Suggested Reorder Units = SUM('vw_reorder_recommendations'[suggested_quantity])
```

The product-sales view has no date column; mark its metrics as **all time**. For product sales sliced by date, use the transaction detail model and label the measure as line-item revenue; reconcile it to sales-header revenue if discounts/tax/rounding cause a difference.

The existing reorder view exposes product ID, generated time, days of stock, suggested quantity, and lead time only. Do not present unavailable average-demand, safety-stock, or reason fields as if stored in that view. Join to the product dimension for current-stock and reorder-level context.

## Payments and returns

```DAX
Total Paid = CALCULATE(SUM('vw_payment_summary'[amount]), 'vw_payment_summary'[status] = "paid")
Pending Payments = CALCULATE(SUM('vw_payment_summary'[amount]), 'vw_payment_summary'[status] = "pending")
Return Quantity = SUM('vw_returns_summary'[return_quantity])
Return Value = SUM('vw_returns_summary'[return_value])
Return Count = COUNTROWS('returns')
Return Quantity Rate = DIVIDE([Return Quantity], [Total Quantity Sold], 0)
```

Return Count uses the transaction-level `returns` table because `vw_returns_summary` is grouped by date and does not expose a count. Use `return_items` with `returns` and `products` for product-level return visuals.

## Purchase and supplier measures

```DAX
Purchase Value = SUM('purchases'[total])
Purchase Quantity = SUM('purchase_items'[quantity])
Supplier Purchase Value (All Time) = SUM('vw_supplier_purchases'[purchase_value])
Supplier Purchase Quantity (All Time) = SUM('vw_supplier_purchases'[purchase_quantity])
```

The supplier view is a lifetime aggregate and has no purchase date. Use `purchases` plus `purchase_items` for purchase trends. Do not combine the all-time supplier aggregate with dated purchase totals in a single sum.

## Time intelligence

Mark `'DateTable'[Date]` as the model's date table. These examples compare the selected date context with the equivalent prior month; label cards/charts **Previous Month** and **Month-over-Month** rather than implying a different comparison.

```DAX
Revenue Previous Month = CALCULATE([Total Revenue], DATEADD('DateTable'[Date], -1, MONTH))
Revenue Growth vs Previous Month % = DIVIDE([Total Revenue] - [Revenue Previous Month], [Revenue Previous Month], 0)
Profit Previous Month = CALCULATE([Net Profit], DATEADD('DateTable'[Date], -1, MONTH))
Profit Growth vs Previous Month % = DIVIDE([Net Profit] - [Profit Previous Month], [Profit Previous Month], 0)
Expenses Previous Month = CALCULATE([Operating Expenses], DATEADD('DateTable'[Date], -1, MONTH))
Expense Growth vs Previous Month % = DIVIDE([Operating Expenses] - [Expenses Previous Month], [Expenses Previous Month], 0)
```

`DIVIDE(..., 0)` intentionally returns zero for zero or missing denominators. Consider displaying “N/A” in a separate card when the prior period has no baseline.

## Metric definitions

- Revenue: sum of completed sales totals, matching the application summary definition.
- COGS: sold quantity multiplied by stored unit cost.
- Gross profit: revenue less COGS.
- Net profit: gross profit less operating expenses.
- AOV: revenue divided by completed sale transactions.
- Inventory value: current stock multiplied by product purchase cost.
- Return value: returned quantity multiplied by item unit value, as defined by the view.
- Forecast amounts/quantities are estimates and must be labeled **FORECAST / ESTIMATED**.
