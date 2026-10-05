from datetime import date
from pydantic import BaseModel,ConfigDict,Field,field_validator
class ProductCreate(BaseModel):
    model_config=ConfigDict(extra='forbid')
    product_code:str=Field(min_length=1,max_length=40)
    product_name:str=Field(min_length=1,max_length=160)
    supplier_id:int=Field(gt=0)
    category:str=Field(min_length=1,max_length=80)
    net_weight:float=Field(gt=0)
    unit:str=Field(default='g',max_length=12)
    selling_price:float=Field(gt=0)
    purchase_price:float=Field(gt=0)
    current_stock:float=Field(ge=0)
    minimum_stock:float=Field(ge=0)
    reorder_level:float=Field(ge=0)
    barcode:str|None=None
class ProductUpdate(BaseModel):
    model_config=ConfigDict(extra='forbid')
    product_name:str|None=Field(default=None,min_length=1,max_length=160)
    category:str|None=Field(default=None,min_length=1,max_length=80)
    net_weight:float|None=Field(default=None,gt=0)
    unit:str|None=Field(default=None,max_length=12)
    selling_price:float|None=Field(default=None,gt=0)
    purchase_price:float|None=Field(default=None,gt=0)
    current_stock:float|None=Field(default=None,ge=0)
    minimum_stock:float|None=Field(default=None,ge=0)
    reorder_level:float|None=Field(default=None,ge=0)
    barcode:str|None=None

class SupplierCreate(BaseModel):
    model_config=ConfigDict(extra='forbid')
    supplier_name:str=Field(min_length=1,max_length=160)
    phone:str|None=Field(default=None,max_length=40)
    lead_time_days:int=Field(default=7,ge=1,le=365)

class PurchaseLine(BaseModel):
    model_config=ConfigDict(extra='forbid')
    product_id:int=Field(gt=0)
    quantity:float=Field(gt=0)
    unit_cost:float=Field(gt=0)

class PurchaseCreate(BaseModel):
    model_config=ConfigDict(extra='forbid')
    supplier_id:int=Field(gt=0)
    purchase_date:date|None=None
    status:str=Field(default='paid',min_length=1,max_length=20)
    items:list[PurchaseLine]=Field(min_length=1)
    @field_validator('purchase_date',mode='before')
    @classmethod
    def default_purchase_date(cls,value):
        return value or date.today()
