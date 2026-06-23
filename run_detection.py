"""Run the analytics pipeline from the command line (no dashboard).

Usage:
    python run_detection.py --config config.yaml
"""
from __future__ import annotations

import argparse
import logging

from src.config import Config
from src.pipeline import Pipeline


def main() -> None:
    parser = argparse.ArgumentParser(description="Smart Road Vehicle Analytics")
    parser.add_argument("--config", default="config.yaml", help="Path to config.yaml")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    cfg = Config.load(args.config)
    pipeline = Pipeline(cfg)
    pipeline.run()


if __name__ == "__main__":
    main()
