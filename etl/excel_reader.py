import pandas as pd
from pathlib import Path
FILE=Path(__file__).resolve().parents[1]/'data/raw/business_data.xlsx'
def read_workbook(path=FILE):
    if not Path(path).exists():raise FileNotFoundError(f'Workbook not found: {path}')
    try:return pd.read_excel(path,sheet_name=None)
    except Exception as exc:raise ValueError(f'Unable to read Excel workbook {path}: {exc}') from exc
