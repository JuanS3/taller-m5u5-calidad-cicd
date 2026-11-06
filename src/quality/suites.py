"""
Suites de expectativas de Great Expectations (GX 1.x) del taller.

* ``clientes_calidad`` → las **6 dimensiones** de calidad (Unidad 1):
  completitud, unicidad, validez, consistencia, exactitud y oportunidad.
* ``ordenes_negocio``  → reglas de negocio *cross-field* del e-commerce
  (caso avanzado: fechas, cálculos financieros, referencias y estados).

Cada expectativa lleva ``meta`` con:
* ``dimension``  → dimensión de calidad o categoría de la regla.
* ``regla``      → descripción legible que aparece en el reporte HTML.

Convención: ``meta`` es lo que hace trazable un reporte de calidad;
sin ella, un fallo es solo "una expectativa roja" sin contexto de negocio.
"""
from __future__ import annotations

import great_expectations as gx
import great_expectations.expectations as gxe

from src.config import (
    AGE_RANGE,
    AMOUNT_TOLERANCE,
    CREDIT_SCORE_RANGE,
    DATE_REGEX,
    EMAIL_REGEX,
    INCOME_RANGE,
    MIN_LAST_UPDATE,
    ORDER_STATUS,
    PAYMENT_METHODS,
    PRODUCT_CATALOG,
    SHIPPING_METHODS,
    VALID_COUNTRIES,
)
from src.generators.orders_generator import COUNTRIES

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _meta(dimension: str, regla: str) -> dict[str, str]:
    """Construye el diccionario ``meta`` estándar de cada expectativa."""
    return {"dimension": dimension, "regla": regla}


# ---------------------------------------------------------------------------
# Suite 1 · Clientes — las 6 dimensiones de calidad
# ---------------------------------------------------------------------------


def build_customers_suite(context: gx.AbstractDataContext) -> gx.ExpectationSuite:
    """
    Suite de validación para el dataset de clientes.

    Parameters
    ----------
    context : gx.AbstractDataContext
        Contexto GX **activo** (efímero). En GX 1.x la suite debe estar
        adjunta a un contexto antes de añadir expectativas.

    Returns
    -------
    gx.ExpectationSuite
        Suite con expectativas agrupadas por las 6 dimensiones.

    """
    suite = context.suites.add(gx.ExpectationSuite(name="clientes_calidad"))

    # ── COMPLETITUD: los campos críticos no pueden ser nulos ───────────────
    for column, por_que in [
        ("customer_id", "llave primaria del registro"),
        ("first_name", "nombre requerido para comunicaciones"),
        ("last_name", "apellido requerido para comunicaciones"),
        ("email", "canal principal de contacto"),
        ("age", "requerido para segmentación"),
        ("country", "requerido para fiscalización"),
        ("city", "requerido para logística"),
    ]:
        suite.add_expectation(
            gxe.ExpectColumnValuesToNotBeNull(
                column=column,
                meta=_meta("Completitud", f"{column} no puede ser nulo ({por_que})."),
            )
        )

    # ── UNICIDAD: llaves e identificadores sin duplicados ──────────────────
    suite.add_expectation(
        gxe.ExpectColumnValuesToBeUnique(
            column="customer_id",
            meta=_meta("Unicidad", "cada cliente aparece una sola vez (llave primaria)."),
        )
    )
    suite.add_expectation(
        gxe.ExpectColumnValuesToBeUnique(
            column="email",
            meta=_meta("Unicidad", "el email no puede repetirse entre clientes."),
        )
    )

    # ── VALIDEZ: formatos y dominios correctos ─────────────────────────────
    suite.add_expectation(
        gxe.ExpectColumnValuesToMatchRegex(
            column="email",
            regex=EMAIL_REGEX,
            meta=_meta("Validez", "email con formato usuario@dominio.extensión."),
        )
    )
    suite.add_expectation(
        gxe.ExpectColumnValuesToBeBetween(
            column="age",
            min_value=AGE_RANGE[0],
            max_value=AGE_RANGE[1],
            meta=_meta("Validez", f"edad entre {AGE_RANGE[0]} y {AGE_RANGE[1]} años."),
        )
    )
    suite.add_expectation(
        gxe.ExpectColumnValuesToMatchRegex(
            column="registration_date",
            regex=DATE_REGEX,
            meta=_meta("Validez", "registration_date con formato ISO YYYY-MM-DD."),
        )
    )
    suite.add_expectation(
        gxe.ExpectColumnValuesToMatchRegex(
            column="last_update",
            regex=DATE_REGEX,
            meta=_meta("Validez", "last_update con formato ISO YYYY-MM-DD."),
        )
    )

    # ── CONSISTENCIA: coherencia ENTRE campos (columnas de control) ────────
    suite.add_expectation(
        gxe.ExpectColumnValuesToBeInSet(
            column="city_country_ok",
            value_set=[True],
            meta=_meta("Consistencia", "la ciudad pertenece al país declarado."),
        )
    )
    suite.add_expectation(
        gxe.ExpectColumnValuesToBeBetween(
            column="age_diff",
            min_value=-1,
            max_value=1,
            meta=_meta(
                "Consistencia",
                "la edad coincide con birth_date (tolerancia ±1 año por años bisiestos).",
            ),
        )
    )

    # ── EXACTITUD: valores dentro de rangos del mundo real ─────────────────
    suite.add_expectation(
        gxe.ExpectColumnValuesToBeBetween(
            column="annual_income",
            min_value=INCOME_RANGE[0],
            max_value=INCOME_RANGE[1],
            meta=_meta(
                "Exactitud",
                f"ingreso anual entre {INCOME_RANGE[0]:,.0f} y {INCOME_RANGE[1]:,.0f} USD.",
            ),
        )
    )
    suite.add_expectation(
        gxe.ExpectColumnValuesToBeBetween(
            column="credit_score",
            min_value=CREDIT_SCORE_RANGE[0],
            max_value=CREDIT_SCORE_RANGE[1],
            meta=_meta(
                "Exactitud",
                f"credit score entre {CREDIT_SCORE_RANGE[0]} y {CREDIT_SCORE_RANGE[1]}.",
            ),
        )
    )

    # ── OPORTUNIDAD: los datos están al día ────────────────────────────────
    suite.add_expectation(
        gxe.ExpectColumnValuesToBeBetween(
            column="last_update_year",
            min_value=int(MIN_LAST_UPDATE[:4]),
            max_value=int(MIN_LAST_UPDATE[:4]) + 5,
            meta=_meta(
                "Oportunidad",
                f"última actualización no anterior a {MIN_LAST_UPDATE[:4]}.",
            ),
        )
    )

    return suite


# ---------------------------------------------------------------------------
# Suite 2 · Órdenes — reglas de negocio cross-field
# ---------------------------------------------------------------------------


def build_orders_suite(
    context: gx.AbstractDataContext,
    valid_countries: list[str] | None = None,
) -> gx.ExpectationSuite:
    """
    Suite de validación para el dataset de órdenes (caso avanzado).

    Parameters
    ----------
    context : gx.AbstractDataContext
        Contexto GX activo (efímero).
    valid_countries : list[str] | None
        Países admitidos. Si es ``None`` se deduce de los generadores.

    """
    countries = valid_countries or sorted(set(VALID_COUNTRIES) | set(COUNTRIES))
    categories = sorted(PRODUCT_CATALOG.keys())
    methods_envio = sorted(SHIPPING_METHODS.keys())
    pagos = sorted(PAYMENT_METHODS)
    estados = sorted(ORDER_STATUS)

    suite = context.suites.add(gx.ExpectationSuite(name="ordenes_negocio"))

    # ── ESTRUCTURA Y VALIDEZ ───────────────────────────────────────────────
    suite.add_expectation(
        gxe.ExpectColumnValuesToMatchRegex(
            column="order_id",
            regex=r"^ORD-\d{7}$",
            meta=_meta("Validez", "order_id con formato ORD-XXXXXXX."),
        )
    )
    suite.add_expectation(
        gxe.ExpectColumnValuesToBeUnique(
            column="order_id",
            meta=_meta("Unicidad", "cada orden aparece una sola vez (llave primaria)."),
        )
    )
    suite.add_expectation(
        gxe.ExpectColumnValuesToBeInSet(
            column="product_category",
            value_set=categories,
            meta=_meta("Validez", "categoría de producto del catálogo."),
        )
    )
    suite.add_expectation(
        gxe.ExpectColumnValuesToBeInSet(
            column="shipping_method",
            value_set=methods_envio,
            meta=_meta("Validez", "método de envío del catálogo."),
        )
    )
    suite.add_expectation(
        gxe.ExpectColumnValuesToBeInSet(
            column="payment_method",
            value_set=pagos,
            meta=_meta("Validez", "medio de pago del catálogo."),
        )
    )
    suite.add_expectation(
        gxe.ExpectColumnValuesToBeInSet(
            column="order_status",
            value_set=estados,
            meta=_meta("Validez", "estado de orden del catálogo."),
        )
    )
    suite.add_expectation(
        gxe.ExpectColumnValuesToBeInSet(
            column="customer_country",
            value_set=countries,
            meta=_meta("Validez", "país del cliente dentro de los países operados."),
        )
    )

    # ── REFERENCIAL (integridad orden → cliente) ───────────────────────────
    suite.add_expectation(
        gxe.ExpectColumnValuesToBeInSet(
            column="customer_ok",
            value_set=[True],
            meta=_meta("Referencial", "customer_id existe en el dataset de clientes."),
        )
    )

    # ── LÓGICA DE NEGOCIO: dominios de negocio por campo ───────────────────
    suite.add_expectation(
        gxe.ExpectColumnValuesToBeBetween(
            column="quantity",
            min_value=1,
            max_value=5,
            meta=_meta("Lógica de negocio", "cantidad entre 1 y 5 unidades."),
        )
    )
    suite.add_expectation(
        gxe.ExpectColumnValuesToBeBetween(
            column="unit_price",
            min_value=0.01,
            max_value=100_000.0,
            meta=_meta("Lógica de negocio", "precio unitario positivo."),
        )
    )
    suite.add_expectation(
        gxe.ExpectColumnValuesToBeBetween(
            column="discount_percent",
            min_value=0,
            max_value=100,
            meta=_meta("Lógica de negocio", "descuento entre 0 % y 100 %."),
        )
    )
    suite.add_expectation(
        gxe.ExpectColumnValuesToBeBetween(
            column="delivery_days",
            min_value=1,
            max_value=30,
            meta=_meta("Lógica de negocio", "entrega entre 1 y 30 días después del envío."),
        )
    )
    suite.add_expectation(
        gxe.ExpectColumnPairValuesAToBeGreaterThanB(
            column_A="subtotal",
            column_B="discount_amount",
            or_equal=True,
            meta=_meta("Lógica de negocio", "el descuento no supera el subtotal."),
        )
    )

    # ── CONSISTENCIA ENTRE CAMPOS (columnas de control) ────────────────────
    suite.add_expectation(
        gxe.ExpectColumnValuesToBeInSet(
            column="currency_ok",
            value_set=[True],
            meta=_meta("Consistencia", "la moneda corresponde al país del cliente."),
        )
    )
    suite.add_expectation(
        gxe.ExpectColumnValuesToBeBetween(
            column="total_diff",
            min_value=0,
            max_value=AMOUNT_TOLERANCE,
            meta=_meta(
                "Consistencia",
                "total = subtotal − descuento + IVA + envío (tolerancia centavos).",
            ),
        )
    )
    suite.add_expectation(
        gxe.ExpectColumnValuesToBeInSet(
            column="order_after_reg",
            value_set=[True],
            meta=_meta("Consistencia", "la orden es posterior al registro del cliente."),
        )
    )
    suite.add_expectation(
        gxe.ExpectColumnValuesToBeInSet(
            column="ship_after_order",
            value_set=[True],
            meta=_meta("Consistencia", "el envío es posterior a la orden."),
        )
    )
    suite.add_expectation(
        gxe.ExpectColumnValuesToBeInSet(
            column="deliver_after_ship",
            value_set=[True],
            # Las órdenes CANCELLED no tienen entrega (columna nula a propósito)
            # y quedan excluidas de esta regla temporal.
            row_condition='order_status != "CANCELLED"',
            condition_parser="pandas",
            meta=_meta("Consistencia", "la entrega es posterior al envío (no aplica a CANCELLED)."),
        )
    )
    suite.add_expectation(
        gxe.ExpectColumnValuesToNotBeNull(
            column="shipping_date",
            row_condition='order_status == "DELIVERED"',
            condition_parser="pandas",
            meta=_meta("Consistencia", "una orden DELIVERED debe tener fecha de envío."),
        )
    )
    suite.add_expectation(
        gxe.ExpectColumnValuesToBeNull(
            column="delivery_date",
            row_condition='order_status == "CANCELLED"',
            condition_parser="pandas",
            meta=_meta("Consistencia", "una orden CANCELLED no puede tener entrega."),
        )
    )

    return suite
