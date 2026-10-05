from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from etl.pipeline import run
if __name__=="__main__":
    s=run();print(s);sys.exit(0 if s["status"]=="success" else 1)
