from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL
class Settings(BaseSettings):
    database_mode:str="sqlite"
    database_url:str|None=None
    db_host:str="127.0.0.1"
    db_port:int=3306
    db_name:str="maganlal_chikki_bi"
    db_user:str="root"
    db_password:str=""
    cors_origins:str="http://localhost:5173"
    data_classification:str="demo"
    data_stale_after_minutes:int=60
    model_config=SettingsConfigDict(env_file=".env",extra="ignore")
    @property
    def connection_url(self):
        if self.database_url:return self.database_url
        if self.database_mode.lower()=="mysql":
            return URL.create("mysql+pymysql",username=self.db_user,password=self.db_password,host=self.db_host,port=self.db_port,database=self.db_name,query={"charset":"utf8mb4"})
        return "sqlite:///./maganlal_demo.db"
settings=Settings()
