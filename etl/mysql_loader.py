from sqlalchemy import delete
from backend.app.database import SessionLocal
from backend.app.models import (Category,Product,Supplier,ProductSupplier,Sale,SaleItem,Purchase,PurchaseItem,Inventory,InventoryMovement,Expense,Payment,BusinessReturn,ReturnItem,ForecastResult,BusinessInsight,ReorderRecommendation)
from backend.app.product_identity import product_identity

def _records(frame):
    import pandas as pd
    return frame.astype(object).where(pd.notna(frame),None).to_dict('records')
def load(sheets):
    db=SessionLocal()
    try:
        # Replace complete workbook snapshot transactionally; delete children before parents.
        for model in (ReturnItem,BusinessReturn,ReorderRecommendation,ForecastResult,BusinessInsight,Payment,Expense,InventoryMovement,Inventory,ProductSupplier,PurchaseItem,Purchase,SaleItem,Sale,Product,Supplier,Category):db.execute(delete(model))
        db.flush()
        categories={int(r['category_id']):str(r['category']) for r in _records(sheets['Categories'])}
        db.add_all([Category(id=k,category_name=v) for k,v in categories.items()])
        db.add_all([Supplier(id=int(r['supplier_id']),supplier_name=str(r['supplier_name']),phone=str(r.get('phone') or ''),lead_time_days=int(r.get('lead_time_days') or 7)) for r in _records(sheets['Suppliers'])]);db.flush()
        category_ids={v:k for k,v in categories.items()}
        db.add_all([Product(id=int(r['product_id']),product_code=str(r['product_code']),product_name=str(r['product_name']),category_id=category_ids[str(r['category'])],category=str(r['category']),net_weight=float(r.get('net_weight') or 100),unit=str(r.get('unit') or 'g'),selling_price=float(r['selling_price']),purchase_price=float(r['purchase_price']),current_stock=float(r['current_stock']),minimum_stock=float(r.get('minimum_stock') or 0),reorder_level=float(r.get('reorder_level') or 0),barcode=str(r.get('barcode') or '') or None) for r in _records(sheets['Products'])]);db.flush()
        db.add_all([Sale(id=int(r['sale_id']),sale_code=str(r['sale_code']),sale_date=r['sale_date'],total=float(r['total']),status=str(r.get('status') or 'completed')) for r in _records(sheets['Sales'])])
        db.add_all([Purchase(id=int(r['purchase_id']),supplier_id=int(r['supplier_id']),purchase_date=r['purchase_date'],total=float(r['total']),status=str(r.get('status') or 'paid')) for r in _records(sheets['Purchases'])]);db.flush()
        db.add_all([SaleItem(sale_id=int(r['sale_id']),product_id=int(r['product_id']),quantity=float(r['quantity']),unit_price=float(r['unit_price']),unit_cost=float(r['unit_cost'])) for r in _records(sheets['Sale_Items'])])
        db.add_all([PurchaseItem(purchase_id=int(r['purchase_id']),product_id=int(r['product_id']),quantity=float(r['quantity']),unit_cost=float(r['unit_cost'])) for r in _records(sheets['Purchase_Items'])])
        db.flush()
        # Supplier/product identity is derived from transaction provenance already present in the workbook.
        pairs=db.query(Product,Purchase.supplier_id).join(PurchaseItem,PurchaseItem.product_id==Product.id).join(Purchase,Purchase.id==PurchaseItem.purchase_id).distinct().all()
        identities={};links=[]
        for product,supplier_id in pairs:
            name,weight,unit=product_identity(product.product_name,product.net_weight,product.unit)
            key=(int(supplier_id),name,weight,unit)
            if key in identities:
                if identities[key]!=product.id:raise ValueError('Workbook contains duplicate product name/weight/supplier identities; import rejected without changing the current dataset.')
                continue
            identities[key]=product.id
            links.append(ProductSupplier(product_id=product.id,supplier_id=supplier_id,normalized_name=name,canonical_weight=weight,canonical_unit=unit))
        db.add_all(links)
        db.add_all([Inventory(product_id=int(r['product_id']),current_stock=float(r['current_stock']),minimum_stock=float(r['minimum_stock']),reorder_level=float(r['reorder_level'])) for r in _records(sheets['Inventory'])])
        db.add_all([InventoryMovement(id=int(r['movement_id']),product_id=int(r['product_id']),movement_date=r['movement_date'],movement_type=str(r['movement_type']),quantity=float(r['quantity']),reference=str(r.get('reference') or '')) for r in _records(sheets['Inventory_Movements'])])
        db.add_all([Expense(id=int(r['expense_id']),expense_date=r['expense_date'],category=str(r['category']),description=str(r.get('description') or ''),amount=float(r['amount'])) for r in _records(sheets['Expenses'])])
        db.add_all([Payment(id=int(r['payment_id']),payment_date=r['payment_date'],amount=float(r['amount']),payment_type=str(r['payment_type']),reference=str(r.get('reference') or ''),related_type=str(r.get('related_type') or ''),related_id=int(r.get('related_id') or 0),status=str(r['status'])) for r in _records(sheets['Payments'])])
        db.add_all([BusinessReturn(id=int(r['return_id']),return_date=r['return_date'],sale_id=int(r['sale_id']),reason=str(r['reason']),total_value=float(r['total_value'])) for r in _records(sheets['Returns'])]);db.flush()
        db.add_all([ReturnItem(id=int(r['return_item_id']),return_id=int(r['return_id']),product_id=int(r['product_id']),quantity=float(r['quantity']),unit_value=float(r['unit_value'])) for r in _records(sheets['Return_Items'])])
        db.commit()
    except Exception:db.rollback();raise
    finally:db.close()
