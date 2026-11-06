"""
Configuración central del taller (Módulo 5 · Unidad 5: CI/CD para pipelines de datos).

Principio DataOps que enseña este archivo: **una sola fuente de verdad**.
Todas las rutas, umbrales y constantes de negocio viven aquí; ningún otro
módulo define rutas "mágicas" dispersas.
"""
from __future__ import annotations

from pathlib import Path

# ---------------------------------------------------------------------------
# Constantes de negocio (importadas de los generadores: fuente única)
# ---------------------------------------------------------------------------
from src.generators.data_generator import VALID_COUNTRIES
from src.generators.orders_generator import (
    CURRENCIES_BY_COUNTRY,
    ORDER_STATUS,
    PAYMENT_METHODS,
    PRODUCT_CATALOG,
    SHIPPING_METHODS,
)

# Fecha de referencia "hoy" del taller. Es la misma que usan los generadores
# para birth_date y last_update. Fija (no datetime.now()) para que CADA
# ejecución sea 100% reproducible: mismo dato de entrada → mismo resultado.
REF_DATE: str = "2026-09-15"

# Oportunidad: un cliente se considera "actualizado" si last_update >= esta fecha.
MIN_LAST_UPDATE: str = "2023-01-01"

# Rangos de negocio plausibles (dimensión EXACTITUD).
AGE_RANGE: tuple[int, int] = (18, 85)
INCOME_RANGE: tuple[float, float] = (15_000.0, 250_000.0)
CREDIT_SCORE_RANGE: tuple[int, int] = (300, 850)

# Tolerancia (en unidades monetarias) para comparaciones de montos.
AMOUNT_TOLERANCE: float = 0.01

# Expresión regular de un email "válido" (dimensión VALIDEZ).
EMAIL_REGEX: str = r"^[\w.+-]+@[\w-]+\.[\w.-]+$"

# Formato de fecha ISO que exigen los generadores (dimensión VALIDEZ).
DATE_REGEX: str = r"^\d{4}-\d{2}-\d{2}$"

# ---------------------------------------------------------------------------
# Rutas del proyecto
# ---------------------------------------------------------------------------
PROJECT_ROOT: Path = Path(__file__).resolve().parents[1]
DATA_DIR: Path = PROJECT_ROOT / "data"
RAW_DIR: Path = DATA_DIR / "raw"
CLEAN_DIR: Path = DATA_DIR / "clean"
REPORTS_DIR: Path = DATA_DIR / "reportes"

CUSTOMERS_RAW: Path = RAW_DIR / "customers.csv"
ORDERS_RAW: Path = RAW_DIR / "orders.csv"
CUSTOMERS_CLEAN: Path = CLEAN_DIR / "customers_clean.csv"
CUSTOMERS_CLEAN_PARQUET: Path = CLEAN_DIR / "customers_clean.parquet"
ORDERS_CLEAN: Path = CLEAN_DIR / "orders_clean.csv"
ORDERS_CLEAN_PARQUET: Path = CLEAN_DIR / "orders_clean.parquet"

# Base (sin extensión) de cada reporte de calidad → .html y .json
REPORT_CUSTOMERS_RAW: Path = REPORTS_DIR / "clientes_raw"
REPORT_CUSTOMERS_CLEAN: Path = REPORTS_DIR / "clientes_clean"
REPORT_ORDERS_RAW: Path = REPORTS_DIR / "ordenes_raw"
REPORT_ORDERS_CLEAN: Path = REPORTS_DIR / "ordenes_clean"


def ensure_dirs() -> None:
    """Crea la estructura de carpetas de datos si no existe."""
    for folder in (RAW_DIR, CLEAN_DIR, REPORTS_DIR):
        folder.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Mapas auxiliares derivados (consistencia ciudad-país, costo de envío, etc.)
# ---------------------------------------------------------------------------
CITY_TO_COUNTRY: dict[str, str] = {
    city: country for country, cities in VALID_COUNTRIES.items() for city in cities
}

SHIPPING_COST_BY_METHOD: dict[str, float] = {
    method: float(cfg["cost"]) for method, cfg in SHIPPING_METHODS.items()
}

TAX_RATE: float = 0.16  # IVA usado por el generador de órdenes
