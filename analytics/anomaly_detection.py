def z_score_anomalies(values, threshold=2.5):
    """Return statistical flags only; these are potential anomalies, not confirmed errors."""
    if len(values)<4:return []
    mean=sum(values)/len(values); variance=sum((x-mean)**2 for x in values)/len(values); sd=variance**0.5
    if not sd:return []
    return [{"index":i,"value":v,"z_score":round((v-mean)/sd,2),"label":"Potential anomaly"} for i,v in enumerate(values) if abs((v-mean)/sd)>=threshold]
