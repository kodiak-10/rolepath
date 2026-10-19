"""Public hosting entrypoint: authentication is mandatory before loading the app."""
import os
import runpy
from pathlib import Path
os.environ['ROLEPATH_CLOUD'] = '1'
runpy.run_path(str(Path(__file__).with_name('app.py')), run_name='__main__')
