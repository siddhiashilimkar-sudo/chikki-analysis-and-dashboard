def moving_average(values,window=3,horizon=3):
    tail=values[-window:];estimate=sum(tail)/len(tail) if tail else 0
    return {"method":f"{window}-period moving average","estimate":estimate,"horizon":[estimate]*horizon}
