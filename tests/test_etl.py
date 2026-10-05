import unittest
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from etl.excel_reader import read_workbook
from etl.cleaner import validate
class WorkbookTests(unittest.TestCase):
    def test_all_expected_sheets_validate(self):
        sheets=read_workbook();self.assertEqual(set(sheets),set(__import__('etl.cleaner',fromlist=['REQUIRED_COLUMNS']).REQUIRED_COLUMNS));self.assertEqual(validate(sheets)[0],[])
    def test_duplicate_product_ids_are_errors(self):
        sheets=read_workbook();sheets['Products']=sheets['Products'].copy();sheets['Products'].loc[1,'product_id']=sheets['Products'].loc[0,'product_id'];self.assertTrue(any('duplicate IDs' in e for e in validate(sheets)[0]))
    def test_missing_column_is_error(self):
        sheets=read_workbook();sheets['Sales']=sheets['Sales'].drop(columns=['total']);self.assertTrue(any('missing required columns' in e for e in validate(sheets)[0]))
if __name__=='__main__':unittest.main()
