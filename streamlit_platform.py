from __future__ import annotations

import os
import sys

# Add src/ to path so imports work on Streamlit Cloud
SRC = os.path.join(os.path.dirname(__file__), "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from blog_keyword_analyzer.streamlit_platform import main  # type: ignore  # noqa: E402

if __name__ == "__main__":
    main()

