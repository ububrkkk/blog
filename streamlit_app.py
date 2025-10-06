"""Streamlit Cloud entrypoint (repo root).

This shim ensures `src/` is on sys.path, then runs the real app.
Set Streamlit "App file path" to `streamlit_app.py`.
"""

from __future__ import annotations

import os
import sys

SRC = os.path.join(os.path.dirname(__file__), "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from blog_keyword_analyzer.streamlit_platform import main  # type: ignore  # noqa: E402

if __name__ == "__main__":
    main()

