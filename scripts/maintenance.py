"""Explicit local maintenance switch; never changes profiles or model data."""

import argparse
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["on", "off"])
    mode = parser.parse_args().mode
    flag = Path(__file__).resolve().parents[1] / "data" / "runtime" / "maintenance.flag"
    if mode == "on":
        flag.parent.mkdir(parents=True, exist_ok=True)
        flag.write_text("Maintenance in progress\n", encoding="utf-8")
    else:
        flag.unlink(missing_ok=True)
    print(f"Maintenance {mode}; refresh the browser to see the change.")


if __name__ == "__main__":
    main()
