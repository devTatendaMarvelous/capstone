"""File and console logging for acquisition runs."""

from __future__ import annotations

import logging
from pathlib import Path

from utils.config import data_dir


def get_logger(name: str = "smartcrop.acquisition") -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)
    path = data_dir() / "logs" / "acquisition.log"
    path.parent.mkdir(parents=True, exist_ok=True)
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s", "%Y-%m-%d %H:%M:%S")
    file_handler = logging.FileHandler(path, encoding="utf-8")
    file_handler.setFormatter(formatter)
    stream = logging.StreamHandler()
    stream.setFormatter(formatter)
    logger.addHandler(file_handler)
    logger.addHandler(stream)
    logger.propagate = False
    return logger
