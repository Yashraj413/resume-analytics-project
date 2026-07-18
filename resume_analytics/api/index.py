import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dashboard.app import app as dash_app

app = dash_app.server