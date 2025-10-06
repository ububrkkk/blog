"""Streamlit Cloud entrypoint (repo root).

This shim ensures `src/` is on sys.path, then runs the real app.
Set Streamlit "App file path" to `streamlit_app.py`.
"""

from __future__ import annotations

import os
import sys
import runpy

SRC = os.path.join(os.path.dirname(__file__), "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

try:
    from blog_keyword_analyzer.streamlit_platform import main  # type: ignore  # noqa: E402
except Exception:
    # Fallback: run the module file directly if import fails (path issues on cloud)
    APP = os.path.join(SRC, "blog_keyword_analyzer", "streamlit_platform.py")
    ns = runpy.run_path(APP)
    main = ns.get("main")
    if main is None:
        raise SystemExit("Cannot load app entrypoint")

if __name__ == "__main__":
    main()
