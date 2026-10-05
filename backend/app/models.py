from datetime import datetime,timezone
def utcnow():return datetime.now(timezone.utc).replace(tzinfo=None)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Float, Date, DateTime, ForeignKey, Boolean, Integer, Text, Numeric, UniqueConstraint
from .database import Base
class Category(Base):
    __tablename__="categories"
    id:Mapped[int]=mapped_column("category_id",primary_key=True)
    category_name:Mapped[str]=mapped_column(String(80),unique=True,index=True)
class Supplier(Base):
    __tablename__="suppliers"
    id:Mapped[int]=mapped_column("supplier_id",primary_key=True)
    supplier_name:Mapped[str]=mapped_column(String(160),index=True)
    phone:Mapped[str|None]=mapped_column(String(40),nullable=True)
    lead_time_days:Mapped[int]=mapped_column(Integer,default=7)
class Product(Base):
    __tablename__="products"
    id:Mapped[int]=mapped_column("product_id",primary_key=True,autoincrement=True)
    product_code:Mapped[str]=mapped_column(String(40),unique=True,index=True)
    product_name:Mapped[str]=mapped_column(String(160),index=True)
    category_id:Mapped[int|None]=mapped_column(ForeignKey("categories.category_id"),nullable=True,index=True)
    category:Mapped[str]=mapped_column(String(80),index=True)
    net_weight:Mapped[float]=mapped_column(Float,default=100)
    unit:Mapped[str]=mapped_column(String(12),default="g")
    selling_price:Mapped[float]=mapped_column(Float)
    purchase_price:Mapped[float]=mapped_column(Float)
    current_stock:Mapped[float]=mapped_column(Float,default=0)
    minimum_stock:Mapped[float]=mapped_column(Float,default=10)
    reorder_level:Mapped[float]=mapped_column(Float,default=20)
    barcode:Mapped[str|None]=mapped_column(String(80),nullable=True,index=True)
    active:Mapped[bool]=mapped_column(Boolean,default=True)
    created_at:Mapped[datetime]=mapped_column(DateTime,default=utcnow)
    updated_at:Mapped[datetime]=mapped_column(DateTime,default=utcnow,onupdate=utcnow)
class ProductSupplier(Base):
    """Supplier-qualified product identity; the source workbook records supplier on purchases."""
    __tablename__="product_suppliers"
    __table_args__=(
        UniqueConstraint("supplier_id","normalized_name","canonical_weight","canonical_unit",name="uq_product_supplier_identity"),
        UniqueConstraint("product_id","supplier_id",name="uq_product_supplier_pair"),
    )
    id:Mapped[int]=mapped_column("product_supplier_id",Integer,primary_key=True,autoincrement=True)
    product_id:Mapped[int]=mapped_column(ForeignKey("products.product_id",ondelete="CASCADE"),index=True)
    supplier_id:Mapped[int]=mapped_column(ForeignKey("suppliers.supplier_id",ondelete="CASCADE"),index=True)
    normalized_name:Mapped[str]=mapped_column(String(160),nullable=False)
    canonical_weight:Mapped[float]=mapped_column(Numeric(16,6),nullable=False)
    canonical_unit:Mapped[str]=mapped_column(String(20),nullable=False)
class Sale(Base):
    __tablename__="sales"
    id:Mapped[int]=mapped_column("sale_id",primary_key=True)
    sale_date:Mapped[Date]=mapped_column(Date,index=True)
    sale_code:Mapped[str]=mapped_column(String(40),unique=True)
    total:Mapped[float]=mapped_column(Float)
    status:Mapped[str]=mapped_column(String(20),default="completed",index=True)
class SaleItem(Base):
    __tablename__="sale_items"
    id:Mapped[int]=mapped_column("sale_item_id",primary_key=True,autoincrement=True)
    sale_id:Mapped[int]=mapped_column(ForeignKey("sales.sale_id",ondelete="CASCADE"),index=True)
    product_id:Mapped[int]=mapped_column(ForeignKey("products.product_id"),index=True)
    quantity:Mapped[float]=mapped_column(Float)
    unit_price:Mapped[float]=mapped_column(Float)
    unit_cost:Mapped[float]=mapped_column(Float)
class Purchase(Base):
    __tablename__="purchases"
    id:Mapped[int]=mapped_column("purchase_id",primary_key=True)
    supplier_id:Mapped[int]=mapped_column(ForeignKey("suppliers.supplier_id"),index=True)
    purchase_date:Mapped[Date]=mapped_column(Date,index=True)
    total:Mapped[float]=mapped_column(Float)
    status:Mapped[str]=mapped_column(String(20),default="paid")
class PurchaseItem(Base):
    __tablename__="purchase_items"
    id:Mapped[int]=mapped_column("purchase_item_id",primary_key=True,autoincrement=True)
    purchase_id:Mapped[int]=mapped_column(ForeignKey("purchases.purchase_id",ondelete="CASCADE"),index=True)
    product_id:Mapped[int]=mapped_column(ForeignKey("products.product_id"),index=True)
    quantity:Mapped[float]=mapped_column(Float)
    unit_cost:Mapped[float]=mapped_column(Float)
class Inventory(Base):
    __tablename__="inventory"
    product_id:Mapped[int]=mapped_column(ForeignKey("products.product_id"),primary_key=True)
    current_stock:Mapped[float]=mapped_column(Float)
    minimum_stock:Mapped[float]=mapped_column(Float)
    reorder_level:Mapped[float]=mapped_column(Float)
    updated_at:Mapped[datetime]=mapped_column(DateTime,default=utcnow,onupdate=utcnow)
class InventoryMovement(Base):
    __tablename__="inventory_movements"
    id:Mapped[int]=mapped_column("movement_id",primary_key=True)
    product_id:Mapped[int]=mapped_column(ForeignKey("products.product_id"),index=True)
    movement_date:Mapped[Date]=mapped_column(Date,index=True)
    movement_type:Mapped[str]=mapped_column(String(30))
    quantity:Mapped[float]=mapped_column(Float)
    reference:Mapped[str]=mapped_column(String(80),default="")
class Expense(Base):
    __tablename__="expenses"
    id:Mapped[int]=mapped_column("expense_id",primary_key=True)
    expense_date:Mapped[Date]=mapped_column(Date,index=True)
    category:Mapped[str]=mapped_column(String(80),index=True)
    description:Mapped[str]=mapped_column(String(255),default="")
    amount:Mapped[float]=mapped_column(Float)
class Payment(Base):
    __tablename__="payments"
    id:Mapped[int]=mapped_column("payment_id",primary_key=True)
    payment_date:Mapped[Date]=mapped_column(Date,index=True)
    amount:Mapped[float]=mapped_column(Float)
    payment_type:Mapped[str]=mapped_column(String(30))
    reference:Mapped[str]=mapped_column(String(80),default="")
    related_type:Mapped[str]=mapped_column(String(20),default="")
    related_id:Mapped[int]=mapped_column(Integer,default=0,index=True)
    status:Mapped[str]=mapped_column(String(20),index=True)
class BusinessReturn(Base):
    __tablename__="returns"
    id:Mapped[int]=mapped_column("return_id",primary_key=True)
    return_date:Mapped[Date]=mapped_column(Date,index=True)
    sale_id:Mapped[int]=mapped_column(ForeignKey("sales.sale_id"),index=True)
    reason:Mapped[str]=mapped_column(String(255),default="")
    total_value:Mapped[float]=mapped_column(Float)
class ReturnItem(Base):
    __tablename__="return_items"
    id:Mapped[int]=mapped_column("return_item_id",primary_key=True)
    return_id:Mapped[int]=mapped_column(ForeignKey("returns.return_id",ondelete="CASCADE"),index=True)
    product_id:Mapped[int]=mapped_column(ForeignKey("products.product_id"),index=True)
    quantity:Mapped[float]=mapped_column(Float)
    unit_value:Mapped[float]=mapped_column(Float)
class ForecastResult(Base):
    __tablename__="forecast_results"
    id:Mapped[int]=mapped_column("forecast_id",primary_key=True,autoincrement=True)
    product_id:Mapped[int|None]=mapped_column(ForeignKey("products.product_id"),nullable=True,index=True)
    generated_at:Mapped[datetime]=mapped_column(DateTime,default=utcnow)
    period_start:Mapped[Date]=mapped_column(Date)
    horizon_days:Mapped[int]=mapped_column(Integer)
    forecast_quantity:Mapped[float]=mapped_column(Float)
    method:Mapped[str]=mapped_column(String(80))
class BusinessInsight(Base):
    __tablename__="business_insights"
    id:Mapped[int]=mapped_column("insight_id",primary_key=True,autoincrement=True)
    generated_at:Mapped[datetime]=mapped_column(DateTime,default=utcnow,index=True)
    type:Mapped[str]=mapped_column(String(40))
    title:Mapped[str]=mapped_column(String(160))
    description:Mapped[str]=mapped_column(Text)
    severity:Mapped[str]=mapped_column(String(20))
    related_metric:Mapped[str]=mapped_column(String(80))
    supporting_value:Mapped[float]=mapped_column(Float)
class ReorderRecommendation(Base):
    __tablename__="reorder_recommendations"
    id:Mapped[int]=mapped_column("recommendation_id",primary_key=True,autoincrement=True)
    product_id:Mapped[int]=mapped_column(ForeignKey("products.product_id"),index=True)
    generated_at:Mapped[datetime]=mapped_column(DateTime,default=utcnow)
    days_of_stock:Mapped[float|None]=mapped_column(Float,nullable=True)
    suggested_quantity:Mapped[float]=mapped_column(Float)
    lead_time_days:Mapped[int]=mapped_column(Integer)
class EtlLog(Base):
    __tablename__="etl_logs"
    id:Mapped[int]=mapped_column("etl_id",primary_key=True,autoincrement=True)
    started_at:Mapped[datetime]=mapped_column(DateTime,default=utcnow)
    finished_at:Mapped[datetime|None]=mapped_column(DateTime,nullable=True)
    status:Mapped[str]=mapped_column(String(20),index=True)
    records_processed:Mapped[int]=mapped_column(Integer,default=0)
    warnings:Mapped[int]=mapped_column(Integer,default=0)
    errors:Mapped[int]=mapped_column(Integer,default=0)
    details:Mapped[str]=mapped_column(Text,default="{}")
