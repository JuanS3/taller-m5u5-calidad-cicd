"""
Generación de reportes de calidad (HTML autocontenido + JSON).

Práctica DataOps (Unidad 3): cada ejecución deja **evidencia auditable**.
Los reportes se publican como artefactos en GitHub Actions y permiten
trazar qué reglas fallaron, con qué datos de ejemplo y en qué ambiente.
"""
from __future__ import annotations

import datetime as dt
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from src.quality.runner import ValidationSummary

_CSS = """
  :root { --ok:#16a34a; --bad:#dc2626; --ink:#0f172a; --muted:#64748b; }
  * { box-sizing: border-box; }
  body { font-family: -apple-system, 'Segoe UI', Roboto, Arial, sans-serif;
         color: var(--ink); margin: 0; background: #f1f5f9; }
  .wrap { max-width: 960px; margin: 24px auto; padding: 0 16px; }
  .card { background: #fff; border-radius: 12px; padding: 24px;
          box-shadow: 0 1px 3px rgba(0,0,0,.08); margin-bottom: 16px; }
  h1 { font-size: 22px; margin: 0 0 4px; }
  .meta { color: var(--muted); font-size: 13px; }
  .badge { display: inline-block; padding: 4px 14px; border-radius: 999px;
           color: #fff; font-weight: 700; font-size: 14px; }
  .badge.ok { background: var(--ok); }  .badge.bad { background: var(--bad); }
  .kpis { display: flex; gap: 12px; flex-wrap: wrap; margin-top: 14px; }
  .kpi { flex: 1 1 120px; background: #f8fafc; border: 1px solid #e2e8f0;
         border-radius: 10px; padding: 10px 14px; }
  .kpi b { display: block; font-size: 20px; }
  .kpi span { color: var(--muted); font-size: 12px; }
  table { width: 100%; border-collapse: collapse; font-size: 13.5px; }
  th { text-align: left; background: #f8fafc; color: var(--muted);
       padding: 8px 10px; border-bottom: 2px solid #e2e8f0; }
  td { padding: 8px 10px; border-bottom: 1px solid #eef2f7; vertical-align: top; }
  tr.dim td { background: #eff6ff; font-weight: 700; color: #1d4ed8; }
  .ok { color: var(--ok); font-weight: 700; }
  .bad { color: var(--bad); font-weight: 700; }
  .ej { color: var(--muted); font-size: 12px; margin-top: 2px; }
  footer { color: var(--muted); font-size: 12px; text-align: center; margin: 18px 0; }
"""

_DIMENSION_HEADER = {
    "Completitud": "COMPLETITUD — ¿están los campos requeridos?",
    "Unicidad": "UNICIDAD — ¿hay duplicados?",
    "Validez": "VALIDEZ — ¿formatos y dominios correctos?",
    "Consistencia": "CONSISTENCIA — ¿coherencia entre campos?",
    "Referencial": "REFERENCIAL — ¿las relaciones existen?",
    "Lógica de negocio": "LÓGICA DE NEGOCIO — ¿reglas del dominio?",
    "Exactitud": "EXACTITUD — ¿valores realistas?",
    "Oportunidad": "OPORTUNIDAD — ¿datos al día?",
    "General": "GENERAL",
}


def write_json_report(summary: ValidationSummary, path: Path) -> Path:
    """Escribe el resumen de validación como JSON (evidencia máquina)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    payload: dict[str, Any] = {
        "generado": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        **asdict(summary),
    }
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    return path


def write_html_report(summary: ValidationSummary, path: Path) -> Path:
    """Escribe un reporte HTML autocontenido (una sola página, sin JS)."""
    path.parent.mkdir(parents=True, exist_ok=True)

    estado = (
        '<span class="badge ok">✔ APROBADO (100%)</span>'
        if summary.success
        else f'<span class="badge bad">✘ RECHAZADO ({summary.porcentaje_exito}%)</span>'
    )

    filas_html: list[str] = []
    dimension_actual: str | None = None
    orden = {d: i for i, d in enumerate(
        ["Completitud", "Unicidad", "Validez", "Consistencia", "Referencial",
         "Lógica de negocio", "Exactitud", "Oportunidad", "General"]
    )}
    for check in sorted(summary.checks, key=lambda c: orden.get(c.dimension, 99)):
        if check.dimension != dimension_actual:
            dimension_actual = check.dimension
            filas_html.append(
                f'<tr class="dim"><td colspan="4">'
                f'{_DIMENSION_HEADER.get(check.dimension, check.dimension)}</td></tr>'
            )
        estado_celda = (
            '<span class="ok">✔ OK</span>'
            if check.exitosa
            else '<span class="bad">✘ FALLO</span>'
        )
        ejemplos = ""
        if not check.exitosa and check.ejemplos:
            textos = [
                ", ".join(f"{k}={v}" for k, v in ej.items()) for ej in check.ejemplos
            ]
            ejemplos = f'<div class="ej">ej: {" · ".join(textos)}</div>'
        fallidos = "-" if check.fallidos is None else f"{check.fallidos}"
        pct = (
            ""
            if check.porcentaje_fallidos is None or check.exitosa
            else f' ({check.porcentaje_fallidos}%)'
        )
        filas_html.append(
            "<tr>"
            f"<td>{check.regla or check.expectativa}{ejemplos}</td>"
            f"<td>{estado_celda}</td>"
            f"<td style='text-align:right'>{fallidos}{pct}</td>"
            "</tr>"
        )

    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<title>Reporte de calidad · {summary.dataset}</title>
<style>{_CSS}</style>
</head>
<body>
<div class="wrap">
  <div class="card">
    <h1>📋 Reporte de calidad de datos · {summary.dataset}</h1>
    <div class="meta">
      Generado: {dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC ·
      Suite Great Expectations 1.x · Taller Módulo 5 · Unidad 5
    </div>
    <div style="margin-top:10px">{estado}</div>
    <div class="kpis">
      <div class="kpi"><b>{summary.filas:,}</b><span>filas evaluadas</span></div>
      <div class="kpi"><b>{summary.total}</b><span>expectativas</span></div>
      <div class="kpi"><b>{summary.exitosas}</b><span>exitosas</span></div>
      <div class="kpi"><b>{summary.fallidas}</b><span>fallidas</span></div>
      <div class="kpi"><b>{summary.porcentaje_exito}%</b><span>% de éxito</span></div>
    </div>
  </div>
  <div class="card">
    <table>
      <tr><th style="width:70%">Regla de calidad</th><th>Estado</th>
          <th style="text-align:right">Filas fallidas</th></tr>
      {"".join(filas_html)}
    </table>
  </div>
  <footer>Taller Módulo 5 · Unidad 5 — CI/CD para pipelines de datos ·
  reporte generado automáticamente por el pipeline</footer>
</div>
</body>
</html>"""

    path.write_text(html, encoding="utf-8")
    return path
