def inventory_insights(products):
    low=[p for p in products if p["current_stock"]<=p["reorder_level"]]
    return ([{"type":"inventory","severity":"warning","title":"Reorder attention needed","description":f"{len(low)} items are at or below reorder level.","supporting_value":len(low)}] if low else [])
