"""
Preparación de datos para validación: creación de "columnas de control".

Great Expectations valida, en esencia, columna por columna. Las reglas que
relacionan dos o más campos (edad vs. fecha de nacimiento, ciudad vs. país,
total vs. componentes del cálculo) se resuelven con el patrón estándar de
calidad de datos: **calcular columnas derivadas antes de validar**.

Este módulo aplica las transformaciones de CONTROL sobre el DataFrame:
no corrige nada (eso lo hace ``src.cleaning.cleaner``), solo expone en
columnas la evidencia que las expectativas de GX necesitan.
"""
from __future__ import annotations

import pandas as pd

from src.config import (
    AMOUNT_TOLERANCE,
    CITY_TO_COUNTRY,
    CURRENCIES_BY_COUNTRY,
    REF_DATE,
    TAX_RATE,
)


def enrich_customers(df: pd.DataFrame) -> pd.DataFrame:
    """
    Añade columnas de control al dataset de clientes.

    Columns
    -------
    age_calc : int
        Edad calculada desde ``birth_date`` hasta ``REF_DATE``.
    age_diff : float
        ``age - age_calc``; debe estar en ``[-1, 1]`` (consistencia).
    city_country_ok : bool
        True si la ciudad pertenece al país declarado (consistencia).
    last_update_year : int
        Año de ``last_update``; debe ser reciente (oportunidad).

    """
    out = df.copy()

    ref = pd.Timestamp(REF_DATE)
    birth = pd.to_datetime(out["birth_date"], errors="coerce")
    # Convención del sistema fuente: edad = año de referencia − año de nacimiento.
    out["age_calc"] = ref.year - birth.dt.year
    out["age_diff"] = pd.to_numeric(out["age"], errors="coerce") - out["age_calc"]

    out["city_country_ok"] = out.apply(
        lambda row: CITY_TO_COUNTRY.get(row["city"]) == row["country"], axis=1
    )

    last_update = pd.to_datetime(out["last_update"], errors="coerce")
    out["last_update_year"] = last_update.dt.year.fillna(0).astype(int)

    return out


def enrich_orders(df: pd.DataFrame, valid_customer_ids: set[str]) -> pd.DataFrame:
    """
    Añade columnas de control al dataset de órdenes.

    Parameters
    ----------
    df : pd.DataFrame
        Órdenes crudas o limpias.
    valid_customer_ids : set[str]
        IDs de clientes válidos (dataset de clientes limpio) para la
        validación referencial orden → cliente.

    Notes
    -----
    * Normaliza la llave ``customer_id`` a 6 dígitos (``CUST-000042``), paso
      típico de "conformación de llaves" cuando dos sistemas usan formatos
      distintos. Los IDs inexistentes seguirán fallando la validación
      referencial, que es justo lo que queremos detectar.

    """
    out = df.copy()

    # --- Conformación de llave cliente (CUST-000042) -----------------------
    digits = out["customer_id"].astype(str).str.extract(r"^CUST-(\d+)$")[0]
    out["customer_id"] = "CUST-" + digits.str.zfill(6)

    # --- Fechas en formato datetime (NaT si son inválidas o nulas) ---------
    for col in (
        "customer_registration_date",
        "order_date",
        "shipping_date",
        "delivery_date",
    ):
        out[f"{col}_dt"] = pd.to_datetime(out[col], errors="coerce")

    # --- Referencial: la orden apunta a un cliente existente ---------------
    out["customer_ok"] = out["customer_id"].isin(valid_customer_ids)

    # --- Consistencia: moneda coherente con el país ------------------------
    out["currency_expected"] = out["customer_country"].map(CURRENCIES_BY_COUNTRY)
    out["currency_ok"] = out["customer_currency"] == out["currency_expected"]

    # --- Consistencia financiera: total = subtotal - descuento + IVA + envío
    expected_total = (
        out["subtotal"]
        - out["discount_amount"]
        + out["tax_amount"]
        + out["shipping_cost"]
    )
    out["total_diff"] = (out["total_amount"] - expected_total).abs()

    # --- Jerarquía temporal: registro → orden → envío → entrega ------------
    # Comparaciones con NaT dan False: las fechas nulas fallan, que es lo
    # que queremos que ocurra en el dataset crudo.
    out["order_after_reg"] = (
        out["order_date_dt"] >= out["customer_registration_date_dt"]
    )
    out["ship_after_order"] = out["shipping_date_dt"] > out["order_date_dt"]
    out["deliver_after_ship"] = out["delivery_date_dt"] > out["shipping_date_dt"]

    return out


# La tolerancia se usa en la suite (expectativa sobre total_diff) y queda
# importada aquí para documentar de dónde sale el valor por defecto.
TOLERANCE_DOC: float = AMOUNT_TOLERANCE
TAX_RATE_DOC: float = TAX_RATE
