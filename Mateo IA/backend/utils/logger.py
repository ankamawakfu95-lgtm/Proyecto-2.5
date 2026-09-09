"""Configuración de logging sin efectos secundarios inesperados."""
from __future__ import annotations

import logging
import os
from typing import Optional


def setup_logger(name: str = "Mateo", level: Optional[int] = None) -> logging.Logger:
    """Devuelve un logger configurado una sola vez."""
    logger = logging.getLogger(name)
    if level is None:
        level = getattr(logging, os.getenv("MATEO_LOG_LEVEL", "INFO").upper(), logging.INFO)
    logger.setLevel(level)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
        logger.addHandler(handler)
    logger.propagate = False
    return logger
