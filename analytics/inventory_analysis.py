def stock_status(stock,reorder): return "Out of stock" if stock<=0 else "Low" if stock<=reorder else "Healthy"
