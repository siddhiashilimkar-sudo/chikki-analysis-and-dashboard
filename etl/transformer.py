def transform(sheets):
    """Apply canonical trimming without discarding or guessing source values."""
    transformed={}
    for name,frame in sheets.items():
        df=frame.copy()
        for column in df.select_dtypes(include=['object']).columns:
            df[column]=df[column].map(lambda value:value.strip() if isinstance(value,str) else value)
        transformed[name]=df
    if 'Products' in transformed:
        transformed['Products']['unit']=transformed['Products']['unit'].fillna('g').astype(str).str.strip().str.lower()
    return transformed
