
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.converter_core import DEFAULT_OUTPUT_FOLDER, run_profile
from app.output_delivery import publish_to_network


def run_all(logger=print):
    DEFAULT_OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)
    results = []

    for profile in ("30D_SALES", "CLOSING_STOCK", "STOCK_INTRANSIT", "SCCT"):
        result = run_profile(profile, DEFAULT_OUTPUT_FOLDER, logger=logger)
        result["network_output"] = str(publish_to_network(
            Path(result["output"]),
            profile,
            logger=logger,
        ))
        results.append(result)

    return results


if __name__ == "__main__":
    run_all()
