def summarize(rows):
    revenue=sum(r["revenue"] for r in rows)
    return {"revenue":revenue,"periods":len(rows),"average_period_revenue":revenue/len(rows) if rows else 0}
