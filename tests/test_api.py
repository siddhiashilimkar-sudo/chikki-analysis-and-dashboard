import unittest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.database import SessionLocal
from backend.app.models import Product,Inventory,InventoryMovement,Purchase,PurchaseItem,ProductSupplier,Supplier
class ApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.client=TestClient(app)
    @classmethod
    def tearDownClass(cls):cls.client.close()
    def cleanup_identity_supplier(self,supplier_id):
        db=SessionLocal()
        try:
            purchase_ids=[x[0] for x in db.query(Purchase.id).filter(Purchase.supplier_id==supplier_id).all()]
            if purchase_ids:db.query(PurchaseItem).filter(PurchaseItem.purchase_id.in_(purchase_ids)).delete(synchronize_session=False)
            product_ids=[x[0] for x in db.query(Product.id).filter(Product.product_code.like('TEST-ID-%')).all()]
            if product_ids:
                db.query(InventoryMovement).filter(InventoryMovement.product_id.in_(product_ids)).delete(synchronize_session=False)
                db.query(ProductSupplier).filter(ProductSupplier.product_id.in_(product_ids)).delete(synchronize_session=False)
                db.query(Inventory).filter(Inventory.product_id.in_(product_ids)).delete(synchronize_session=False)
                db.query(Product).filter(Product.id.in_(product_ids)).delete(synchronize_session=False)
            if purchase_ids:db.query(Purchase).filter(Purchase.id.in_(purchase_ids)).delete(synchronize_session=False)
            db.query(ProductSupplier).filter(ProductSupplier.supplier_id==supplier_id).delete(synchronize_session=False)
            db.query(Supplier).filter(Supplier.id==supplier_id).delete(synchronize_session=False);db.commit()
        finally:db.close()
    def test_health_and_all_required_read_endpoints(self):
        paths=['/health','/api/dashboard/summary','/api/dashboard/freshness','/api/dashboard/sales-trend','/api/dashboard/weekly-sales','/api/dashboard/monthly-sales','/api/dashboard/top-products','/api/dashboard/slow-products','/api/dashboard/category-performance','/api/inventory','/api/inventory/low-stock','/api/inventory/movements','/api/products','/api/suppliers','/api/purchases','/api/sales','/api/expenses','/api/payments','/api/returns','/api/finance/summary','/api/finance/profit-trend','/api/forecast','/api/reorder-recommendations','/api/insights','/api/etl/status','/api/etl/logs']
        for path in paths:
            with self.subTest(path=path):self.assertEqual(self.client.get(path).status_code,200)
    def test_products_detail_and_pagination(self):
        rows=self.client.get('/api/products?limit=2').json();self.assertEqual(len(rows),2);self.assertEqual(self.client.get('/api/products/'+str(rows[0]['id'])).status_code,200)
    def test_product_create_and_update(self):
        supplier=self.client.get('/api/suppliers').json()[0]
        payload={'product_code':'TEST-CRUD-001','product_name':'Test Chikki','supplier_id':supplier['supplier_id'],'category':'Peanut Chikki','net_weight':100,'unit':'g','selling_price':100,'purchase_price':60,'current_stock':5,'minimum_stock':2,'reorder_level':4,'barcode':'TEST-CRUD-001'}
        created=self.client.post('/api/products',json=payload);self.assertEqual(created.status_code,201);pid=created.json()['id']
        changed=self.client.patch(f'/api/products/{pid}',json={'current_stock':8});self.assertEqual(changed.status_code,200);self.assertEqual(changed.json()['current_stock'],8)
        self.assertEqual(self.client.get('/api/inventory').status_code,200)
        db=SessionLocal()
        try:db.query(Inventory).filter(Inventory.product_id==pid).delete();db.query(Product).filter(Product.id==pid).delete();db.commit()
        finally:db.close()
    def test_supplier_product_identity_and_purchase_cost_workflow(self):
        supplier=self.client.post('/api/suppliers',json={'supplier_name':'  Identity   Supplier ','phone':'TEST-ID-001','lead_time_days':5})
        self.assertEqual(supplier.status_code,201);sid=supplier.json()['supplier_id']
        self.addCleanup(self.cleanup_identity_supplier,sid)
        duplicate_supplier=self.client.post('/api/suppliers',json={'supplier_name':'identity supplier','phone':' TEST-ID-001 ','lead_time_days':5})
        self.assertEqual(duplicate_supplier.status_code,409)
        other=self.client.post('/api/suppliers',json={'supplier_name':'Identity Supplier Other','phone':'TEST-ID-002','lead_time_days':8})
        self.assertEqual(other.status_code,201);other_sid=other.json()['supplier_id']
        self.addCleanup(self.cleanup_identity_supplier,other_sid)
        base={'product_code':'TEST-ID-500-X','product_name':'Crushed   Groundnut','supplier_id':sid,'category':'Peanut Chikki','net_weight':500,'unit':'gm','selling_price':250,'purchase_price':200,'current_stock':5,'minimum_stock':1,'reorder_level':3,'barcode':None}
        created=self.client.post('/api/products',json=base);self.assertEqual(created.status_code,201);pid=created.json()['id'];self.assertEqual(created.json()['product_name'],'Crushed Groundnut')
        try:
            duplicate={**base,'product_code':'TEST-ID-DUP-X','product_name':' crushed groundnut ','unit':'g','purchase_price':180}
            response=self.client.post('/api/products',json=duplicate)
            self.assertEqual(response.status_code,409);self.assertEqual(response.json()['detail']['existing_product_id'],pid)
            small={**base,'product_code':'TEST-ID-250-X','net_weight':250,'unit':'g','purchase_price':100,'current_stock':0}
            small_resp=self.client.post('/api/products',json=small);self.assertEqual(small_resp.status_code,201);small_id=small_resp.json()['id']
            other_supplier={**base,'product_code':'TEST-ID-OTHER-X','supplier_id':other_sid,'purchase_price':150,'current_stock':0}
            other_resp=self.client.post('/api/products',json=other_supplier);self.assertEqual(other_resp.status_code,201);other_id=other_resp.json()['id']
            purchase=self.client.post('/api/purchases',json={'supplier_id':sid,'status':'paid','items':[{'product_id':pid,'quantity':10,'unit_cost':180}]})
            self.assertEqual(purchase.status_code,201);self.assertAlmostEqual(purchase.json()['total'],1800)
            self.assertEqual(self.client.get(f'/api/products/{pid}').json()['current_stock'],15)
            db=SessionLocal()
            try:
                product=db.get(Product,pid);self.assertAlmostEqual(product.purchase_price,(5*200+10*180)/15,places=2)
                self.assertEqual(db.query(PurchaseItem).filter(PurchaseItem.product_id==pid).count(),1)
                self.assertEqual(db.query(InventoryMovement).filter(InventoryMovement.product_id==pid,InventoryMovement.movement_type=='purchase').count(),1)
            finally:db.close()
            # Unit aliases and normalized names match; a distinct size or supplier remains allowed.
            dup_equivalent={**base,'product_code':'TEST-ID-EQUIV-X','product_name':'CRUSHED GROUNDNUT','unit':'g','purchase_price':99}
            self.assertEqual(self.client.post('/api/products',json=dup_equivalent).status_code,409)
            one_kg={**base,'product_code':'TEST-ID-KG-X','product_name':'Whole Nut Test','net_weight':1,'unit':'kg','current_stock':0}
            kg_resp=self.client.post('/api/products',json=one_kg);self.assertEqual(kg_resp.status_code,201);kg_id=kg_resp.json()['id']
            one_thousand_g={**one_kg,'product_code':'TEST-ID-G-X','net_weight':1000,'unit':'g'}
            self.assertEqual(self.client.post('/api/products',json=one_thousand_g).status_code,409)
            self.assertNotEqual(pid,small_id);self.assertNotEqual(pid,other_id)
        finally:
            db=SessionLocal()
            try:
                product_ids=[x for x in (locals().get('pid'),locals().get('small_id'),locals().get('other_id')) if x]
                purchase_ids=[x[0] for x in db.query(Purchase.id).filter(Purchase.supplier_id.in_([sid,other_sid])).all()]
                if purchase_ids:db.query(PurchaseItem).filter(PurchaseItem.purchase_id.in_(purchase_ids)).delete(synchronize_session=False)
                if product_ids:
                    db.query(InventoryMovement).filter(InventoryMovement.product_id.in_(product_ids)).delete(synchronize_session=False)
                    db.query(ProductSupplier).filter(ProductSupplier.product_id.in_(product_ids)).delete(synchronize_session=False)
                    db.query(Inventory).filter(Inventory.product_id.in_(product_ids)).delete(synchronize_session=False)
                    db.query(Product).filter(Product.id.in_(product_ids)).delete(synchronize_session=False)
                if purchase_ids:db.query(Purchase).filter(Purchase.id.in_(purchase_ids)).delete(synchronize_session=False)
                db.query(Supplier).filter(Supplier.id.in_([sid,other_sid])).delete(synchronize_session=False);db.commit()
            finally:db.close()
    def test_dashboard_calculations(self):
        s=self.client.get('/api/dashboard/summary').json();self.assertGreater(s['revenue'],0);self.assertGreater(s['sales'],0);self.assertAlmostEqual(s['gross_profit'],s['revenue']-s['cogs'],places=1);self.assertAlmostEqual(s['net_profit'],s['gross_profit']-s['operating_expenses'],places=1)
    def test_freshness_is_database_backed_and_logs_are_structured(self):
        freshness=self.client.get('/api/dashboard/freshness').json();self.assertTrue(freshness['database_connected']);self.assertIn(freshness['data_status'],{'LIVE','STALE'});self.assertTrue(freshness.get('last_data_update'))
        logs=self.client.get('/api/etl/logs?limit=1').json();self.assertGreaterEqual(len(logs),1);self.assertIn(logs[0]['status'],{'success','failed'});self.assertIsNotNone(logs[0]['completed_at'])
    def test_etl_post(self):
        result=self.client.post('/api/etl/run');self.assertEqual(result.status_code,200);self.assertEqual(result.json()['returncode'],0)
        status=self.client.get('/api/etl/status').json();self.assertEqual(status['status'],'success');self.assertGreater(status['rows_processed'],0);self.assertGreaterEqual(status['duration_seconds'],0)
if __name__=='__main__':unittest.main()
