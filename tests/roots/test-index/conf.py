import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

extensions = ["sphinxcontrib.prefect"]

prefect_modules = ["index_pkg.first", "index_pkg.second"]
prefect_main_flows = [
    "index_pkg.first.alpha",
    "index_pkg.second.explicit_main",
    "index_pkg.outside.outside_flow",
]
