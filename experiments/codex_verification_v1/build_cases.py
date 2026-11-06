#!/usr/bin/env python3
# Compatibility entry point; canonical source: cases/build_cases.py
import runpy
from pathlib import Path
runpy.run_path(str(Path(__file__).resolve().parent/'cases/build_cases.py'), run_name='__main__')
