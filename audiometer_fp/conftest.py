"""Add the project root to sys.path so tests find the ``audiometer`` package
without an explicit install step."""

import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
