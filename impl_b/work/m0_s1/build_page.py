"""Compatibility entry: render current course pages from this project's JSON."""
from pathlib import Path
import runpy
runpy.run_path(str(Path(__file__).resolve().parents[2] / 'scripts/render_course.py'), run_name='__main__')
