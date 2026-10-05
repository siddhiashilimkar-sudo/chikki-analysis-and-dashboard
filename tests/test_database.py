import unittest
from sqlalchemy import inspect,text
from backend.app.database import engine,SessionLocal
from backend.app.models import Product,Sale,SaleItem,Purchase,Supplier,Expense,Payment,BusinessReturn,InventoryMovement,Inventory,Category,EtlLog
class DatabaseTests(unittest.TestCase):
    def test_database_connects_and_expected_tables_exist(self):
        with engine.connect() as c:self.assertEqual(c.execute(text('SELECT 1')).scalar(),1)
        required={'products','categories','sales','sale_items','purchases','purchase_items','suppliers','product_suppliers','inventory','inventory_movements','expenses','payments','returns','return_items','forecast_results','business_insights','reorder_recommendations','etl_logs'}
        self.assertTrue(required.issubset(set(inspect(engine).get_table_names())))
        for table in required:self.assertTrue(inspect(engine).get_pk_constraint(table)['constrained_columns'],table)
        unique_names={x.get('name') for x in inspect(engine).get_unique_constraints('product_suppliers')}
        self.assertIn('uq_product_supplier_identity',unique_names)
    def test_loaded_demo_counts_and_relations(self):
        db=SessionLocal()
        try:
            self.assertEqual(db.query(Product).count(),40);self.assertEqual(db.query(Sale).count(),1500);self.assertEqual(db.query(Supplier).count(),12);self.assertGreater(db.query(SaleItem).count(),2000);self.assertEqual(db.query(Category).count(),8);self.assertGreater(db.query(EtlLog).count(),0)
        finally:db.close()
if __name__=='__main__':unittest.main()
