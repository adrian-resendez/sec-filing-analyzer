from __future__ import annotations

import logging
import sys


def configure_logging(level: int = logging.INFO) -> None:
    root_logger = logging.getLogger()
    if root_logger.handlers:
        return

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s %(levelname)s [%(name)s] %(message)s",
            "%Y-%m-%d %H:%M:%S",
        )
    )

    root_logger.setLevel(level)
    root_logger.addHandler(handler)


def get_logger(name: str) -> logging.Logger:
    configure_logging()
    return logging.getLogger(name)
