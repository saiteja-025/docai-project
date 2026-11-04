# Root entrypoint to support `uvicorn main:app` directly from the project root.
import os
import sys

_current_dir = os.path.dirname(os.path.abspath(__file__))
if _current_dir not in sys.path:
    sys.path.insert(0, _current_dir)

from backend.main import app

__all__ = ["app"]
