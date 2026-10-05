from datetime import date,timedelta,datetime,timezone
from pathlib import Path
import json,subprocess,sys,logging,hashlib
import os
from fastapi import FastAPI,Depends,HTTPException,Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import func
from .database import Base,engine,get_db,SessionLocal
from .models import *
from .config import settings
from .schemas.products import ProductCreate,ProductUpdate,SupplierCreate,PurchaseCreate
from .product_identity import display_name,normalize_label,product_identity
from sqlalchemy.exc import IntegrityError
from sqlalchemy import text
ROOT=Path(__file__).resolve().parents[2]
Base.metadata.create_all(engine)
app=FastAPI(title='Maganlal Chikki BI',version='1.1.0',description='Business operations and analytics; demo data is synthetic.')
app.add_middleware(CORSMiddleware,allow_origins=[x.strip() for x in settings.cors_origins.split(',')],allow_credentials=True,allow_methods=['*'],allow_headers=['*'])

def backfill_product_supplier_links():
    """Preserve existing supplier provenance from purchase history for identity checks."""
    db=SessionLocal()
    try:
        rows=db.query(Product,Purchase.supplier_id).join(PurchaseItem,PurchaseItem.product_id==Product.id).join(Purchase,Purchase.id==PurchaseItem.purchase_id).distinct().all()
        existing={(x.product_id,x.supplier_id) for x in db.query(ProductSupplier).all()}
        links=[]
        seen=set()
        for product,supplier_id in rows:
            pair=(product.id,supplier_id)
            if pair in existing or pair in seen:continue
            name,weight,unit=product_identity(product.product_name,product.net_weight,product.unit)
            links.append(ProductSupplier(product_id=product.id,supplier_id=supplier_id,normalized_name=name,canonical_weight=weight,canonical_unit=unit));seen.add(pair)
        if links:db.add_all(links);db.commit()
    except Exception as exc:
        db.rollback()
        logging.warning('Could not backfill product-supplier identity links (%s)',type(exc).__name__)
    finally:db.close()
backfill_product_supplier_links()
def period_month():return func.strftime('%Y-%m',Sale.sale_date) if engine.dialect.name=='sqlite' else func.date_format(Sale.sale_date,'%Y-%m')
def bounds(q,from_date,to_date,col):
    if from_date:q=q.filter(col>=from_date)
    if to_date:q=q.filter(col<=to_date)
    return q
def paginate(q,skip,limit):return q.offset(max(0,skip)).limit(max(1,min(limit,500)))
def product_rows(db,category=None,product_id=None):
    q=db.query(Product)
    if category:q=q.filter(Product.category==category)
    if product_id:q=q.filter(Product.id==product_id)
    return q

def sales_query(db,from_date=None,to_date=None,product_id=None,category=None):
    q=db.query(Sale);q=bounds(q,from_date,to_date,Sale.sale_date)
    if product_id or category:
        q=q.join(SaleItem,SaleItem.sale_id==Sale.id).join(Product,Product.id==SaleItem.product_id)
        if product_id:q=q.filter(Product.id==product_id)
        if category:q=q.filter(Product.category==category)
        q=q.distinct()
    return q

def summary(db,from_date=None,to_date=None):
    sq=sales_query(db,from_date,to_date);sids=sq.with_entities(Sale.id).statement
    revenue=db.query(func.coalesce(func.sum(Sale.total),0)).filter(Sale.id.in_(sids)).scalar() or 0
    count=sq.count();cogs=db.query(func.coalesce(func.sum(SaleItem.quantity*SaleItem.unit_cost),0)).filter(SaleItem.sale_id.in_(sids)).scalar() or 0
    expenses=bounds(db.query(func.coalesce(func.sum(Expense.amount),0)),from_date,to_date,Expense.expense_date).scalar() or 0
    inv=db.query(func.coalesce(func.sum(Product.current_stock*Product.purchase_price),0)).scalar() or 0
    low=db.query(func.count(Product.id)).filter(Product.current_stock<=Product.reorder_level).scalar() or 0
    pending=db.query(func.coalesce(func.sum(Payment.amount),0)).filter(Payment.status=='pending').scalar() or 0
    gross=revenue-cogs;net=gross-expenses
    latest=db.query(EtlLog).filter(EtlLog.status=='success',EtlLog.finished_at.isnot(None)).order_by(EtlLog.finished_at.desc()).first()
    return {'revenue':round(float(revenue),2),'sales':count,'quantity':int(db.query(func.coalesce(func.sum(SaleItem.quantity),0)).filter(SaleItem.sale_id.in_(sids)).scalar() or 0),'average_order_value':round(float(revenue)/count,2) if count else 0,'cogs':round(float(cogs),2),'gross_profit':round(float(gross),2),'operating_expenses':round(float(expenses),2),'net_profit':round(float(net),2),'gross_margin':round(float(gross)/float(revenue)*100,2) if revenue else 0,'net_margin':round(float(net)/float(revenue)*100,2) if revenue else 0,'inventory_value':round(float(inv),2),'low_stock_items':low,'pending_payments':round(float(pending),2),'updated_at':latest.finished_at.isoformat()+'Z' if latest and latest.finished_at.tzinfo is None else latest.finished_at.isoformat() if latest else None}

@app.get('/health')
def health(db:Session=Depends(get_db)):
    db.execute(__import__('sqlalchemy').text('SELECT 1'))
    return {'status':'ok','database_mode':settings.database_mode,'dialect':engine.dialect.name,'products':db.query(Product).count()}
def _watcher_state():
    path=ROOT/'data/processed/watcher_status.json'
    try: state=json.loads(path.read_text(encoding='utf-8'))
    except (OSError,ValueError):return {'status':'stopped','monitoring':False,'heartbeat_at':None}
    heartbeat=state.get('heartbeat_at')
    try:
        stamp=datetime.fromisoformat(heartbeat.replace('Z','+00:00')) if heartbeat else None
        if stamp and stamp.tzinfo is None:stamp=stamp.replace(tzinfo=timezone.utc)
        active=bool(state.get('monitoring')) and stamp is not None and (datetime.now(timezone.utc)-stamp).total_seconds()<=45
    except (ValueError,TypeError):active=False
    return {**state,'monitoring':active,'status':'monitoring' if active else 'stopped'}
def _etl_details(log):
    try:return json.loads(log.details or '{}')
    except (TypeError,ValueError):return {}
@app.get('/api/dashboard/freshness')
def dashboard_freshness(db:Session=Depends(get_db)):
    try:
        db.execute(text('SELECT 1'))
        latest_run=db.query(EtlLog).order_by(EtlLog.started_at.desc()).first()
        latest=db.query(EtlLog).filter(EtlLog.status=='success',EtlLog.finished_at.isnot(None)).order_by(EtlLog.finished_at.desc()).first()
        watcher=_watcher_state();now=datetime.now(timezone.utc)
        updated=latest.finished_at if latest else None
        if updated and updated.tzinfo is None:updated=updated.replace(tzinfo=timezone.utc)
        age=(now-updated).total_seconds() if updated else None
        current=latest is not None and age is not None and age<=max(1,settings.data_stale_after_minutes)*60
        return {'database_connected':True,'database_mode':settings.database_mode,'dialect':engine.dialect.name,'api_status':'online','data_status':'LIVE' if current else 'STALE','data_classification':settings.data_classification.upper(),'last_data_update':updated.isoformat().replace('+00:00','Z') if updated else None,'age_seconds':round(age,1) if age is not None else None,'etl_status':latest_run.status if latest_run else 'not_run','watcher':watcher}
    except Exception:
        return {'database_connected':False,'database_mode':settings.database_mode,'dialect':engine.dialect.name,'api_status':'online','data_status':'OFFLINE','data_classification':settings.data_classification.upper(),'last_data_update':None,'age_seconds':None,'etl_status':'unknown','watcher':_watcher_state()}
@app.get('/api/dashboard/summary')
def dashboard_summary(from_date:date|None=None,to_date:date|None=None,db:Session=Depends(get_db)):return summary(db,from_date,to_date)
@app.get('/api/dashboard/sales-trend')
def trend(from_date:date|None=None,to_date:date|None=None,db:Session=Depends(get_db)):
    q=bounds(db.query(Sale.sale_date,func.sum(Sale.total)).group_by(Sale.sale_date),from_date,to_date,Sale.sale_date)
    return [{'date':str(d),'revenue':float(v)} for d,v in q.order_by(Sale.sale_date).all()]
@app.get('/api/dashboard/weekly-sales')
def weekly(from_date:date|None=None,to_date:date|None=None,db:Session=Depends(get_db)):
    q=bounds(db.query(Sale.sale_date,func.sum(Sale.total)).group_by(Sale.sale_date),from_date,to_date,Sale.sale_date);data={i:0.0 for i in range(7)}
    for d,v in q.all():data[d.weekday()]+=float(v)
    return [{'weekday':['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday'][i],'revenue':round(v,2)} for i,v in data.items()]
@app.get('/api/dashboard/monthly-sales')
def monthly(from_date:date|None=None,to_date:date|None=None,db:Session=Depends(get_db)):
    q=bounds(db.query(period_month(),func.sum(Sale.total)).group_by(period_month()),from_date,to_date,Sale.sale_date)
    return [{'month':str(m),'revenue':float(v)} for m,v in q.order_by(period_month()).all()]
@app.get('/api/dashboard/top-products')
def top_products(limit:int=10,from_date:date|None=None,to_date:date|None=None,category:str|None=None,db:Session=Depends(get_db)):
    q=db.query(Product.product_name,Product.id,func.sum(SaleItem.quantity).label('quantity'),func.sum(SaleItem.quantity*SaleItem.unit_price).label('revenue')).join(SaleItem,SaleItem.product_id==Product.id).join(Sale,Sale.id==SaleItem.sale_id)
    q=bounds(q,from_date,to_date,Sale.sale_date)
    if category:q=q.filter(Product.category==category)
    return [{'product_id':i,'product':n,'quantity':float(qty),'revenue':float(rev)} for n,i,qty,rev in q.group_by(Product.id,Product.product_name).order_by(func.sum(SaleItem.quantity*SaleItem.unit_price).desc()).limit(min(limit,100)).all()]
@app.get('/api/dashboard/slow-products')
def slow_products(limit:int=10,db:Session=Depends(get_db)):
    since=date.today()-timedelta(days=90)
    demand=db.query(SaleItem.product_id.label('product_id'),func.sum(SaleItem.quantity).label('quantity')).join(Sale,Sale.id==SaleItem.sale_id).filter(Sale.sale_date>=since,Sale.status=='completed').group_by(SaleItem.product_id).subquery()
    return [{'product_id':p.id,'product':p.product_name,'category':p.category,'quantity_90d':float(qty or 0)} for p,qty in db.query(Product,demand.c.quantity).outerjoin(demand,demand.c.product_id==Product.id).order_by(func.coalesce(demand.c.quantity,0)).limit(min(limit,100)).all()]
@app.get('/api/dashboard/category-performance')
def categories(from_date:date|None=None,to_date:date|None=None,db:Session=Depends(get_db)):
    q=db.query(Product.category,func.sum(SaleItem.quantity).label('quantity'),func.sum(SaleItem.quantity*SaleItem.unit_price).label('revenue')).join(SaleItem,SaleItem.product_id==Product.id).join(Sale,Sale.id==SaleItem.sale_id);q=bounds(q,from_date,to_date,Sale.sale_date)
    return [{'category':c,'quantity':float(n),'revenue':float(r)} for c,n,r in q.group_by(Product.category).all()]
@app.get('/api/products')
def products(skip:int=0,limit:int=100,category:str|None=None,db:Session=Depends(get_db)):
    result=[]
    for p in paginate(product_rows(db,category),skip,limit).all():
        supplier_ids=[sid for (sid,) in db.query(ProductSupplier.supplier_id).filter(ProductSupplier.product_id==p.id).all()]
        result.append({'id':p.id,'product_code':p.product_code,'product_name':p.product_name,'category':p.category,'net_weight':p.net_weight,'unit':p.unit,'selling_price':p.selling_price,'purchase_price':p.purchase_price,'current_stock':p.current_stock,'minimum_stock':p.minimum_stock,'reorder_level':p.reorder_level,'barcode':p.barcode,'supplier_ids':supplier_ids})
    return result
@app.post('/api/products',status_code=201)
def create_product(payload:ProductCreate,db:Session=Depends(get_db)):
    category=db.query(Category).filter(Category.category_name==payload.category.strip()).first()
    if not category:raise HTTPException(422,'Choose an existing category from the workbook.')
    supplier=db.get(Supplier,payload.supplier_id)
    if not supplier:raise HTTPException(422,'Choose an existing supplier.')
    shown_name=display_name(payload.product_name)
    try:identity=product_identity(shown_name,payload.net_weight,payload.unit)
    except ValueError as exc:raise HTTPException(422,str(exc))
    normalized_name,canonical_weight,canonical_unit=identity
    lock_names=[]
    try:
        if engine.dialect.name=='mysql':
            digest=hashlib.sha256(f'{payload.supplier_id}|{normalized_name}|{canonical_weight}|{canonical_unit}'.encode()).hexdigest()[:40]
            lock_names=[f'pi.{digest[:48]}',f'{engine.url.database}.products.id']
            for lock_name in lock_names:
                if db.execute(text('SELECT GET_LOCK(:lock_name, 10)'),{'lock_name':lock_name}).scalar()!=1:
                    raise HTTPException(503,'Timed out while checking product identity; retry the request.')
        duplicate=(db.query(Product,ProductSupplier).join(ProductSupplier,ProductSupplier.product_id==Product.id)
            .filter(ProductSupplier.supplier_id==payload.supplier_id,ProductSupplier.normalized_name==normalized_name,
                    ProductSupplier.canonical_weight==canonical_weight,ProductSupplier.canonical_unit==canonical_unit).first())
        if duplicate:
            p,_=duplicate
            raise HTTPException(409,detail={'message':'Product already exists for this supplier and size.','existing_product_id':p.id,
                'existing_product':{'id':p.id,'product_code':p.product_code,'product_name':p.product_name,'net_weight':p.net_weight,'unit':p.unit,'supplier_id':payload.supplier_id,'supplier_name':supplier.supplier_name}})
        values=payload.model_dump(exclude={'category','supplier_id'})
        values['product_name']=shown_name
        if engine.dialect.name=='mysql':values['id']=(db.query(func.max(Product.id)).scalar() or 0)+1
        product=Product(**values,category=category.category_name,category_id=category.id);db.add(product)
        db.flush();db.add(Inventory(product_id=product.id,current_stock=product.current_stock,minimum_stock=product.minimum_stock,reorder_level=product.reorder_level));db.add(ProductSupplier(product_id=product.id,supplier_id=supplier.id,normalized_name=normalized_name,canonical_weight=canonical_weight,canonical_unit=canonical_unit));db.commit();db.refresh(product)
    except IntegrityError:db.rollback();raise HTTPException(409,'Product code or barcode already exists.')
    finally:
        for lock_name in reversed(lock_names):
            try:db.execute(text('SELECT RELEASE_LOCK(:lock_name)'),{'lock_name':lock_name})
            except Exception:db.rollback()
    return {'id':product.id,'product_code':product.product_code,'product_name':product.product_name,'category':product.category,'supplier_id':supplier.id,'supplier_name':supplier.supplier_name}
@app.patch('/api/products/{pid}')
def update_product(pid:int,payload:ProductUpdate,db:Session=Depends(get_db)):
    product=db.get(Product,pid)
    if not product:raise HTTPException(404,'Product not found')
    values=payload.model_dump(exclude_unset=True)
    if 'category' in values:
        category=db.query(Category).filter(Category.category_name==values.pop('category').strip()).first()
        if not category:raise HTTPException(422,'Choose an existing category from the workbook.')
        product.category=category.category_name;product.category_id=category.id
    candidate_name=values.get('product_name',product.product_name)
    candidate_weight=values.get('net_weight',product.net_weight)
    candidate_unit=values.get('unit',product.unit)
    try:normalized_name,canonical_weight,canonical_unit=product_identity(candidate_name,candidate_weight,candidate_unit)
    except ValueError as exc:raise HTTPException(422,str(exc))
    supplier_links=db.query(ProductSupplier).filter(ProductSupplier.product_id==pid).all()
    for link in supplier_links:
        clash=db.query(ProductSupplier.product_id).filter(ProductSupplier.supplier_id==link.supplier_id,ProductSupplier.normalized_name==normalized_name,ProductSupplier.canonical_weight==canonical_weight,ProductSupplier.canonical_unit==canonical_unit,ProductSupplier.product_id!=pid).first()
        if clash:raise HTTPException(409,detail={'message':'Product identity conflicts with an existing product for this supplier.','existing_product_id':clash[0]})
    for key,value in values.items():setattr(product,key,value)
    product.product_name=display_name(product.product_name)
    for link in supplier_links:link.normalized_name=normalized_name;link.canonical_weight=canonical_weight;link.canonical_unit=canonical_unit
    product.updated_at=datetime.now()
    stock=db.get(Inventory,pid)
    if stock:stock.current_stock=product.current_stock;stock.minimum_stock=product.minimum_stock;stock.reorder_level=product.reorder_level
    else:db.add(Inventory(product_id=pid,current_stock=product.current_stock,minimum_stock=product.minimum_stock,reorder_level=product.reorder_level))
    try:db.commit()
    except IntegrityError:db.rollback();raise HTTPException(409,'Product update violates a database constraint.')
    return {'id':product.id,'product_code':product.product_code,'product_name':product.product_name,'category':product.category,'current_stock':product.current_stock}
@app.get('/api/products/{pid}')
def product(pid:int,db:Session=Depends(get_db)):
    p=db.get(Product,pid)
    if not p:raise HTTPException(404,'Product not found')
    return {'id':p.id,'product_code':p.product_code,'product_name':p.product_name,'category':p.category,'net_weight':p.net_weight,'unit':p.unit,'selling_price':p.selling_price,'purchase_price':p.purchase_price,'current_stock':p.current_stock,'reorder_level':p.reorder_level,'barcode':p.barcode}
@app.get('/api/inventory')
def inventory(category:str|None=None,db:Session=Depends(get_db)):
    since=date.today()-timedelta(days=30);q=db.query(SaleItem.product_id,func.sum(SaleItem.quantity)).join(Sale,Sale.id==SaleItem.sale_id).filter(Sale.sale_date>=since).group_by(SaleItem.product_id);demand={pid:float(qty or 0)/30 for pid,qty in q.all()};out=[]
    for p in product_rows(db,category).all():
        daily=demand.get(p.id,0);days=p.current_stock/daily if daily else None;status='Out of Stock' if p.current_stock<=0 else 'Critical' if p.current_stock<=p.minimum_stock else 'Low' if p.current_stock<=p.reorder_level else 'Healthy'
        out.append({'product_id':p.id,'product':p.product_name,'category':p.category,'current_stock':p.current_stock,'reorder_level':p.reorder_level,'average_daily_sales':round(daily,2),'days_of_stock':round(days,1) if days is not None else None,'stock_value':round(p.current_stock*p.purchase_price,2),'status':status})
    return out
@app.get('/api/inventory/low-stock')
def low_stock(db:Session=Depends(get_db)):return [x for x in inventory(db=db) if x['status']!='Healthy']
@app.get('/api/inventory/movements')
def inventory_movements(skip:int=0,limit:int=100,product_id:int|None=None,from_date:date|None=None,to_date:date|None=None,db:Session=Depends(get_db)):
    q=db.query(InventoryMovement,Product.product_name).join(Product,Product.id==InventoryMovement.product_id)
    if product_id:q=q.filter(InventoryMovement.product_id==product_id)
    q=bounds(q,from_date,to_date,InventoryMovement.movement_date);return [{'movement_id':m.id,'product_id':m.product_id,'product':n,'date':str(m.movement_date),'type':m.movement_type,'quantity':m.quantity,'reference':m.reference} for m,n in paginate(q.order_by(InventoryMovement.movement_date.desc()),skip,limit).all()]
@app.get('/api/reorder-recommendations')
def reorder_recommendations(db:Session=Depends(get_db)):
    stock=inventory(db=db);lead=float(db.query(func.avg(Supplier.lead_time_days)).scalar() or 7);lead=max(1,lead);out=[]
    for x in stock:
        if x['status']=='Healthy':continue
        p=db.get(Product,x['product_id']);daily=x['average_daily_sales'];safety=max(p.minimum_stock,daily*lead*.5);target=max(p.reorder_level+safety,daily*lead+safety);qty=max(0,round(target-p.current_stock))
        out.append({**x,'lead_time_days':round(lead),'safety_stock':round(safety,1),'suggested_quantity':qty,'basis':'Data-driven reorder recommendation'})
    db.query(ReorderRecommendation).delete(synchronize_session=False)
    db.add_all([ReorderRecommendation(product_id=x['product_id'],days_of_stock=x['days_of_stock'],suggested_quantity=x['suggested_quantity'],lead_time_days=x['lead_time_days']) for x in out]);db.commit()
    return out
@app.post('/api/suppliers',status_code=201)
def create_supplier(payload:SupplierCreate,db:Session=Depends(get_db)):
    name=display_name(payload.supplier_name)
    normalized=normalize_label(name);phone=display_name(payload.phone or '') or None
    lock_name=f'{engine.url.database}.suppliers.identity'
    try:
        if engine.dialect.name=='mysql' and db.execute(text('SELECT GET_LOCK(:n, 10)'),{'n':lock_name}).scalar()!=1:
            raise HTTPException(503,'Timed out while checking supplier identity; retry the request.')
        existing=db.query(Supplier).all()
        for supplier in existing:
            if normalize_label(supplier.supplier_name)==normalized and normalize_label(supplier.phone or '')==normalize_label(phone or ''):
                raise HTTPException(409,detail={'message':'Supplier already exists.','existing_supplier_id':supplier.id,'existing_supplier':{'supplier_id':supplier.id,'supplier_name':supplier.supplier_name,'phone':supplier.phone}})
        supplier=Supplier(supplier_name=name,phone=phone,lead_time_days=payload.lead_time_days)
        if engine.dialect.name=='mysql':supplier.id=(db.query(func.max(Supplier.id)).scalar() or 0)+1
        db.add(supplier);db.commit();db.refresh(supplier)
        return {'supplier_id':supplier.id,'supplier_name':supplier.supplier_name,'phone':supplier.phone,'lead_time_days':supplier.lead_time_days}
    except IntegrityError:db.rollback();raise HTTPException(409,'Supplier conflicts with an existing record.')
    finally:
        if engine.dialect.name=='mysql':
            try:db.execute(text('SELECT RELEASE_LOCK(:n)'),{'n':lock_name})
            except Exception:db.rollback()

@app.get('/api/suppliers')
def suppliers(skip:int=0,limit:int=100,db:Session=Depends(get_db)):
    q=db.query(Supplier,func.count(Purchase.id),func.coalesce(func.sum(Purchase.total),0)).outerjoin(Purchase,Purchase.supplier_id==Supplier.id).group_by(Supplier.id)
    result=[]
    for s,n,v in paginate(q,skip,limit).all():
        qty=db.query(func.coalesce(func.sum(PurchaseItem.quantity),0)).join(Purchase,Purchase.id==PurchaseItem.purchase_id).filter(Purchase.supplier_id==s.id).scalar() or 0
        result.append({'supplier_id':s.id,'supplier_name':s.supplier_name,'phone':s.phone,'lead_time_days':s.lead_time_days,'purchase_count':int(n),'purchase_value':float(v),'purchase_quantity':float(qty)})
    return result
@app.get('/api/purchases')
def purchases(skip:int=0,limit:int=100,supplier_id:int|None=None,from_date:date|None=None,to_date:date|None=None,db:Session=Depends(get_db)):
    q=db.query(Purchase,Supplier.supplier_name).join(Supplier,Supplier.id==Purchase.supplier_id)
    if supplier_id:q=q.filter(Purchase.supplier_id==supplier_id)
    q=bounds(q,from_date,to_date,Purchase.purchase_date);return [{'purchase_id':p.id,'supplier_id':p.supplier_id,'supplier':name,'date':str(p.purchase_date),'total':p.total,'status':p.status} for p,name in paginate(q.order_by(Purchase.purchase_date.desc()),skip,limit).all()]

@app.post('/api/purchases',status_code=201)
def create_purchase(payload:PurchaseCreate,db:Session=Depends(get_db)):
    supplier=db.get(Supplier,payload.supplier_id)
    if not supplier:raise HTTPException(422,'Choose an existing supplier.')
    products={}
    for item in payload.items:
        product=db.query(Product).filter(Product.id==item.product_id).with_for_update().first()
        if not product:raise HTTPException(422,f'Product {item.product_id} does not exist.')
        products[item.product_id]=product
    lock_name=f'{engine.url.database}.purchases.ids'
    acquired=False
    try:
        if engine.dialect.name=='mysql':
            acquired=db.execute(text('SELECT GET_LOCK(:n, 10)'),{'n':lock_name}).scalar()==1
            if not acquired:raise HTTPException(503,'Timed out while allocating purchase IDs; retry the request.')
        purchase_id=(db.query(func.max(Purchase.id)).scalar() or 0)+1
        purchase_total=sum(float(item.quantity)*float(item.unit_cost) for item in payload.items)
        purchase=Purchase(id=purchase_id,supplier_id=supplier.id,purchase_date=payload.purchase_date or date.today(),total=purchase_total,status=payload.status.strip())
        db.add(purchase);db.flush()
        next_movement=(db.query(func.max(InventoryMovement.id)).scalar() or 0)+1
        grouped={}
        for item in payload.items:
            product=products[item.product_id]
            old_stock=float(product.current_stock or 0);qty=float(item.quantity);cost=float(item.unit_cost)
            new_stock=old_stock+qty
            product.purchase_price=((old_stock*float(product.purchase_price))+qty*cost)/new_stock if new_stock else cost
            product.current_stock=new_stock;product.updated_at=datetime.now()
            stock=db.get(Inventory,product.id)
            if stock:stock.current_stock=new_stock
            else:db.add(Inventory(product_id=product.id,current_stock=new_stock,minimum_stock=product.minimum_stock,reorder_level=product.reorder_level))
            db.add(PurchaseItem(purchase_id=purchase.id,product_id=product.id,quantity=qty,unit_cost=cost))
            db.add(InventoryMovement(id=next_movement,product_id=product.id,movement_date=purchase.purchase_date,movement_type='purchase',quantity=qty,reference=f'purchase:{purchase.id}'));next_movement+=1
            grouped[product.id]=product
        for product in grouped.values():
            name,weight,unit=product_identity(product.product_name,product.net_weight,product.unit)
            link=db.query(ProductSupplier).filter(ProductSupplier.product_id==product.id,ProductSupplier.supplier_id==supplier.id).first()
            if link:
                link.normalized_name=name;link.canonical_weight=weight;link.canonical_unit=unit
            else:
                conflict=db.query(ProductSupplier,Product).join(Product,Product.id==ProductSupplier.product_id).filter(ProductSupplier.supplier_id==supplier.id,ProductSupplier.normalized_name==name,ProductSupplier.canonical_weight==weight,ProductSupplier.canonical_unit==unit).first()
                if conflict:
                    raise HTTPException(409,detail={'message':'This product and size are already registered under another product record for this supplier. Select the existing product.','existing_product_id':conflict[1].id})
                db.add(ProductSupplier(product_id=product.id,supplier_id=supplier.id,normalized_name=name,canonical_weight=weight,canonical_unit=unit))
        db.commit()
        return {'purchase_id':purchase.id,'supplier_id':supplier.id,'supplier':supplier.supplier_name,'purchase_date':str(purchase.purchase_date),'total':purchase.total,'status':purchase.status,'items':[{'product_id':item.product_id,'quantity':item.quantity,'unit_cost':item.unit_cost} for item in payload.items]}
    except HTTPException:
        db.rollback();raise
    except IntegrityError:
        db.rollback();raise HTTPException(409,'Purchase conflicts with existing product/supplier identity or database constraints.')
    finally:
        if acquired:
            try:db.execute(text('SELECT RELEASE_LOCK(:n)'),{'n':lock_name})
            except Exception:db.rollback()
@app.get('/api/sales')
def sales(skip:int=0,limit:int=100,from_date:date|None=None,to_date:date|None=None,product_id:int|None=None,category:str|None=None,db:Session=Depends(get_db)):
    q=sales_query(db,from_date,to_date,product_id,category);return [{'sale_id':s.id,'sale_code':s.sale_code,'sale_date':str(s.sale_date),'total':s.total,'status':s.status} for s in paginate(q.order_by(Sale.sale_date.desc()),skip,limit).all()]
@app.get('/api/expenses')
def expenses(skip:int=0,limit:int=100,from_date:date|None=None,to_date:date|None=None,category:str|None=None,db:Session=Depends(get_db)):
    q=db.query(Expense);q=bounds(q,from_date,to_date,Expense.expense_date)
    if category:q=q.filter(Expense.category==category)
    return [{'expense_id':e.id,'date':str(e.expense_date),'category':e.category,'description':e.description,'amount':e.amount} for e in paginate(q.order_by(Expense.expense_date.desc()),skip,limit).all()]
@app.get('/api/payments')
def payments(skip:int=0,limit:int=100,from_date:date|None=None,to_date:date|None=None,status:str|None=None,db:Session=Depends(get_db)):
    q=bounds(db.query(Payment),from_date,to_date,Payment.payment_date)
    if status:q=q.filter(Payment.status==status)
    return [{'payment_id':p.id,'date':str(p.payment_date),'amount':p.amount,'payment_type':p.payment_type,'reference':p.reference,'related_type':p.related_type,'related_id':p.related_id,'status':p.status} for p in paginate(q.order_by(Payment.payment_date.desc()),skip,limit).all()]
@app.get('/api/returns')
def returns(skip:int=0,limit:int=100,from_date:date|None=None,to_date:date|None=None,product_id:int|None=None,db:Session=Depends(get_db)):
    q=db.query(BusinessReturn)
    if product_id:q=q.join(ReturnItem,ReturnItem.return_id==BusinessReturn.id).filter(ReturnItem.product_id==product_id).distinct()
    q=bounds(q,from_date,to_date,BusinessReturn.return_date);return [{'return_id':r.id,'date':str(r.return_date),'sale_id':r.sale_id,'reason':r.reason,'value':r.total_value} for r in paginate(q.order_by(BusinessReturn.return_date.desc()),skip,limit).all()]
@app.get('/api/finance/summary')
def finance_summary(from_date:date|None=None,to_date:date|None=None,db:Session=Depends(get_db)):return summary(db,from_date,to_date)
@app.get('/api/finance/profit-trend')
def profit_trend(from_date:date|None=None,to_date:date|None=None,db:Session=Depends(get_db)):
    rev=bounds(db.query(period_month().label('month'),func.sum(Sale.total).label('revenue')).group_by(period_month()),from_date,to_date,Sale.sale_date).subquery()
    cogs_q=db.query(period_month().label('month'),func.sum(SaleItem.quantity*SaleItem.unit_cost).label('cogs')).join(Sale,Sale.id==SaleItem.sale_id).group_by(period_month()).subquery()
    exp_q=db.query(func.strftime('%Y-%m',Expense.expense_date).label('month') if engine.dialect.name=='sqlite' else func.date_format(Expense.expense_date,'%Y-%m').label('month'),func.sum(Expense.amount).label('expenses')).group_by('month').subquery()
    return [{'month':m,'revenue':float(r or 0),'cogs':float(c or 0),'gross_profit':float(r or 0)-float(c or 0),'expenses':float(e or 0),'net_profit':float(r or 0)-float(c or 0)-float(e or 0)} for m,r,c,e in db.query(rev.c.month,rev.c.revenue,cogs_q.c.cogs,exp_q.c.expenses).outerjoin(cogs_q,rev.c.month==cogs_q.c.month).outerjoin(exp_q,rev.c.month==exp_q.c.month).order_by(rev.c.month).all()]
@app.get('/api/forecast')
def forecast(horizon:int=3,db:Session=Depends(get_db)):
    historical=monthly(db=db);values=[x['revenue'] for x in historical];window=values[-3:];estimate=sum(window)/len(window) if window else 0
    last=date.today().replace(day=1);forecast_values=[]
    for i in range(1,max(1,min(horizon,12))+1):
        month=(last.month-1+i)%12+1;year=last.year+(last.month-1+i)//12;forecast_values.append({'month':f'{year:04d}-{month:02d}','revenue_estimate':round(estimate,2)})
    return {'method':'3-month moving average','label':'Estimate, not guaranteed','horizon_periods':len(forecast_values),'historical':historical,'forecast':forecast_values}
@app.get('/api/insights')
def insights(db:Session=Depends(get_db)):
    from analytics.anomaly_detection import z_score_anomalies
    out=[];low=[p for p in inventory(db=db) if p['status']!='Healthy']
    if low:out.append({'type':'inventory','severity':'warning','title':'Reorder attention needed','description':f'{len(low)} products are at or below reorder level.','related_metric':'low_stock_items','supporting_value':len(low)})
    ms=monthly(db=db)
    if len(ms)>=2:
        prev,cur=ms[-2]['revenue'],ms[-1]['revenue'];pct=(cur-prev)/prev*100 if prev else None
        if pct is not None:out.append({'type':'sales','severity':'info' if pct>=0 else 'warning','title':'Monthly revenue change','description':f'Revenue changed {pct:+.1f}% from the prior month.','related_metric':'revenue_growth_pct','supporting_value':round(pct,2)})
    daily_sales=db.query(Sale.sale_date,func.sum(Sale.total)).filter(Sale.status=='completed').group_by(Sale.sale_date).order_by(Sale.sale_date).all()
    for a in z_score_anomalies([float(v) for _,v in daily_sales]):out.append({'type':'sales','severity':'warning','title':'Potential anomaly in sales','description':f'Daily sales on {daily_sales[a["index"]][0]} are unusual compared with the observed period.','related_metric':'daily_revenue','supporting_value':a['value']})
    daily_exp=db.query(Expense.expense_date,func.sum(Expense.amount)).group_by(Expense.expense_date).order_by(Expense.expense_date).all()
    for a in z_score_anomalies([float(v) for _,v in daily_exp]):out.append({'type':'expense','severity':'warning','title':'Potential anomaly in expenses','description':f'Expenses on {daily_exp[a["index"]][0]} are unusual relative to recorded daily expense totals.','related_metric':'daily_expense','supporting_value':a['value']})
    daily_returns=db.query(BusinessReturn.return_date,func.sum(BusinessReturn.total_value)).group_by(BusinessReturn.return_date).order_by(BusinessReturn.return_date).all()
    for a in z_score_anomalies([float(v) for _,v in daily_returns]):out.append({'type':'returns','severity':'warning','title':'Potential anomaly in returns','description':f'Return value on {daily_returns[a["index"]][0]} is unusual compared with recorded return dates.','related_metric':'return_value','supporting_value':a['value']})
    cut=date.today()-timedelta(days=30);prior=cut-timedelta(days=30)
    recent=dict(db.query(SaleItem.product_id,func.sum(SaleItem.quantity)).join(Sale,Sale.id==SaleItem.sale_id).filter(Sale.sale_date>cut).group_by(SaleItem.product_id).all())
    before=dict(db.query(SaleItem.product_id,func.sum(SaleItem.quantity)).join(Sale,Sale.id==SaleItem.sale_id).filter(Sale.sale_date>prior,Sale.sale_date<=cut).group_by(SaleItem.product_id).all())
    ratios=[(pid,float(recent.get(pid,0))/max(float(before.get(pid,0)),1)) for pid in set(recent)|set(before)]
    for a in z_score_anomalies([ratio for _,ratio in ratios]):
        pid=ratios[a['index']][0];p=db.get(Product,pid);out.append({'type':'product_demand','severity':'info','title':'Potential anomaly in product demand','description':f'Demand for {p.product_name} changed unusually between adjacent 30-day periods.','related_metric':'recent_demand_ratio','supporting_value':a['value']})
    if not out and not ms:out.append({'type':'data','severity':'info','title':'Insights will appear as records accumulate','description':'Load completed sales and operating records to calculate trends and potential anomalies.','related_metric':'sales','supporting_value':0})
    db.query(BusinessInsight).delete(synchronize_session=False)
    db.add_all([BusinessInsight(type=x['type'],title=x['title'],description=x['description'],severity=x['severity'],related_metric=x['related_metric'],supporting_value=float(x['supporting_value'])) for x in out]);db.commit()
    return out
@app.get('/api/etl/status')
def etl_status(db:Session=Depends(get_db)):
    p=ROOT/'data/processed/etl_status.json';w=ROOT/'data/processed/watcher_status.json'
    st=json.loads(p.read_text()) if p.exists() else {'status':'not_run','last_success':None,'errors':[],'warnings':[],'records':{}}
    latest=db.query(EtlLog).order_by(EtlLog.started_at.desc()).first()
    if latest:
        details=_etl_details(latest);st={**details,'status':latest.status,'records_processed':latest.records_processed,'warnings_count':latest.warnings,'errors_count':latest.errors,'completed_at':latest.finished_at.isoformat()+'Z' if latest.finished_at and latest.finished_at.tzinfo is None else latest.finished_at.isoformat() if latest.finished_at else None}
    try:st['watcher']=json.loads(w.read_text(encoding='utf-8')) if w.exists() else {'status':'stopped','monitoring':False}
    except (OSError,ValueError):st['watcher']={'status':'stopped','monitoring':False}
    st['watcher']=_watcher_state()
    return st
@app.get('/api/etl/logs')
def etl_logs(limit:int=Query(20,ge=1,le=100),db:Session=Depends(get_db)):
    out=[]
    for log in db.query(EtlLog).order_by(EtlLog.started_at.desc()).limit(limit).all():
        details=_etl_details(log)
        out.append({'run_id':details.get('run_id'),'source_file':details.get('source_file'),'started_at':log.started_at.isoformat() if log.started_at else None,'completed_at':log.finished_at.isoformat() if log.finished_at else None,'status':log.status,'duration_seconds':details.get('duration_seconds'),'rows_processed':log.records_processed,'validation_errors':details.get('validation_errors',[]),'error_message':(details.get('errors') or [None])[0]})
    return out
@app.post('/api/etl/run')
def etl_run():
    result=subprocess.run([sys.executable,str(ROOT/'etl/pipeline.py')],capture_output=True,text=True,cwd=ROOT)
    output=result.stdout[-4000:];error=result.stderr[-2000:]
    for secret in (settings.db_password,settings.database_url or ''):
        if secret:output=output.replace(secret,'<redacted>');error=error.replace(secret,'<redacted>')
    return {'returncode':result.returncode,'output':output,'error':error}
