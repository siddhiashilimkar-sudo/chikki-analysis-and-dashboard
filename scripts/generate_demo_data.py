from pathlib import Path
import pandas as pd,random
from datetime import date,timedelta
random.seed(42);out=Path(__file__).resolve().parents[1]/"data/raw/business_data.xlsx";out.parent.mkdir(parents=True,exist_ok=True)
cats=['Peanut Chikki','Sesame Chikki','Coconut Chikki','Dry Fruit Chikki','Chocolate Chikki','Special Chikki','Gift Packs','Other'];products=[]
for i in range(1,41):
    c=cats[(i-1)%8];w=[100,250,500,1000][(i-1)%4];cost=35+(i%9)*7
    products.append(dict(product_id=i,product_code=f'DEMO-{i:03}',product_name=f'DEMO {c} {w}g {i:02}',category=c,net_weight=w,unit='g',selling_price=round(cost*random.uniform(1.3,1.9),2),purchase_price=cost,current_stock=random.randint(3,150),minimum_stock=10,reorder_level=20,barcode=f'89000000{i:04}'))
sales=[];items=[];today=date.today()
for n in range(1,1501):
    d=today-timedelta(days=random.randint(0,365));total=0
    for _ in range(random.choices([1,2,3],[.55,.35,.10])[0]):
        p=random.choice(products);q=random.choices([1,2,3,5],[.55,.27,.14,.04])[0];price=p['selling_price'];cost=p['purchase_price'];total+=q*price
        items.append(dict(sale_id=n,product_id=p['product_id'],quantity=q,unit_price=price,unit_cost=cost))
    sales.append(dict(sale_id=n,sale_code=f'DEMO-S-{n:05}',sale_date=d,total=round(total,2),status='completed'))
sup=[dict(supplier_id=i,supplier_name=f'DEMO Supplier {i:02}',phone='',lead_time_days=random.randint(3,14)) for i in range(1,13)]
purchases=[dict(purchase_id=i,supplier_id=random.randint(1,12),purchase_date=today-timedelta(days=random.randint(0,365)),total=round(random.uniform(1500,18000),2),status='paid') for i in range(1,241)]
expenses=[dict(expense_id=i,expense_date=today-timedelta(days=random.randint(0,365)),category=random.choice(['Rent','Electricity','Transport','Packaging','Marketing','Maintenance','Other']),description='Synthetic operating expense',amount=round(random.uniform(50,650),2)) for i in range(1,301)]
frames={'Products':pd.DataFrame(products),'Categories':pd.DataFrame([{'category_id':i+1,'category':v} for i,v in enumerate(cats)]),'Suppliers':pd.DataFrame(sup),'Sales':pd.DataFrame(sales),'Sale_Items':pd.DataFrame(items),'Purchases':pd.DataFrame(purchases),'Purchase_Items':pd.DataFrame([dict(purchase_id=p['purchase_id'],product_id=random.randint(1,40),quantity=random.randint(10,100),unit_cost=random.choice(products)['purchase_price']) for p in purchases]),'Inventory':pd.DataFrame([dict(product_id=p['product_id'],current_stock=p['current_stock'],minimum_stock=p['minimum_stock'],reorder_level=p['reorder_level']) for p in products]),'Inventory_Movements':pd.DataFrame([dict(movement_id=i,product_id=random.randint(1,40),movement_date=today-timedelta(days=random.randint(0,365)),movement_type=random.choice(['purchase','sale','adjustment']),quantity=random.randint(1,30),reference=f'DEMO-{i}') for i in range(1,1801)]),'Expenses':pd.DataFrame(expenses),'Payments':pd.DataFrame([dict(payment_id=i,payment_date=today-timedelta(days=random.randint(0,365)),amount=round(random.uniform(500,15000),2),payment_type='supplier',reference=f'DEMO-PAY-{i}',related_type='purchase',related_id=random.randint(1,240),status=random.choices(['paid','pending'],[.9,.1])[0]) for i in range(1,401)]),'Returns':pd.DataFrame([dict(return_id=i,return_date=today-timedelta(days=random.randint(0,365)),sale_id=random.randint(1,1500),reason=random.choice(['Damaged','Quality','Other']),total_value=round(random.uniform(50,800),2)) for i in range(1,61)]),'Return_Items':pd.DataFrame([dict(return_item_id=i,return_id=i,product_id=random.randint(1,40),quantity=random.randint(1,3),unit_value=round(random.uniform(40,180),2)) for i in range(1,61)])}
with pd.ExcelWriter(out,engine='openpyxl') as writer:
    for name,df in frames.items():df.to_excel(writer,sheet_name=name,index=False)
print(f'Generated synthetic workbook: {out}; {sum(len(x) for x in frames.values())} rows')
