"""Logging con Rich, requerido por los generadores del taller."""
from __future__ import annotations

import logging

from rich.logging import RichHandler

_FORMAT = "%(message)s"
_DATEFMT = "[%X]"


def setup_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """
    Configura y devuelve un logger con salida colorida vía Rich.

    Parameters
    ----------
    name : str
        Nombre del logger (habitualmente ``__name__``).
    level : int, optional
        Nivel de logging, por defecto ``logging.INFO``.

    Returns
    -------
    logging.Logger
        Logger configurado (sin handlers duplicados).

    """
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = RichHandler(rich_tracebacks=True, show_path=False, markup=True)
        handler.setFormatter(logging.Formatter(_FORMAT, datefmt=_DATEFMT))
        logger.addHandler(handler)
        logger.setLevel(level)
        logger.propagate = False
    return logger
