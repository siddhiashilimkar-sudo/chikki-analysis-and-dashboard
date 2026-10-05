REQUIRED_COLUMNS={
 'Categories':{'category_id','category'},'Products':{'product_id','product_code','product_name','category','selling_price','purchase_price','current_stock'},
 'Suppliers':{'supplier_id','supplier_name','lead_time_days'},'Sales':{'sale_id','sale_code','sale_date','total'},
 'Sale_Items':{'sale_id','product_id','quantity','unit_price','unit_cost'},'Purchases':{'purchase_id','supplier_id','purchase_date','total'},
 'Purchase_Items':{'purchase_id','product_id','quantity','unit_cost'},'Inventory':{'product_id','current_stock','minimum_stock','reorder_level'},
 'Inventory_Movements':{'movement_id','product_id','movement_date','movement_type','quantity'},'Expenses':{'expense_id','expense_date','category','amount'},
 'Payments':{'payment_id','payment_date','amount','payment_type','status'},'Returns':{'return_id','return_date','sale_id','reason','total_value'},
 'Return_Items':{'return_item_id','return_id','product_id','quantity','unit_value'}}
IDS={'Categories':'category_id','Products':'product_id','Suppliers':'supplier_id','Sales':'sale_id','Purchases':'purchase_id','Inventory':'product_id','Inventory_Movements':'movement_id','Expenses':'expense_id','Payments':'payment_id','Returns':'return_id','Return_Items':'return_item_id'}
DATES={'Sales':'sale_date','Purchases':'purchase_date','Inventory_Movements':'movement_date','Expenses':'expense_date','Payments':'payment_date','Returns':'return_date'}
NUMERIC={'Products':['selling_price','purchase_price','current_stock','minimum_stock','reorder_level','net_weight'],'Sales':['total'],'Sale_Items':['quantity','unit_price','unit_cost'],'Purchase_Items':['quantity','unit_cost'],'Purchases':['total'],'Inventory':['current_stock','minimum_stock','reorder_level'],'Inventory_Movements':['quantity'],'Expenses':['amount'],'Payments':['amount'],'Returns':['total_value'],'Return_Items':['quantity','unit_value']}
def validate(sheets):
    import pandas as pd
    errors=[];warnings=[]
    for name,required in REQUIRED_COLUMNS.items():
        if name not in sheets:errors.append(f'Missing sheet: {name}');continue
        df=sheets[name];missing=required-set(map(str,df.columns))
        if missing:errors.append(f'{name} missing required columns: {sorted(missing)}');continue
        key=IDS.get(name)
        if key:
            if df[key].isna().any():errors.append(f'{name}.{key} contains missing IDs')
            if df[key].duplicated().any():errors.append(f'{name}.{key} contains duplicate IDs')
    if errors:return errors,warnings
    for name,col in DATES.items():
        parsed=pd.to_datetime(sheets[name][col],errors='coerce')
        if parsed.isna().any():errors.append(f'{name}.{col} contains invalid dates')
    for name,cols in NUMERIC.items():
        for col in cols:
            if col not in sheets[name]:continue
            vals=pd.to_numeric(sheets[name][col],errors='coerce')
            if vals.isna().any():errors.append(f'{name}.{col} has missing or non-numeric values')
            elif (vals<0).any():errors.append(f'{name}.{col} has negative values')
            elif (col=='quantity' and (vals<=0).any()) or (col in ('selling_price','purchase_price','unit_price','unit_cost','net_weight') and (vals<=0).any()):errors.append(f'{name}.{col} must be greater than zero')
    for name,code in [('Sales','sale_code'),('Products','product_code')]:
        if sheets[name][code].duplicated().any():errors.append(f'{name}.{code} contains duplicate transactions')
    links=[('Products','category','Categories','category'),('Sale_Items','product_id','Products','product_id'),('Sale_Items','sale_id','Sales','sale_id'),('Purchase_Items','product_id','Products','product_id'),('Purchase_Items','purchase_id','Purchases','purchase_id'),('Purchases','supplier_id','Suppliers','supplier_id'),('Inventory','product_id','Products','product_id'),('Inventory_Movements','product_id','Products','product_id'),('Returns','sale_id','Sales','sale_id'),('Return_Items','return_id','Returns','return_id'),('Return_Items','product_id','Products','product_id')]
    for source,scol,target,tcol in links:
        if sheets[source][scol].isna().any():errors.append(f'{source}.{scol} contains missing references')
        missing=set(sheets[source][scol].dropna())-set(sheets[target][tcol].dropna())
        if missing:errors.append(f'{source}.{scol} references {len(missing)} missing {target}.{tcol} values')
    for name,df in sheets.items():
        if df.empty:warnings.append(f'{name} contains no data rows')
        if df.columns.duplicated().any():errors.append(f'{name} contains duplicate column names')
    return errors,warnings
def clean(sheets):
    import pandas as pd
    out={k:v.copy() for k,v in sheets.items()}
    for name,col in DATES.items():out[name][col]=pd.to_datetime(out[name][col],errors='coerce').dt.date
    return out
