"""
Pipeline del taller: EXTRAE → VALIDA (raw) → LIMPIA → VALIDA (clean) → PUBLICA.

Un pipeline *production-ready* mínimo pero completo:

1. **Extrae**     : genera los datasets sintéticos con errores controlados
                    (semilla fija → 100 % reproducible) y los guarda en ``data/raw``.
2. **Valida**     : Great Expectations audita los datos CRUDOS contra las 6
                    dimensiones / reglas de negocio. Aquí se ESPERAN fallos:
                    es la evidencia de por qué la calidad importa.
3. **Limpia**     : pandas repara lo reparable y descarta lo demás.
4. **Revalida**   : los datos LIMPIOS pasan por la misma suite.
5. **Quality gate**: si el % de éxito queda bajo el umbral del ambiente
                    (95 % en DEV, 100 % en PROD), el proceso termina con
                    código de salida 1 → GitHub Actions pone el job en rojo.
6. **Publica**    : los datos certificados se guardan en ``data/clean``
                    (CSV + Parquet) y los reportes en ``data/reportes``.

Uso::

    python -m src.pipeline.run_pipeline                 # DEV  (umbral 95 %)
    python -m src.pipeline.run_pipeline --min-success 100   # PROD (umbral 100 %)
    python -m src.pipeline.run_pipeline --skip-generate     # reusa data/raw

"""
from __future__ import annotations

import argparse
import sys
import time

import pandas as pd
from rich import box
from rich.console import Console
from rich.rule import Rule
from rich.table import Table

from src.cleaning.cleaner import clean_customers, clean_orders
from src.config import (
    CUSTOMERS_CLEAN,
    CUSTOMERS_CLEAN_PARQUET,
    CUSTOMERS_RAW,
    ORDERS_CLEAN,
    ORDERS_CLEAN_PARQUET,
    ORDERS_RAW,
    REPORT_CUSTOMERS_CLEAN,
    REPORT_CUSTOMERS_RAW,
    REPORT_ORDERS_CLEAN,
    REPORT_ORDERS_RAW,
    ensure_dirs,
)
from src.quality.prepare import enrich_customers, enrich_orders
from src.quality.reports import write_html_report, write_json_report
from src.quality.runner import (
    ValidationSummary,
    apply_quality_gate,
    create_context,
    print_summary,
    validate_dataframe,
)
from src.quality.suites import build_customers_suite, build_orders_suite

console = Console()


# ---------------------------------------------------------------------------
# Pasos del pipeline
# ---------------------------------------------------------------------------
def step_extraccion(args: argparse.Namespace) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Genera (o recarga) los datasets crudos."""
    from src.generators.data_generator import DataGenerator
    from src.generators.orders_generator import OrdersGenerator

    if args.skip_generate:
        console.print("[yellow]↷ --skip-generate: reutilizando archivos existentes en data/raw[/]")
        clientes = pd.read_csv(CUSTOMERS_RAW)
        ordenes = pd.read_csv(ORDERS_RAW)
        return clientes, ordenes

    console.print(f"  Generando {args.rows} clientes (semilla {args.seed}, {int(args.error_rate * 100)} % de errores)...")
    clientes = DataGenerator(seed=args.seed, error_rate=args.error_rate).generate(args.rows)
    clientes.to_csv(CUSTOMERS_RAW, index=False)

    console.print(
        f"  Generando {args.orders} órdenes (semilla {args.seed}, {int(args.orders_error_rate * 100)} % de errores)..."
    )
    ordenes = OrdersGenerator(seed=args.seed, error_rate=args.orders_error_rate).generate(args.orders)
    ordenes.to_csv(ORDERS_RAW, index=False)

    return clientes, ordenes


def _validar(
    df: pd.DataFrame,
    dataset_label: str,
    index_column: str,
    reporte_base,
    es_orden: bool,
    df_referencia: pd.DataFrame,
) -> ValidationSummary:
    """Enriquece, valida y genera reportes para un dataset.

    Parameters
    ----------
    df_referencia : pd.DataFrame
        Dataset de clientes contra el que se valida la llave referencial de
        las órdenes (raw vs. raw, clean vs. clean).
    """
    context = create_context()  # contexto GX efímero, uno por validación
    if es_orden:
        ids_validos = set(df_referencia["customer_id"])
        df_enriched = enrich_orders(df, ids_validos)
        suite = build_orders_suite(context)
    else:
        df_enriched = enrich_customers(df)
        suite = build_customers_suite(context)

    summary = validate_dataframe(context, suite, df_enriched, dataset_label, index_column)
    print_summary(summary)
    write_html_report(summary, reporte_base.with_suffix(".html"))
    write_json_report(summary, reporte_base.with_suffix(".json"))
    console.print(f"  [dim]Reportes → {reporte_base.with_suffix('.html').name} / {reporte_base.with_suffix('.json').name}[/]")
    return summary


def step_publicacion(clientes: pd.DataFrame, ordenes: pd.DataFrame) -> None:
    """Guarda los datos certificados en CSV + Parquet."""
    clientes.to_csv(CUSTOMERS_CLEAN, index=False)
    clientes.to_parquet(CUSTOMERS_CLEAN_PARQUET, index=False)
    ordenes.to_csv(ORDERS_CLEAN, index=False)
    ordenes.to_parquet(ORDERS_CLEAN_PARQUET, index=False)
    console.print(f"  Clientes certificados → [cyan]data/clean/customers_clean.csv[/] (+ .parquet)")
    console.print(f"  Órdenes certificadas  → [cyan]data/clean/orders_clean.csv[/] (+ .parquet)")


# ---------------------------------------------------------------------------
# Orquestación
# ---------------------------------------------------------------------------
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Pipeline de calidad de datos del taller (Módulo 5 · Unidad 5)",
    )
    parser.add_argument("--rows", type=int, default=1000, help="Clientes a generar")
    parser.add_argument("--orders", type=int, default=2000, help="Órdenes a generar")
    parser.add_argument("--seed", type=int, default=42, help="Semilla de reproducibilidad")
    parser.add_argument("--error-rate", type=float, default=0.15, help="Tasa de errores en clientes")
    parser.add_argument("--orders-error-rate", type=float, default=0.20, help="Tasa de errores en órdenes")
    parser.add_argument(
        "--min-success",
        type=float,
        default=95.0,
        help="Umbral del quality gate en %% (95=DEV, 100=PROD)",
    )
    parser.add_argument("--skip-generate", action="store_true", help="Reusa los CSV de data/raw")
    args = parser.parse_args(argv)

    ensure_dirs()
    inicio = time.time()

    console.print(Rule("[bold cyan]🚀 PIPELINE DE CALIDAD DE DATOS — Taller M5·U5[/]"))
    console.print(
        f"  Ambiente: [bold]{'PRODUCCIÓN' if args.min_success >= 100 else 'DESARROLLO'}[/]"
        f" · quality gate: [bold]{args.min_success} %[/]"
    )

    # ── 1. EXTRACCIÓN ──────────────────────────────────────────────────────
    console.print(Rule("[bold]1️⃣  EXTRACCIÓN — datos sintéticos con errores controlados[/]"))
    clientes_raw, ordenes_raw = step_extraccion(args)

    # ── 2. VALIDACIÓN DE DATOS CRUDOS (informativa) ────────────────────────
    console.print(Rule("[bold]2️⃣  VALIDACIÓN RAW — ¿qué problema tienen los datos de entrada?[/]"))
    resumen_clientes_raw = _validar(
        clientes_raw, "Clientes · RAW", "customer_id", REPORT_CUSTOMERS_RAW, es_orden=False, df_referencia=clientes_raw
    )
    resumen_ordenes_raw = _validar(
        ordenes_raw, "Órdenes · RAW", "order_id", REPORT_ORDERS_RAW, es_orden=True, df_referencia=clientes_raw
    )
    console.print(
        "  [yellow]ℹ Las fallas en RAW son EXPECTADAS: son la evidencia del problema de calidad "
        "que el pipeline debe resolver. No bloquean la ejecución.[/]"
    )

    # ── 3. LIMPIEZA ────────────────────────────────────────────────────────
    console.print(Rule("[bold]3️⃣  LIMPIEZA — reparar lo reparable, descartar lo demás[/]"))
    clientes_clean, stats_clientes = clean_customers(clientes_raw)
    ordenes_clean, stats_ordenes = clean_orders(
        ordenes_raw, valid_customer_ids=set(clientes_clean["customer_id"])
    )
    tabla_stats = Table(box=box.SIMPLE, show_header=True, header_style="bold")
    tabla_stats.add_column("Regla aplicada")
    tabla_stats.add_column("Filas", justify="right")
    for regla, n in {**stats_clientes, **stats_ordenes}.items():
        tabla_stats.add_row(regla, str(n))
    console.print(tabla_stats)
    console.print(
        f"  Clientes: {len(clientes_raw)} → [green]{len(clientes_clean)}[/] filas · "
        f"Órdenes: {len(ordenes_raw)} → [green]{len(ordenes_clean)}[/] filas"
    )

    # ── 4. REVALIDACIÓN + QUALITY GATE ─────────────────────────────────────
    console.print(Rule("[bold]4️⃣  VALIDACIÓN CLEAN + QUALITY GATE[/]"))
    resumen_clientes_clean = _validar(
        clientes_clean, "Clientes · CLEAN", "customer_id", REPORT_CUSTOMERS_CLEAN, es_orden=False, df_referencia=clientes_clean
    )
    gate_clientes = apply_quality_gate(resumen_clientes_clean, args.min_success)

    resumen_ordenes_clean = _validar(
        ordenes_clean, "Órdenes · CLEAN", "order_id", REPORT_ORDERS_CLEAN, es_orden=True, df_referencia=clientes_clean
    )
    gate_ordenes = apply_quality_gate(resumen_ordenes_clean, args.min_success)

    # ── 5. PUBLICACIÓN ─────────────────────────────────────────────────────
    if gate_clientes and gate_ordenes:
        console.print(Rule("[bold]5️⃣  PUBLICACIÓN — datos certificados[/]"))
        step_publicacion(clientes_clean, ordenes_clean)
    else:
        console.print(Rule("[bold red]5️⃣  PUBLICACIÓN CANCELADA — el quality gate bloqueó la promoción[/]"))

    # ── RESUMEN FINAL ──────────────────────────────────────────────────────
    duracion = time.time() - inicio
    resumen = Table(title="Resumen del pipeline", box=box.ROUNDED, show_header=True, header_style="bold")
    resumen.add_column("Dataset")
    resumen.add_column("Filas", justify="right")
    resumen.add_column("Expectativas OK", justify="right")
    resumen.add_column("% éxito", justify="right")
    resumen.add_column("Gate", justify="center")
    for s, gate in [
        (resumen_clientes_raw, None),
        (resumen_ordenes_raw, None),
        (resumen_clientes_clean, gate_clientes),
        (resumen_ordenes_clean, gate_ordenes),
    ]:
        raw = gate is None
        resumen.add_row(
            s.dataset,
            f"{s.filas:,}",
            f"{s.exitosas}/{s.total}",
            f"{s.porcentaje_exito}%",
            "[dim]informativo[/]" if raw else ("[green]PASA[/]" if gate else "[red]BLOQUEA[/]"),
        )
    console.print(resumen)
    console.print(f"  ⏱ Duración total: {duracion:.1f}s")

    exito = gate_clientes and gate_ordenes
    if exito:
        console.print("[bold green]✅ Pipeline exitoso: datos certificados y listos para consumo.[/]")
    else:
        console.print("[bold red]❌ Pipeline falló: el quality gate impidió la promoción (código de salida 1).[/]")
    return 0 if exito else 1


if __name__ == "__main__":
    sys.exit(main())
