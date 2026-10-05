import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from backend.app.database import Base,engine
import backend.app.models
Base.metadata.create_all(engine)
print('Database initialized:',engine.url.render_as_string(hide_password=True) if hasattr(engine.url,'render_as_string') else engine.url)
