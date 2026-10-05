def profit(revenue,cogs,expenses):
    gross=revenue-cogs;net=gross-expenses
    return {"gross_profit":gross,"net_profit":net,"gross_margin_pct":gross/revenue*100 if revenue else 0,"net_margin_pct":net/revenue*100 if revenue else 0}
