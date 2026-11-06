"""
Ejecutor de validaciones Great Expectations + puerta de calidad.

Flujo de cada validación:
1. Contexto GX **efímero** (sin archivos de configuración: ideal para un
   pipeline de taller y para CI, donde el repo queda limpio).
2. Registrar suite → datasource pandas en memoria → lote completo.
3. Ejecutar la ValidationDefinition con ``result_format=COMPLETE``.
4. Traducir el resultado a un resumen propio (``ValidationSummary``) que el
   pipeline sabe convertir en reportes HTML/JSON y en decisión de gate.

La "puerta de calidad" (quality gate) es la aplicación más directa de
CI/CD a datos: si el porcentaje de expectativas exitosas queda por debajo
del umbral del ambiente, el pipeline termina con código de salida 1 y el
workflow de GitHub Actions se pone en rojo.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

import great_expectations as gx
import pandas as pd
from rich.console import Console
from rich.table import Table

from src.utils.logger import setup_logger

logger = setup_logger(__name__)
console = Console()

# Dimensiones en el orden pedagógico de la Unidad 1 del Módulo 5.
DIMENSION_ORDER: list[str] = [
    "Completitud",
    "Unicidad",
    "Validez",
    "Consistencia",
    "Referencial",
    "Lógica de negocio",
    "Exactitud",
    "Oportunidad",
    "General",
]


@dataclass
class CheckResult:
    """Resultado de UNA expectativa."""

    expectativa: str
    dimension: str
    regla: str
    exitosa: bool
    fallidos: int | None = None
    porcentaje_fallidos: float | None = None
    ejemplos: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class ValidationSummary:
    """Resumen ejecutable de una validación completa."""

    dataset: str
    filas: int
    total: int
    exitosas: int
    fallidas: int
    porcentaje_exito: float
    success: bool
    checks: list[CheckResult] = field(default_factory=list)


def create_context() -> gx.AbstractDataContext:
    """Crea un contexto GX efímero (sin archivos de configuración en el repo)."""
    context = gx.get_context(mode="ephemeral")
    _disable_progress_bars(context)
    return context


def _clean_example(value: Any) -> Any:
    """Convierte valores numpy/pandas a tipos nativos para JSON."""
    if isinstance(value, dict):
        return {k: _clean_example(v) for k, v in value.items()}
    if pd.isna(value):
        return None
    if hasattr(value, "item"):
        return value.item()
    return value


def _disable_progress_bars(context: gx.AbstractDataContext) -> None:
    """Silencia las barras 'Calculating Metrics' de GX (salida más limpia)."""
    try:
        from great_expectations.data_context.types.base import ProgressBarsConfig

        context.variables.progress_bars = ProgressBarsConfig(globally=False)
    except Exception:  # pragma: no cover - depende de la versión de GX
        pass


def validate_dataframe(
    context: gx.AbstractDataContext,
    suite: gx.ExpectationSuite,
    df: pd.DataFrame,
    dataset_label: str,
    index_column: str,
) -> ValidationSummary:
    """
    Ejecuta una suite GX contra un DataFrame en memoria.

    Parameters
    ----------
    context : gx.AbstractDataContext
        Contexto GX efímero ya activo (ver ``create_context``).
    suite : gx.ExpectationSuite
        Suite de expectativas (ya adjunta al contexto).
    df : pd.DataFrame
        Datos a validar (ya enriquecidos con columnas de control).
    dataset_label : str
        Nombre legible del dataset (para el resumen y reportes).
    index_column : str
        Columna usada para identificar filas fallidas en los reportes
        (``customer_id`` u ``order_id``).

    """
    data_source = context.data_sources.add_pandas(name="taller_m5u5")
    asset = data_source.add_dataframe_asset(name=dataset_label.lower().replace(" ", "_"))
    batch_definition = asset.add_batch_definition_whole_dataframe("lote_completo")

    validation = context.validation_definitions.add(
        gx.ValidationDefinition(
            data=batch_definition,
            suite=suite,
            name=f"vd_{dataset_label.lower().replace(' ', '_')}",
        )
    )

    result = validation.run(
        batch_parameters={"dataframe": df},
        result_format={
            "result_format": "COMPLETE",
            "unexpected_index_column_names": [index_column],
            "include_unexpected_rows": True,
        },
    )

    checks: list[CheckResult] = []
    for r in result.results:
        config = r.expectation_config
        res = r.result or {}
        meta = config.meta or {}

        ejemplos: list[dict[str, Any]] = []
        for item in (res.get("unexpected_index_list") or [])[:5]:
            if isinstance(item, dict):
                ejemplos.append({k: _clean_example(v) for k, v in item.items()})
            else:
                ejemplos.append({"valor": _clean_example(item)})

        checks.append(
            CheckResult(
                expectativa=config.type,
                dimension=meta.get("dimension", "General"),
                regla=meta.get("regla", ""),
                exitosa=bool(r.success),
                fallidos=res.get("unexpected_count"),
                porcentaje_fallidos=(
                    round(float(res["unexpected_percent"]), 2)
                    if res.get("unexpected_percent") is not None
                    else None
                ),
                ejemplos=ejemplos,
            )
        )

    exitosas = sum(1 for c in checks if c.exitosa)
    total = len(checks)
    porcentaje = round(exitosas / total * 100, 2) if total else 0.0

    return ValidationSummary(
        dataset=dataset_label,
        filas=int(len(df)),
        total=total,
        exitosas=exitosas,
        fallidas=total - exitosas,
        porcentaje_exito=porcentaje,
        success=porcentaje >= 100.0,
        checks=checks,
    )


# ---------------------------------------------------------------------------
# Impresión en consola (Rich)
# ---------------------------------------------------------------------------


def print_summary(summary: ValidationSummary) -> None:
    """Imprime el detalle de una validación en consola (agrupado por dimensión)."""
    color = "green" if summary.success else "red"
    console.print(
        f"\n[bold {color}]📋 Validación: {summary.dataset}[/] — "
        f"{summary.filas} filas · {summary.exitosas}/{summary.total} expectativas OK "
        f"({summary.porcentaje_exito}%)",
    )

    table = Table(show_header=True, header_style="bold", pad_edge=False)
    table.add_column("Dimensión", style="cyan", max_width=18)
    table.add_column("Regla", max_width=55)
    table.add_column("Estado", justify="center", width=9)
    table.add_column("Fallidos", justify="right", width=9)

    for check in sorted(summary.checks, key=lambda c: DIMENSION_ORDER.index(c.dimension)):
        estado = "[green]✔ OK[/]" if check.exitosa else "[red]✘ FALLO[/]"
        regla = check.regla or check.expectativa
        if not check.exitosa and check.ejemplos:
            primero = check.ejemplos[0]
            muestra = ", ".join(f"{k}={v}" for k, v in primero.items())
            regla = f"{regla}\n[dim]ej: {muestra}[/]"
        table.add_row(
            check.dimension,
            regla,
            estado,
            str(check.fallidos if check.fallidos is not None else "-"),
        )

    console.print(table)


def apply_quality_gate(summary: ValidationSummary, min_success_pct: float) -> bool:
    """
    Aplica la puerta de calidad del ambiente.

    Parameters
    ----------
    summary : ValidationSummary
        Resultado de la validación del dataset limpio.
    min_success_pct : float
        Umbral mínimo de expectativas exitosas (95 en DEV, 100 en PROD).

    Returns
    -------
    bool
        ``True`` si el dataset puede promocionarse.

    """
    aprobado = summary.porcentaje_exito >= min_success_pct
    if aprobado:
        console.print(
            f"  [bold green]🚪 QUALITY GATE: PASA[/] "
            f"({summary.porcentaje_exito}% ≥ umbral {min_success_pct}%)"
        )
    else:
        console.print(
            f"  [bold red]⛔ QUALITY GATE: BLOQUEADO[/] "
            f"({summary.porcentaje_exito}% < umbral {min_success_pct}%)"
        )
    return aprobado


def summary_to_dict(summary: ValidationSummary) -> dict[str, Any]:
    """Serializa un resumen a diccionario apto para JSON."""
    data = asdict(summary)
    return data
