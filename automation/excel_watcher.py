from pathlib import Path
from threading import Timer,Lock
from datetime import datetime,timezone
import sys,time,json,logging,os
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from etl.pipeline import run
TARGET=ROOT/'data/raw/business_data.xlsx';STATUS=ROOT/'data/processed/watcher_status.json';logging.basicConfig(level=logging.INFO,format='%(asctime)s %(levelname)s %(message)s')
lock=Lock();processing_lock=Lock();timer=None;last_processed_signature=None
def file_signature():
    try:
        stat=TARGET.stat();return (stat.st_mtime_ns,stat.st_size)
    except OSError:return None
def write_status(**values):
    STATUS.parent.mkdir(parents=True,exist_ok=True)
    try:old=json.loads(STATUS.read_text(encoding='utf-8')) if STATUS.exists() else {}
    except (OSError,ValueError):old={}
    old.update(values);temp=STATUS.with_suffix('.tmp');temp.write_text(json.dumps(old,indent=2),encoding='utf-8');temp.replace(STATUS)
def execute():
    global last_processed_signature
    with processing_lock:
        signature=file_signature()
        if signature is None or signature==last_processed_signature:return
        last_processed_signature=signature
        logging.info('Workbook save settled; validating and loading ETL')
        write_status(status='processing',monitoring=True,processing_started_at=datetime.now(timezone.utc).isoformat())
        result=run();write_status(status='monitoring',monitoring=True,last_sync=datetime.now(timezone.utc).isoformat(),last_sync_status=result['status'],last_errors=result['errors'],last_run_id=result['run_id'],last_run_duration_seconds=result['duration_seconds'],last_rows_processed=result['rows_processed'])
        logging.info('ETL result: %s',result['status'])
class Handler(FileSystemEventHandler):
    def on_any_event(self,event):
        global timer,last_processed_signature
        if event.is_directory or event.event_type not in ('created','modified','moved'):return
        path=Path(getattr(event,'dest_path',None) or event.src_path)
        if path.name.lower()!=TARGET.name.lower():return
        with lock:
            signature=file_signature()
            if signature is None or signature==last_processed_signature:return
            write_status(status='monitoring',monitoring=True,last_event=datetime.now(timezone.utc).isoformat())
            if timer:timer.cancel()
            timer=Timer(2.0,execute);timer.daemon=True;timer.start()
if __name__=='__main__':
    observer=Observer();observer.schedule(Handler(),str(TARGET.parent),recursive=False);observer.start();last_processed_signature=file_signature();write_status(status='monitoring',monitoring=True,pid=os.getpid(),started_at=datetime.now(timezone.utc).isoformat(),heartbeat_at=datetime.now(timezone.utc).isoformat());logging.info('Watching %s',TARGET)
    try:
        while True:
            time.sleep(10);write_status(heartbeat_at=datetime.now(timezone.utc).isoformat())
    except KeyboardInterrupt:observer.stop()
    observer.join();
    if timer:timer.cancel()
    write_status(status='stopped',monitoring=False,stopped_at=datetime.now(timezone.utc).isoformat())
