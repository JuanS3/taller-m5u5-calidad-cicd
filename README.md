# 🚀 Taller M5·U5 — Calidad de Datos con Great Expectations y CI/CD en GitHub

> **Programa PAE Data Engineer · Módulo 5: Calidad, DataOps y Producción Production-Ready**
> **Unidad 5: CI/CD para pipelines de datos** (integra también las Unidades 1, 2 y 3)
>
> Pipeline *production-ready* mínimo: **extraer → validar (GX) → limpiar → revalidar → quality gate → publicar**, con integración y despliegue continuos en GitHub Actions.

![CI · Calidad de datos (DEV)](https://github.com/TU-USUARIO/TU-REPO/actions/workflows/01-ci-dev.yml/badge.svg)
![CD · Promoción a producción](https://github.com/TU-USUARIO/TU-REPO/actions/workflows/02-cd-produccion.yml/badge.svg)

> ℹ️ Tras subir el repo a GitHub, reemplaza `TU-USUARIO/TU-REPO` en las líneas de badges por tu usuario y nombre de repositorio para que los badges funcionen.

---

## 1. Qué van a construir los participantes

Un pipeline de datos con **puerta de calidad (quality gate)** que bloquea la promoción
de datos defectuosos a producción, automatizado de punta a punta con GitHub Actions:

```
                     ┌──────────────────────────────────────────────────┐
                     │                src/pipeline/run_pipeline.py      │
                     └──────────────────────────────────────────────────┘

  1️⃣ EXTRAE          2️⃣ VALIDA RAW        3️⃣ LIMPIA          4️⃣ VALIDA CLEAN + GATE     5️⃣ PUBLICA
┌───────────────┐   ┌───────────────┐   ┌──────────────┐   ┌──────────────────────┐   ┌─────────────┐
│ generadores   │   │ Great         │   │ pandas:      │   │ Great Expectations   │   │ data/clean/ │
│ sintéticos    │──▶│ Expectations  │──▶│ reparar o    │──▶│ + QUALITY GATE       │──▶│ CSV+Parquet │
│ (errores      │   │ (se ESPERAN   │   │ descartar    │   │ DEV 95% / PROD 100%  │   │ + reportes  │
│ controlados)  │   │  fallos aquí) │   │              │   │ ✋ bloquea si no pasa │   │ HTML/JSON   │
└───────────────┘   └───────────────┘   └──────────────┘   └──────────────────────┘   └─────────────┘
        ▲                                                                ▲
        └──────────────── GitHub Actions (CI/CD) ────────────────────────┘
          • push / pull_request  → CI DEV (umbral 95 %)  → reportes como artefacto
          • tag v1.0.0           → CD PROD (umbral 100 %) → Release con datos certificados
```

**Los datos son deliberadamente "sucios"**: los generadores adjuntos inyectan violaciones
controladas a las 6 dimensiones de calidad (con semilla fija → resultados 100 % reproducibles).
La sesión gira alrededor de una narrativa real: *los datos crudos fallan la auditoría →
el pipeline limpia y revalida → solo si la calidad alcanza el umbral del ambiente se promocionan*.

### Resultados de referencia (semilla 42, valores reales de una ejecución)

| Dataset | Filas | Expectativas OK | % éxito | Gate |
|---|---|---|---|---|
| Clientes · RAW | 1,000 | 5/18 | 27.78 % | informativo |
| Órdenes · RAW | 2,000 | 7/20 | 35.0 % | informativo |
| Clientes · CLEAN | 902 | 18/18 | **100 %** | ✅ PASA |
| Órdenes · CLEAN | 1,639 | 20/20 | **100 %** | ✅ PASA |

### Cobertura del Módulo 5

| Parte del taller | Unidad del Módulo 5 |
|---|---|
| Suite de clientes con las 6 dimensiones | U1 · Calidad de datos en pipelines modernos |
| Suites Great Expectations + reportes | U2 · Herramientas de calidad con Great Expectations |
| Pipeline automatizado, evidencia auditable, umbral por ambiente | U3 · Bases de DataOps |
| CI en push/PR, CD con tag → release, quality gates | **U5 · CI/CD para pipelines de datos** |
| *(U4 · Terraform queda fuera del alcance de este taller simple)* | — |

---

## 2. Agenda (2 horas)

| ⏱ | Parte | Actividad |
|---|---|---|
| 15 min | **Parte 0** | Preparación del entorno (clonar, venv, dependencias) |
| 20 min | **Parte 1** | Primera ejecución del pipeline y lectura del reporte de calidad |
| 25 min | **Parte 2** | Anatomía de una validación GX: dimensiones, expectativas, meta |
| 30 min | **Parte 3** | Ejercicios: extender la suite, romper y reparar el quality gate |
| 25 min | **Parte 4** | CI/CD en GitHub: push, Actions, pull request, tag → release |
| 5 min | **Cierre** | Reflexión y discusión |

---

## 3. Requisitos

- **Python 3.10+** (probado con 3.12) — [python.org](https://www.python.org/downloads/)
- **Git** y una cuenta de **GitHub**
- Editor de código (VS Code recomendado)
- *Opcional*: GNU Make para usar los atajos del `Makefile` (en Windows no es necesario)

---

## 4. Estructura del repositorio

```
taller-m5u5-calidad-cicd/
├── README.md                        ← esta guía
├── requirements.txt                 ← dependencias (GX 1.x, pandas, rich, pyarrow)
├── Makefile                         ← atajos opcionales
├── .github/workflows/
│   ├── 01-ci-dev.yml                ← CI: push/PR → pipeline + gate 95 % + artefactos
│   └── 02-cd-produccion.yml         ← CD: tag v* → gate 100 % → GitHub Release
├── src/
│   ├── config.py                    ← rutas, umbrales y reglas de negocio (fuente única)
│   ├── generators/                  ← generadores de datos sintéticos (sin modificar)
│   ├── utils/logger.py              ← logging con Rich (requerido por los generadores)
│   ├── quality/
│   │   ├── prepare.py               ← columnas de control (validaciones cross-field)
│   │   ├── suites.py                ← suites GX: 6 dimensiones + reglas de negocio
│   │   ├── runner.py                ← ejecuta validaciones y aplica el quality gate
│   │   └── reports.py               ← reportes HTML/JSON de cada validación
│   ├── cleaning/cleaner.py          ← reglas: reparar lo reparable, descartar lo demás
│   └── pipeline/run_pipeline.py     ← orquestador CLI del pipeline
├── data/
│   ├── raw/                         ← datos crudos (no se versionan; semilla fija)
│   ├── clean/                       ← datos certificados (CSV + Parquet)
│   └── reportes/                    ← evidencia de calidad (HTML + JSON)
└── docs/soluciones.md               ← soluciones de los ejercicios (no espiar 😉)
```

> 🔑 **Decisión DataOps**: los datos generados **no se versionan** (`.gitignore`), porque el
> pipeline los regenera de forma idéntica con semilla fija. El repositorio solo contiene código.

---

## Parte 0 · Preparación del entorno (15 min)

```bash
# 1) Clonar (o descargar y descomprimir) el proyecto
git clone https://github.com/TU-USUARIO/taller-m5u5-calidad-cicd.git
cd taller-m5u5-calidad-cicd

# 2) Crear y activar entorno virtual
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

# 3) Instalar dependencias
pip install -r requirements.txt
```

> **Windows (PowerShell)**: usa `py -m venv .venv` y `.venv\Scripts\Activate.ps1`.

**Verificación rápida** (debe imprimir la versión de GX sin errores):

```bash
python -c "import great_expectations as gx; print(gx.__version__)"
```

---

## Parte 1 · Primera ejecución y lectura del reporte (20 min)

Ejecuta el pipeline completo desde la raíz del proyecto:

```bash
python -m src.pipeline.run_pipeline
```

Qué va a pasar (y qué discutir mientras corre):

1. **EXTRACCIÓN** — genera 1,000 clientes y 2,000 órdenes con errores controlados (~15 % y ~20 % de las filas).
2. **VALIDACIÓN RAW** — Great Expectations audita los datos crudos. **Se ven fallos rojos y es correcto**: es la radiografía del problema.
3. **LIMPIEZA** — pandas repara lo reparable (recalcular edad, país, moneda, totales…) y descarta lo incurable (emails inválidos, clientes inexistentes…).
4. **VALIDACIÓN CLEAN + GATE** — la misma suite revalida. Con el umbral DEV (95 %) el gate pasa y los datos certificados se publican en `data/clean/` (CSV + Parquet).
5. **REPORTES** — cada validación dejó evidencia en `data/reportes/`.

Ahora abre el reporte de la auditoría cruda de clientes:

```bash
# macOS
open data/reportes/clientes_raw.html
# Windows
start data\reportes\clientes_raw.html
# Linux
xdg-open data/reportes/clientes_raw.html
```

**Conversación guiada sobre el reporte (Unidad 1):**

- ¿Qué dimensión concentra más fallos? ¿Por qué el generador la golpea más?
- Compara `clientes_raw.html` vs `clientes_clean.html`: la limpieza **repara** (consistencia) y **descarta** (validez, exactitud). ¿Qué passaría con cada estrategia en un caso de negocio real (p. ej., no puedes "descartar" un cliente con facturación activa)?
- Cada expectativa fallida muestra ejemplos (`ej: customer_id=...`): ¿cómo ayuda eso a diagnosticar la causa raíz en lugar de solo "hay errores"?

---

## Parte 2 · Anatomía de una validación GX (25 min)

Abre `src/quality/suites.py` y recorre la suite `clientes_calidad` con la clase.
Puntos clave del recorrido:

**1) Toda expectativa lleva `meta`** — dimensiona y da contexto de negocio:

```python
suite.add_expectation(
    gxe.ExpectColumnValuesToNotBeNull(
        column="email",
        meta=_meta("Completitud", "email no puede ser nulo (canal de contacto)."),
    )
)
```

**2) Las 6 dimensiones están representadas así:**

| Dimensión | Expectativa GX | Columna de control |
|---|---|---|
| Completitud | `ExpectColumnValuesToNotBeNull` | — |
| Unicidad | `ExpectColumnValuesToBeUnique` | — |
| Validez | `ExpectColumnValuesToMatchRegex`, `...ToBeBetween` | — |
| Consistencia | `...ToBeInSet` / `...ToBeBetween` | `city_country_ok`, `age_diff` |
| Exactitud | `...ToBeBetween` (rangos realistas) | — |
| Oportunidad | `...ToBeBetween` | `last_update_year` |

**3) Reglas cross-field = columnas de control** (`src/quality/prepare.py`).
GX valida columna por columna; cuando la regla relaciona varios campos
(total vs. componentes, ciudad vs. país, fechas en jerarquía), el pipeline
**calcula primero** la columna de control y luego la expectativa la audita:

```python
out["total_diff"] = (out["total_amount"] - expected_total).abs()   # preparar…
# …validar:
gxe.ExpectColumnValuesToBeBetween(column="total_diff", min_value=0, max_value=0.01)
```

**4) Condiciones por fila** — las órdenes CANCELLED no tienen entrega (nulo a
propósito) y quedan fuera de la regla temporal:

```python
gxe.ExpectColumnValuesToBeInSet(
    column="deliver_after_ship", value_set=[True],
    row_condition='order_status != "CANCELLED"', condition_parser="pandas",
)
```

**5) El gate** (`src/quality/runner.py`) convierte el % de éxito en una decisión:
`porcentaje_exito >= umbral` → código de salida 0 (promociona) o 1 (bloquea).

---

## Parte 3 · Ejercicios (30 min)

> Las soluciones están en [`docs/soluciones.md`](docs/soluciones.md). Intenta primero sin mirar.

### Ejercicio 1 — Amplía la suite de clientes (10 min)

En `src/quality/suites.py`, añade a `clientes_calidad`:

1. `country` solo puede ser uno de los países operados (`VALID_COUNTRIES`).
2. `customer_id` debe cumplir el patrón `^CUST-\d{6}$`.
3. (Reto) Una expectativa propia de la dimensión que elijas, con su `meta`.

Ejecuta el pipeline y verifica que la suite pasa de 18 a 21 expectativas **manteniendo el 100 % en CLEAN**.

### Ejercicio 2 — Rompe el quality gate a propósito (10 min)

Simula un bug de producción: en `src/cleaning/cleaner.py`, comenta la regla de
limpieza de emails inválidos (`_drop(out["email"].astype(str).str.match(...))`)
y vuelve a ejecutar:

```bash
python -m src.pipeline.run_pipeline --min-success 100   # umbral estricto
echo $?    # → 1: el pipeline FALLA y bloquea la promoción
```

Observa: ¿qué expectativa se pone roja? ¿Qué cambió en `data/clean/` (no se publicó, ¿verdad?)?
Restaura la regla y confirma el verde. **Esa es, en miniatura, la función de un quality gate.**

### Ejercicio 3 — Umbral por ambiente (10 min)

- Ejecuta en modo DEV (`--min-success 95`) y en modo PROD (`--min-success 100`).
- Sube el umbral DEV a 99: ¿sigue pasando? ¿Por qué con esta limpieza SÍ y con datos reales probablemente NO?
- Discusión: ¿qué umbral pondrías para un pipeline financiero? ¿Y para un dashboard de marketing? *(No hay respuesta única: es gestión de riesgo.)*

---

## Parte 4 · CI/CD en GitHub (25 min)

### 4.1 Sube el repositorio (5 min)

```bash
git init
git add .
git commit -m "Taller M5·U5: calidad de datos con GX y CI/CD"
git branch -M main
git remote add origin https://github.com/TU-USUARIO/taller-m5u5-calidad-cicd.git
git push -u origin main
```

Entra a la pestaña **Actions** del repo: el workflow *CI · Calidad de datos (DEV)*
se está ejecutando. Ábrelo y observa los pasos: install → pipeline → artefactos.

### 4.2 Descarga la evidencia (5 min)

Al terminar, en **Summary** (parte inferior) está el artefacto `reportes-calidad`
con los 8 reportes HTML/JSON. **Evidencia auditable de calidad, generada en cada push.**

### 4.3 Pull request con revisión (10 min)

1. Crea una rama: `git checkout -b ejercicio-1`.
2. Implementa el Ejercicio 1, commit y push: `git push -u origin ejercicio-1`.
3. Abre un **Pull Request** → el CI corre sobre el PR y publica el resultado (verde/rojo) **antes** de mezclar. Discute: esto es *integración continua aplicada a datos*.
4. Mezcla solo si está verde.

### 4.4 Promoción a producción con tag (5 min)

```bash
git tag v1.0.0
git push origin v1.0.0
```

Dispara *CD · Promoción a producción*: el pipeline corre con **gate estricto (100 %)** y,
al pasar, publica un **GitHub Release** con `customers_clean.csv` y `orders_clean.csv`
como "datos certificados". En la sección *Releases* del repo queda la versión descargable.

> 🎓 **Mapa a la teoría (U5)**: push/PR → *integración continua*; tag → *despliegue/promoción*;
> gate rojo que bloquea → *deployment gate*; Release versionado → *artefacto productivo*.

---

## Cierre · Preguntas de reflexión (5 min)

1. ¿Por qué el gate se aplica a los datos limpios y la validación raw es solo informativa?
2. En un pipeline real con Airflow/dbt (Módulo 3), ¿dónde encajaría esta validación? ¿Qué cambiaría?
3. ¿Qué alertas añadirías cuando el gate bloquea en producción? ¿Quién debería enterarse y cómo?
4. ¿Qué dimensión de calidad sería más costosa de violar en tu organización? ¿Cómo la detectarías hoy?

---

## Solución de problemas

| Síntoma | Causa probable | Solución |
|---|---|---|
| `ModuleNotFoundError: src` al ejecutar el pipeline | No estás en la raíz del proyecto | Ejecuta siempre desde `taller-m5u5-calidad-cicd/` |
| `python` no encontrado (Windows) | Python sin PATH / usa el launcher | Usa `py -m venv .venv` y `py -m src.pipeline.run_pipeline` |
| Error al instalar `great_expectations` | pip viejo o Python < 3.10 | `python -m pip install --upgrade pip`; verifica `python --version` |
| Parquet falla (`to_parquet`) | Falta `pyarrow` | `pip install -r requirements.txt` dentro del venv activo |
| El CI queda rojo pero en local pasa verde | Versiones distintas | El CI instala `requirements.txt`: replica el venv local desde cero |
| Cambié el generador y los resultados no cambian | Semilla fija es determinista | Cambia `--seed` (pero los resultados de referencia del README ya no aplican) |

---

## Glosario exprés

- **Expectativa**: afirmación comprobable sobre los datos ("email no nulo y con formato").
- **Suite**: conjunto de expectativas que auditan un dataset.
- **Quality gate**: regla de promoción (umbral de % de éxito) que bloquea el despliegue si no se cumple.
- **Columna de control**: columna derivada que materializa una regla cross-field para poder validarla.
- **Artefacto**: archivo publicado por una ejecución de Actions (aquí, los reportes de calidad).
- **Release**: versión publicada del repo; en este taller transporta los datos certificados.
- **Reproducibilidad**: misma semilla → mismos datos → mismo resultado de calidad, en cualquier máquina.

---

## Ideas para llevar el taller más lejos

- Ejecutar el CI **programado** (`schedule: cron`) para simular monitoreo continuo.
- Publicar los reportes en **GitHub Pages** en lugar de artefactos.
- Convertir las validaciones en **pruebas pytest** (`pytest tests/`) y medir cobertura.
- Alertar por **Slack/email** cuando el gate de producción bloquee.
- Conectar el pipeline a una base de datos real (PostgreSQL del Módulo 2) como destino de la carga.
