import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

extensions = ["sphinxcontrib.prefect"]

exclude_patterns = ["description.rst", "description.md"]
