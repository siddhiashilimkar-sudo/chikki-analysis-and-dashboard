from pathlib import Path
from datetime import datetime,timezone
from time import perf_counter
from uuid import uuid4
import json,sys,logging
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from etl.excel_reader import read_workbook
from etl.cleaner import validate,clean
from etl.transformer import transform
from etl.mysql_loader import load
from backend.app.database import Base,engine,SessionLocal
from backend.app.models import EtlLog
from backend.app.config import settings
Base.metadata.create_all(engine)
logging.basicConfig(level=logging.INFO,format='%(asctime)s %(levelname)s %(message)s')
def run():
    target=ROOT/'data/processed/etl_status.json';previous=json.loads(target.read_text()) if target.exists() else {}
    started=datetime.now(timezone.utc);clock=perf_counter();run_id=str(uuid4());relative_source='data/raw/business_data.xlsx'
    status={'run_id':run_id,'source_file':relative_source,'started_at':started.isoformat(),'completed_at':None,'duration_seconds':None,'status':'failed','errors':[],'validation_errors':[],'warnings':[],'records':{},'rows_processed':0,'data_classification':settings.data_classification.upper(),'last_success':previous.get('last_success'),'last_failed':None}
    try:
        sheets=read_workbook();errors,warnings=validate(sheets);status['errors']=errors;status['warnings']=warnings
        status['validation_errors']=errors.copy()
        if errors:raise ValueError('Workbook validation failed; see data/processed/etl_status.json')
        sheets=transform(clean(sheets));load(sheets)
        status['records']={name:int(len(df)) for name,df in sheets.items()};status['rows_processed']=sum(status['records'].values());status['status']='success';status['last_success']=datetime.now(timezone.utc).isoformat()
        logging.info('ETL loaded %s rows across %s sheets',sum(status['records'].values()),len(sheets))
    except Exception as exc:
        safe_error=str(exc)
        for secret in (settings.db_password,settings.database_url or ''):
            if secret:safe_error=safe_error.replace(secret,'<redacted>')
        status['errors'].append(safe_error);status['last_failed']=datetime.now(timezone.utc).isoformat();logging.error('ETL failed (%s): %s',type(exc).__name__,safe_error)
    completed=datetime.now(timezone.utc);status['completed_at']=completed.isoformat();status['finished_at']=status['completed_at'];status['duration_seconds']=round(perf_counter()-clock,3)
    target.parent.mkdir(parents=True,exist_ok=True);target.write_text(json.dumps(status,indent=2),encoding='utf-8')
    db=SessionLocal()
    try:
        db.add(EtlLog(started_at=started.replace(tzinfo=None),finished_at=completed.replace(tzinfo=None),status=status['status'],records_processed=status['rows_processed'],warnings=len(status['warnings']),errors=len(status['errors']),details=json.dumps(status)))
        db.commit()
    except Exception:db.rollback();logging.exception('Could not persist ETL log to database')
    finally:db.close()
    return status
if __name__=='__main__':
    result=run();print(json.dumps(result,indent=2));sys.exit(0 if result['status']=='success' else 1)
