"""
Limpieza de datos con pandas: reparar lo reparable, descartar lo demás.

Este módulo responde a los hallazgos de Great Expectations con una política
explícita, decisión típica de un ingeniero de datos en producción:

* **REPARAR**  → cuando existe una regla determinística que restaura el valor
  correcto (edad desde birth_date, moneda según país, recálculo financiero).
* **DESCARTAR** → cuando el valor verdadero es desconocido y no hay base
  para reconstruirlo (email inválido, cliente inexistente, descuento ilegible).

Cada regla está etiquetada con la dimensión de calidad que atiende, para que
la clase pueda mapear 1 a 1: *expectativa fallida → acción de limpieza*.
"""
from __future__ import annotations

import pandas as pd

from src.config import (
    AGE_RANGE,
    CITY_TO_COUNTRY,
    CREDIT_SCORE_RANGE,
    EMAIL_REGEX,
    INCOME_RANGE,
    MIN_LAST_UPDATE,
    REF_DATE,
    SHIPPING_COST_BY_METHOD,
    TAX_RATE,
)
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


# ---------------------------------------------------------------------------
# Clientes
# ---------------------------------------------------------------------------


def clean_customers(df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, int]]:
    """
    Limpia el dataset de clientes.

    Returns
    -------
    tuple[pd.DataFrame, dict[str, int]]
        (dataset limpio, conteo de filas afectadas por cada regla).

    """
    stats: dict[str, int] = {}
    out = df.copy()

    def _drop(mask: pd.Series, regla: str) -> None:
        nonlocal out
        eliminadas = int((~mask).sum())
        if eliminadas:
            out = out[mask]
        stats[regla] = stats.get(regla, 0) + eliminadas

    # ── COMPLETITUD ────────────────────────────────────────────────────────
    # Los campos críticos sin valor no tienen reparación posible → descartar.
    requeridas = ["customer_id", "first_name", "last_name", "email", "age", "country", "city"]
    _drop(out[requeridas].notna().all(axis=1), "Completitud · eliminar filas con campos críticos nulos")

    # ── UNICIDAD ───────────────────────────────────────────────────────────
    # El email duplicado se conserva la PRIMERA aparición (la más antigua).
    before = len(out)
    out = out.drop_duplicates(subset=["email"], keep="first")
    stats["Unicidad · eliminar emails duplicados (se conserva el primero)"] = before - len(out)

    # ── VALIDEZ ────────────────────────────────────────────────────────────
    _drop(
        out["email"].astype(str).str.match(EMAIL_REGEX, na=False),
        "Validez · eliminar emails con formato inválido",
    )
    _drop(
        out["age"].between(AGE_RANGE[0], AGE_RANGE[1]),
        "Validez · eliminar edades fuera de rango 18–85",
    )
    registro = pd.to_datetime(out["registration_date"], errors="coerce")
    _drop(registro.notna(), "Validez · eliminar registration_date no parseable")
    out = out.assign(registration_date=registro.dt.strftime("%Y-%m-%d"))

    # ── CONSISTENCIA (aquí SÍ hay reparación determinística) ───────────────
    # 1) ciudad → país: el catálogo dice a qué país pertenece cada ciudad.
    antes_pais = out["country"].copy()
    out["country"] = out["city"].map(CITY_TO_COUNTRY).fillna(out["country"])
    stats["Consistencia · recalcular país a partir de la ciudad"] = int(
        (antes_pais != out["country"]).sum()
    )

    # 2) edad desde birth_date: la fecha de nacimiento es la fuente verídica.
    #    CONVENCIÓN del sistema fuente (ver generador): edad = 2026 − año de
    #    nacimiento. Respetar la convención del origen, no "reinventarla".
    birth = pd.to_datetime(out["birth_date"], errors="coerce")
    ref = pd.Timestamp(REF_DATE)
    edad_calculada = (ref.year - birth.dt.year).astype("float")
    reparadas = int((out["age"] != edad_calculada).sum())
    out["age"] = edad_calculada.astype(int)
    stats["Consistencia · recalcular edad desde birth_date"] = reparadas

    # ── EXACTITUD ──────────────────────────────────────────────────────────
    # Valores fuera de todo rango real (p. ej. 50 millones de USD) no tienen
    # fuente de verdad para corregirse → descartar.
    _drop(
        out["annual_income"].between(*INCOME_RANGE),
        "Exactitud · eliminar ingresos fuera de rango real",
    )
    _drop(
        out["credit_score"].between(*CREDIT_SCORE_RANGE),
        "Exactitud · eliminar credit scores fuera de 300–850",
    )

    # ── OPORTUNIDAD ────────────────────────────────────────────────────────
    # Regla de actualización: si el registro está viejo, se estampa la fecha
    # del proceso (así lo haría el sistema fuente en un upsert real).
    viejos = pd.to_datetime(out["last_update"], errors="coerce") < pd.Timestamp(MIN_LAST_UPDATE)
    stats["Oportunidad · actualizar last_update de registros obsoletos"] = int(viejos.sum())
    out.loc[viejos, "last_update"] = REF_DATE

    return out, stats


# ---------------------------------------------------------------------------
# Órdenes
# ---------------------------------------------------------------------------


def clean_orders(
    df: pd.DataFrame, valid_customer_ids: set[str]
) -> tuple[pd.DataFrame, dict[str, int]]:
    """
    Limpia el dataset de órdenes.

    Parameters
    ----------
    df : pd.DataFrame
        Órdenes crudas.
    valid_customer_ids : set[str]
        IDs de clientes existentes (dataset de clientes ya limpio).

    """
    stats: dict[str, int] = {}
    out = df.copy()

    def _drop(mask: pd.Series, regla: str) -> None:
        nonlocal out
        eliminadas = int((~mask).sum())
        if eliminadas:
            out = out[mask]
        stats[regla] = stats.get(regla, 0) + eliminadas

    # ── REFERENCIAL: normalizar llave y descartar clientes inexistentes ────
    digits = out["customer_id"].astype(str).str.extract(r"^CUST-(\d+)$")[0]
    out["customer_id"] = "CUST-" + digits.str.zfill(6)
    _drop(out["customer_id"].isin(valid_customer_ids), "Referencial · eliminar órdenes de clientes inexistentes")

    # Fechas a datetime (para reparar y validar la jerarquía temporal).
    for col in ("customer_registration_date", "order_date", "shipping_date", "delivery_date"):
        out[f"{col}_dt"] = pd.to_datetime(out[col], errors="coerce")

    # ── CONSISTENCIA: fechas nulas = estado imposible → descartar ──────────
    # (p. ej. DELIVERED sin fecha de envío, SHIPPED sin fecha de orden)
    _drop(
        out["order_date_dt"].notna() & out["shipping_date_dt"].notna(),
        "Consistencia · eliminar órdenes con order_date o shipping_date nulos",
    )

    # ── LÓGICA DE NEGOCIO: dominios imposibles sin forma de inferirse ──────
    _drop(out["quantity"].between(1, 5), "Lógica de negocio · eliminar cantidades fuera de 1–5")
    _drop(
        out["unit_price"].between(0.01, 100_000.0),
        "Lógica de negocio · eliminar precios unitarios no positivos",
    )
    _drop(
        out["discount_percent"].between(0, 100),
        "Lógica de negocio · eliminar descuentos fuera de 0–100 %",
    )

    # ── CONSISTENCIA TEMPORAL ──────────────────────────────────────────────
    # La orden anterior al registro del cliente no es reparable → descartar.
    _drop(
        out["order_date_dt"] >= out["customer_registration_date_dt"],
        "Consistencia · eliminar órdenes anteriores al registro del cliente",
    )
    # Envío antes/igual que la orden → regla: se despacha al día siguiente.
    mask = out["shipping_date_dt"] <= out["order_date_dt"]
    stats["Consistencia · reparar fechas de envío inválidas (+1 día)"] = int(mask.sum())
    out.loc[mask, "shipping_date"] = (out.loc[mask, "order_date_dt"] + pd.Timedelta(days=1)).dt.strftime("%Y-%m-%d")
    out.loc[mask, "shipping_date_dt"] = out.loc[mask, "order_date_dt"] + pd.Timedelta(days=1)
    # Entrega antes/igual que el envío → regla: entrega al día siguiente.
    mask = out["delivery_date_dt"] <= out["shipping_date_dt"]
    stats["Consistencia · reparar fechas de entrega inválidas (+1 día)"] = int(mask.sum())
    out.loc[mask, "delivery_date"] = (out.loc[mask, "shipping_date_dt"] + pd.Timedelta(days=1)).dt.strftime("%Y-%m-%d")
    out.loc[mask, "delivery_date_dt"] = out.loc[mask, "shipping_date_dt"] + pd.Timedelta(days=1)
    # CANCELLED con entrega → la entrega se anula.
    mask = out["order_status"] == "CANCELLED"
    stats["Consistencia · anular entrega de órdenes canceladas"] = int(mask.sum())
    out.loc[mask, ["delivery_date", "delivery_date_dt", "delivery_days"]] = None

    # ── CONSISTENCIA: moneda según país ────────────────────────────────────
    from src.config import CURRENCIES_BY_COUNTRY

    antes = out["customer_currency"].copy()
    out["customer_currency"] = out["customer_country"].map(CURRENCIES_BY_COUNTRY)
    stats["Consistencia · recalcular moneda según país del cliente"] = int(
        (antes != out["customer_currency"]).sum()
    )

    # ── EXACTITUD/NEGOCIO: costo de envío según catálogo ───────────────────
    mask = ~out["shipping_cost"].gt(0)
    stats["Exactitud · reparar costos de envío con tarifa del catálogo"] = int(mask.sum())
    out.loc[mask, "shipping_cost"] = out.loc[mask, "shipping_method"].map(SHIPPING_COST_BY_METHOD)

    # ── RECALCULO FINANCIERO (regla determinística del negocio) ────────────
    # subtotal → descuento → base gravable → IVA → total.
    stats["Consistencia · recalcular cadena financiera completa"] = len(out)
    out["subtotal"] = (out["unit_price"] * out["quantity"]).round(2)
    out["discount_amount"] = (out["subtotal"] * out["discount_percent"] / 100).round(2)
    base_gravable = out["subtotal"] - out["discount_amount"]
    out["tax_amount"] = (base_gravable * out["tax_rate"].fillna(TAX_RATE)).round(2)
    out["total_amount"] = (base_gravable + out["tax_amount"] + out["shipping_cost"]).round(2)

    # ── delivery_days derivado de las fechas ya reparadas ──────────────────
    entregadas = out["delivery_date_dt"].notna()
    out.loc[entregadas, "delivery_days"] = (
        out.loc[entregadas, "delivery_date_dt"] - out.loc[entregadas, "shipping_date_dt"]
    ).dt.days

    # Devolver el esquema original (quitar columnas auxiliares *_dt).
    auxiliares = [c for c in out.columns if c.endswith("_dt")]
    out = out.drop(columns=auxiliares)

    return out, stats
