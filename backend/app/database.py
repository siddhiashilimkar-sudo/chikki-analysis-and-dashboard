from sqlalchemy import create_engine,event
from sqlalchemy.orm import sessionmaker,DeclarativeBase
from .config import settings
url=settings.connection_url;sqlite=str(url).startswith('sqlite')
engine=create_engine(url,connect_args={'check_same_thread':False} if sqlite else {},pool_pre_ping=True)
if sqlite:
    @event.listens_for(engine,'connect')
    def enable_sqlite_foreign_keys(connection,record):
        cursor=connection.cursor();cursor.execute('PRAGMA foreign_keys=ON');cursor.close()
SessionLocal=sessionmaker(bind=engine,autoflush=False,autocommit=False)
class Base(DeclarativeBase):pass
def get_db():
    db=SessionLocal()
    try:yield db
    finally:db.close()
