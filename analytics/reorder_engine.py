def recommendation(stock,reorder_level,avg_daily_sales,lead_time_days=7):
    days=stock/avg_daily_sales if avg_daily_sales>0 else None
    target=max(reorder_level*2,avg_daily_sales*lead_time_days+reorder_level)
    return {"days_of_stock":round(days,1) if days is not None else None,"suggested_quantity":max(0,round(target-stock)),"basis":"Data-driven estimate; review before ordering"}
