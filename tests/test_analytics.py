import unittest
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from analytics.anomaly_detection import z_score_anomalies
from analytics.insights_engine import inventory_insights
from analytics.inventory_analysis import stock_status
from analytics.reorder_engine import recommendation
from analytics.forecasting import moving_average
from analytics.finance_analysis import profit
class AnalyticsTests(unittest.TestCase):
    def test_profit_and_margins(self):
        x=profit(100,60,15);self.assertEqual(x['gross_profit'],40);self.assertEqual(x['net_profit'],25);self.assertEqual(x['net_margin_pct'],25)
    def test_reorder_includes_lead_demand_and_safety(self):
        x=recommendation(5,20,2,lead_time_days=7);self.assertGreater(x['suggested_quantity'],0);self.assertEqual(x['days_of_stock'],2.5)
    def test_forecast_is_moving_average(self):
        x=moving_average([2,4,6]);self.assertEqual(x['estimate'],4);self.assertEqual(x['horizon'],[4,4,4])
    def test_anomaly_labels_are_potential(self):
        out=z_score_anomalies([1,1,1,1,20],threshold=1.5);self.assertTrue(out);self.assertEqual(out[0]['label'],'Potential anomaly')
    def test_stock_health_states(self):
        self.assertEqual(stock_status(0,10),'Out of stock');self.assertEqual(stock_status(5,10),'Low');self.assertEqual(stock_status(20,10),'Healthy')
    def test_insight_requires_low_stock_evidence(self):
        self.assertEqual(inventory_insights([{'current_stock':25,'reorder_level':10}]),[]);self.assertTrue(inventory_insights([{'current_stock':2,'reorder_level':10}]))
if __name__=='__main__':unittest.main()
