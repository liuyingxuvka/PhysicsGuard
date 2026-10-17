import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "models/owners/hierarchical_model_mesh"))

from model import run_model


def main() -> dict[str, bool]:
    return run_model()


if __name__ == "__main__":
    from flowguard.map.runner import run_owner
    raise SystemExit(run_owner(main))
