# 📘 Manual de GitHub Actions — CI/CD para pipelines de datos

> **Taller M5·U5 · Calidad de Datos con Great Expectations y CI/CD en GitHub**
> Manual de referencia para el instructor y los participantes. No requiere experiencia previa
> con GitHub Actions: parte de cero y termina con el flujo completo **DEV → PROD** funcionando
> sobre el proyecto del taller.

---

## Índice

1. [¿Qué es CI/CD (y por qué importa en datos)?](#1-qué-es-cicd-y-por-qué-importa-en-datos)
2. [¿Qué es GitHub Actions?](#2-qué-es-github-actions)
3. [Anatomía de un workflow: el archivo YAML](#3-anatomía-de-un-workflow-el-archivo-yaml)
4. [El CI/CD de este proyecto, explicado línea a línea](#4-el-cicd-de-este-proyecto-explicado-línea-a-línea)
5. [Puesta en marcha paso a paso (de cero a CI verde)](#5-puesta-en-marcha-paso-a-paso)
6. [Promoción a producción: tags y Releases](#6-promoción-a-producción-tags-y-releases)
7. [Ejercicios prácticos para el taller](#7-ejercicios-prácticos-para-el-taller)
8. [Solución de problemas frecuentes](#8-solución-de-problemas-frecuentes)
9. [Glosario y referencia rápida](#9-glosario-y-referencia-rápida)

---

## 1. ¿Qué es CI/CD (y por qué importa en datos)?

**CI/CD** son las siglas de *Continuous Integration* (integración continua) y *Continuous
Delivery/Deployment* (entrega o despliegue continuos). Nacieron en el mundo del software,
pero se aplican igual —o con más razón— a los pipelines de datos:

- **Integración continua (CI):** cada vez que alguien sube cambios al repositorio, una
  máquina limpia y aislada ejecuta automáticamente las mismas verificaciones que ejecutarías
  a mano: instalar dependencias, correr el pipeline, validar la calidad. Si algo falla, el
  equipo lo sabe **en minutos**, no semanas después cuando el dato malo ya llegó a producción.
- **Entrega/despliegue continuo (CD):** si las verificaciones pasan, los artefactos
  (en este taller: los datos certificados) se **publican automáticamente** en el ambiente
  de destino, sin pasos manuales y sin olvidos.

En un pipeline de datos, la diferencia clave es que el "test" no prueba solo código: prueba
**también los datos en sí mismos** contra reglas de calidad (las *expectativas* de Great Expectations).
Eso convierte al CI/CD en el transportador de una **quality gate**: una barrera que mide el
porcentaje de expectativas cumplidas y **bloquea el paso** si no alcanza el umbral del ambiente.

> 🎓 **La idea central del taller:** los datos crudos fallan la auditoría (RAW: 27.78 % y 35 %),
> el pipeline limpia y revalida (CLEAN: 100 %), y **solo si el gate pasa se promocionan**.
> En DEV el umbral es 95 %; para saltar a PROD se exige 100 %.

---

## 2. ¿Qué es GitHub Actions?

**GitHub Actions** es la plataforma de automatización integrada en GitHub. escucha *eventos*
que ocurren en tu repositorio (un `push`, un *pull request*, la creación de un *tag*, un clic
en un botón…) y, en respuesta, ejecuta flujos de trabajo definidos por ti en máquinas que
GitHub alquila y configura. No necesitas instalar Jenkins, ni servidores de build, ni
mantener agentes: **el repositorio es el disparador y GitHub pone la infraestructura**.

### 2.1 Vocabulario esencial

| Concepto | Qué es | En este taller |
|---|---|---|
| **Workflow** | Un proceso automatizado definido en un archivo YAML dentro de `.github/workflows/` | `01-ci-dev.yml` y `02-cd-produccion.yml` |
| **Evento (trigger)** | Lo que dispara el workflow: `push`, `pull_request`, `workflow_dispatch`, `schedule`… | push a `main`, PRs, tags `v*.*.*`, botón manual |
| **Job** | Un conjunto de pasos que corre en un mismo runner | `calidad-datos`, `promocion-produccion` |
| **Step** | Una tarea individual dentro de un job (un comando o una acción) | `pip install -r requirements.txt` |
| **Runner** | La máquina virtual que ejecuta el job (Ubuntu, Windows, macOS) | `ubuntu-latest` |
| **Action** | Un paso reutilizable publicado por la comunidad o por GitHub | `actions/checkout@v4`, `actions/setup-python@v5` |
| **Artefacto** | Archivo que el workflow guarda al terminar, descargable desde la UI | `reportes-calidad` (HTML/JSON) |
| **Release** | Publicación versionada en GitHub, con archivos adjuntos | Los CSV certificados de `v1.0.0` |

### 2.2 ¿Cómo funciona por dentro?

Cuando ocurre un evento que coincide con un `on:` de algún workflow:

1. GitHub lee los YAML de `.github/workflows/` y decide qué workflows disparar.
2. Crea una **ejecución (run)** visible en la pestaña **Actions** del repositorio.
3. Aprovisiona un **runner** limpio (una VM Ubuntu recién creada que se destruye al acabar).
4. Ejecuta los jobs paso a paso; si un paso falla (código de salida ≠ 0), el job se marca ❌
   y, por defecto, los pasos siguientes se omiten.
5. Los pasos con `if: always()` se ejecutan **aunque todo lo anterior falle** — así publicamos
   los reportes de calidad incluso cuando el gate bloquea.

El runner es desechable: cada ejecución parte de cero. Eso es una virtud, no un problema:
garantiza que el pipeline funciona **en una máquina limpia**, no solo "en mi laptop".

### 2.3 ¿Qué es gratis?

GitHub Actions es gratuito en repositorios **públicos** (con límites razonables de uso) y
incluye 2,000 minutos/mes gratis en planes privados individuales. Para este taller: costo $0.

---

## 3. Anatomía de un workflow: el archivo YAML

Un workflow es un archivo de texto con formato YAML ubicado **obligatoriamente** en
`.github/workflows/` (la ruta y la extensión `.yml`/`.yaml` no son negociables: GitHub
escanea esa carpeta). Este es el esqueleto con las piezas que usaremos:

```yaml
name: "Nombre visible en la pestaña Actions"     # opcional pero recomendado

on:                                              # ← DISPARADORES
  push:
    branches: [main]                             #     push a main
  pull_request:                                  #     cualquier pull request
  workflow_dispatch:                             #     botón "Run workflow" en la UI

env:                                             # ← VARIABLES GLOBALES
  PYTHON_VERSION: "3.12"

jobs:                                            # ← LOS TRABAJOS
  mi-job:
    name: Nombre legible del job
    runs-on: ubuntu-latest                       # máquina que ejecuta
    steps:
      - name: Descargar el código
        uses: actions/checkout@v4                # ← ACTION: paso reutilizable

      - name: Un comando nuestro
        run: echo "Hola desde el runner"         # ← RUN: shell directo

      - name: Paso que siempre corre
        if: always()                             # ← CONDICIÓN
        run: echo "Corre incluso si algo falló"
```

Reglas de oro para leer (y escribir) YAML de Actions:

- **`uses:`** invoca una *action* publicada (con su versión: `@v4`); **`run:`** ejecuta
  comandos de shell. Un step usa una u otra, nunca ambas.
- **`${{ ... }}`** es la sintaxis de *expresiones*: acceso a contexto (`github.ref`,
  `github.event.inputs…`), condiciones y variables.
- La **indentación sí importa** (como en Python): `steps:` se anida bajo el job, no al revés.
- Si un step `run:` termina con código distinto de 0 (como nuestro quality gate cuando el
  umbral no se alcanza), **GitHub marca el step/job en rojo automáticamente**. Nuestro gate
  aprovecha exactamente ese mecanismo: `exit 1` = gate rojo = promoción bloqueada.

---

## 4. El CI/CD de este proyecto, explicado línea a línea

El proyecto ya viene **completo y conectado**: la parte de CI/CD no hay que programarla,
solo subirla a GitHub y entenderla. Son **dos workflows** que representan los dos ambientes:

```
                    ┌─────────────────────────────────────────────┐
                    │        git push / pull request / tag        │
                    └──────────────────┬──────────────────────────┘
                                       │
              ┌────────────────────────┴───────────────────────┐
              ▼                                                ▼
   ┌──────────────────────┐                        ┌──────────────────────────┐
   │  01-ci-dev.yml (CI)  │                        │ 02-cd-produccion.yml(CD) │
   │  push a main / PR    │                        │  tag v*.*.*              │
   │  gate DEV: 95 %      │                        │  gate PROD: 100 %        │
   │  → artefacto         │                        │  → GitHub Release (CSV)  │
   └──────────────────────┘                        └──────────────────────────┘
        ambiente DESARROLLO                              ambiente PRODUCCIÓN
```

Ambos ejecutan **el mismo pipeline** (`src/pipeline/run_pipeline.py`); lo único que cambia
es el **umbral del quality gate** y el **destino de la publicación**. Ese es el patrón
*"mismo código, distinta barra por ambiente"* que usa la industria.

### 4.1 Workflow de CI — `.github/workflows/01-ci-dev.yml`

```yaml
name: "CI · Calidad de datos (DEV)"

on:
  push:
    branches: [main]        # cada push a main dispara el pipeline
  pull_request:             # cada PR se valida ANTES de fusionarse
  workflow_dispatch:        # ejecución manual desde la UI
    inputs:
      min_success:          # el umbral se puede ajustar a mano
        description: "Umbral del quality gate (%)"
        required: false
        default: "95"

env:
  PYTHON_VERSION: "3.12"

jobs:
  calidad-datos:
    name: Pipeline + quality gate (DEV)
    runs-on: ubuntu-latest
    steps:
      - name: Descargar el código
        uses: actions/checkout@v4

      - name: Configurar Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}
          cache: pip                        # cachea dependencias → runs más rápidos

      - name: Instalar dependencias
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt

      - name: Ejecutar pipeline (extraer → validar → limpiar → revalidar → publicar)
        run: |
          python -m src.pipeline.run_pipeline \
            --min-success "${{ github.event.inputs.min_success || '95' }}"

      - name: Publicar reportes de calidad (artefacto)
        if: always()                        # ← evidencia incluso si el gate FALLA
        uses: actions/upload-artifact@v4
        with:
          name: reportes-calidad
          path: data/reportes/
          retention-days: 30
```

**Qué hace cada pieza y por qué:**

| Paso | Explicación |
|---|---|
| `checkout@v4` | Clona el repo dentro del runner. Sin esto, el runner no sabe nada de tu código. |
| `setup-python@v5` + `cache: pip` | Instala Python 3.12 y cachea los paquetes de `requirements.txt` para acelerar las siguientes ejecuciones. |
| `run_pipeline --min-success 95` | Corre el pipeline completo con el umbral de desarrollo. **Si el gate no pasa, el script sale con `exit 1` y el workflow se pone rojo.** |
| `upload-artifact` con `if: always()` | Publica los reportes HTML/JSON como evidencia auditable, **aunque el pipeline falle**: así siempre puedes abrir el reporte y ver *qué* expectativa reventó. |

El input `min_success` de `workflow_dispatch` es un regalo didáctico: permite ejecutar el
mismo pipeline con otro umbral (p. ej. 101 %) para **ver el gate romperse a propósito** en el
ejercicio 2, sin tocar una línea de código.

### 4.2 Workflow de CD — `.github/workflows/02-cd-produccion.yml`

```yaml
name: "CD · Promoción a producción"

on:
  push:
    tags: ["v*.*.*"]        # ← SOLO tags de versión: v1.0.0, v2.3.1, …
  workflow_dispatch:

permissions:
  contents: write           # necesario para crear el Release

env:
  PYTHON_VERSION: "3.12"

jobs:
  promocion-produccion:
    name: Gate estricto (100 %) + release de datos certificados
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12", cache: pip }
      - run: pip install -r requirements.txt

      - name: Pipeline con quality gate de producción
        run: python -m src.pipeline.run_pipeline --min-success 100

      - name: Publicar datos certificados como GitHub Release
        if: startsWith(github.ref, 'refs/tags/')
        uses: softprops/action-gh-release@v2
        with:
          files: |
            data/clean/customers_clean.csv
            data/clean/orders_clean.csv
          generate_release_notes: true
```

**Las tres decisiones de diseño que debes poder explicar:**

1. **El disparador es un tag, no un push.** Promocionar a producción es una *decisión
   consciente*: crear `v1.0.0` es el "botón de despliegue". Un push normal nunca llega a prod.
2. **`permissions: contents: write`.** Por defecto los workflows son de solo lectura; para que
   la action pueda **crear el Release** hay que otorgar explícitamente este permiso. Es parte
   del modelo de seguridad de GitHub (mínimo privilegio).
3. **El Release solo se publica si el gate 100 % pasó.** El paso del Release está *después* del
   pipeline: si el pipeline sale con `exit 1`, los pasos siguientes se omiten y **nada se publica**.
   Ese es, literalmente, el gate bloqueando la promoción de datos defectuosos.

> 💡 **Prueba de concepto honesta:** en un proyecto real, este job desplegaría a un warehouse
> (Snowflake, BigQuery), cargaría tablas en Postgres o dispararía Airflow/dbt. Publicar un
> Release con los CSV certificados es la versión mínima que mantiene el taller simple:
> los datos quedan **versionados, descargables y asociados a un tag**.

---

## 5. Puesta en marcha paso a paso

De cero a CI verde en ~10 minutos. Todo lo que hay que "trabajar" en CI/CD es esto:
**subir el proyecto a GitHub y observar**. No hay secretos, servidores ni servicios externos.

### Paso 0 · Verifica el proyecto localmente (opcional pero recomendado)

```bash
cd taller-m5u5-calidad-cicd
make setup          # crea .venv e instala dependencias (o: python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt)
make pipeline       # pipeline completo, umbral DEV 95 % → debe terminar en verde (exit 0)
```

### Paso 1 · Crea el repositorio en GitHub

1. Entra a <https://github.com/new>.
2. Nombre sugerido: `taller-m5u5-calidad-cicd`. Visibilidad: **Public** (Actions gratis e
   ilimitado; además los participantes podrán ver los Releases sin cuenta paga).
3. **NO** marques "Add a README" ni ".gitignore" ni "license": el proyecto ya los trae y un
   commit inicial de GitHub complicaría el primer push.
4. Crea el repo (botón verde **Create repository**).

### Paso 2 · Sube el proyecto (primer push)

```bash
cd taller-m5u5-calidad-cicd
git init
git add .
git commit -m "Taller M5U5: pipeline de calidad GX + CI/CD"
git branch -M main
git remote add origin https://github.com/TU-USUARIO/taller-m5u5-calidad-cicd.git
git push -u origin main
```

> 🔁 Sustituye `TU-USUARIO` por tu usuario de GitHub. Si te pide credenciales, usa un
> **Personal Access Token** como contraseña (GitHub ya no acepta contraseñas en git push).

El momento clave: la carpeta `.github/workflows/` llega a `main` y **GitHub dispara el
workflow de CI automáticamente**. No hay que configurar nada más — ese es el punto de
"el proyecto ya está listo para CI/CD".

### Paso 3 · Observa la primera ejecución

1. Abre la pestaña **Actions** de tu repositorio.
2. Verás *"CI · Calidad de datos (DEV)"* en ejecución con un círculo 🟡 amarillo.
3. Entra al run → al job *"Pipeline + quality gate (DEV)"* → expande los pasos para ver el
   log en vivo: instalación, generación de datos, validaciones GX, gate `GATE PASSED`.
4. En ~2-4 minutos el círculo se vuelve ✅ verde.

**Lectura del resultado esperado** (semilla 42, reproducible):

| Validación | Resultado en el log |
|---|---|
| RAW clientes | 5/18 (27.78 %) — fallos **esperados**, fase informativa |
| RAW órdenes | 7/20 (35.0 %) — ídem |
| CLEAN clientes | 18/18 (100 %) |
| CLEAN órdenes | 20/20 (100 %) |
| **Gate DEV (95 %)** | ✅ `GATE PASSED` → `exit 0` → run verde |

### Paso 4 · Descarga la evidencia (artefactos)

En la página del run, sección **Artifacts** (abajo): descarga `reportes-calidad`. Contiene los
4 HTML + 4 JSON de `data/reportes/`. Abre `clientes_raw.html` en el navegador: verás el
detalle de las 13 expectativas fallidas con sus filas problemáticas. **Esta evidencia existe
aunque el pipeline falle** — así depuran los participantes.

### Paso 5 (opcional, recomendado) · Corrige los badges del README

En `README.md`, reemplaza `TU-USUARIO/TU-REPO` por tu usuario y repo en las dos líneas de
badges, haz `git add README.md && git commit -m "badges" && git push`. Los badges mostrarán
el estado en vivo del CI y del CD: verde si el último run pasó, rojo si no.

---

## 6. Promoción a producción: tags y Releases

Con el CI verde, el flujo completo **DEV → PROD** es un solo comando (más el push):

```bash
git tag v1.0.0
git push origin v1.0.0
```

Qué pasa detrás del telón, en orden:

1. El push del tag dispara `02-cd-produccion.yml` (coincide con `tags: ["v*.*.*"]`).
2. El runner ejecuta el **mismo pipeline** pero con `--min-success 100` (gate estricto).
3. Si el gate **pasa** → `softprops/action-gh-release` crea el Release `v1.0.0` con
   `customers_clean.csv` y `orders_clean.csv` adjuntos y notas generadas automáticamente.
4. Si el gate **fallara** → el workflow se detiene en rojo y **no se publica nada**:
   la promoción queda bloqueada. (Así de simple y así de estricto.)

**Para verificar:** pestaña **Releases** (o **Actions** → run del CD). Verás *v1.0.0* con los
dos CSV descargables — esos son los "datos certificados para producción", con trazabilidad
completa: qué commit, qué reglas de calidad y qué porcentaje de cumplimiento los avalan.

**Para la siguiente versión:** cambias algo (p. ej. una expectativa nueva), subes el cambio,
y publicas `v1.1.0`. Cada Release queda congelado con los datos que le tocaron: **versionado
de datos de facto**, sin infraestructura adicional.

---

## 7. Ejercicios prácticos para el taller

*(25-30 min · Parte 4 de la agenda. Cada ejercicio usa solo la UI de GitHub y git.)*

### 🧪 Ejercicio 1 — Recorrido guiado por Actions (5 min)

Objetivo: familiarizarse con la pestaña Actions y los logs.

1. Pestaña **Actions** → run más reciente de CI → job → expande cada paso.
2. Encuentra en el log: la línea de cada suite GX, los porcentajes RAW/CLEAN y el `GATE PASSED`.
3. Descarga el artefacto `reportes-calidad` y abre un HTML.

**Pregunta para discutir:** ¿por qué el paso de reportes usa `if: always()`? ¿Qué pasaría
sin él cuando el gate falla?

### 🧪 Ejercicio 2 — Rompe el quality gate a propósito (10 min)

Objetivo: ver el CI **en rojo** y entender que el gate realmente bloquea.

1. Pestaña **Actions** → workflow *"CI · Calidad de datos (DEV)"* → botón **Run workflow**.
2. En el input `Umbral del quality gate (%)` escribe `101` (imposible por diseño).
3. Ejecuta y observa: el run termina ❌ rojo, el job falla en el paso del pipeline.
4. Descarga el artefacto: los reportes **sí existen** (`if: always()`), con el detalle de fallos.

**Pregunta para discutir:** ¿qué "exit code" habrá devuelto el script del pipeline? *(Respuesta:
1. El rojo de GitHub no es magia: es el código de salida del proceso.)*

### 🧪 Ejercicio 3 — El ciclo completo: feature → PR → merge → release (15 min)

Objetivo: practicar el flujo real de trabajo con CI/CD.

```bash
# 1. Rama feature
git checkout -b feature/expectativa-email-corporativo
# 2. Edita src/quality/suites.py: añade una expectativa nueva a la suite de clientes
#    (p. ej. que el email contenga "@"), siguiendo el patrón meta={"dimension": ..., "regla": ...}
git add src/quality/suites.py
git commit -m "Nueva expectativa: email válido"
git push -u origin feature/expectativa-email-corporativo
# 3. Abre el Pull Request en GitHub → el CI corre SOLO en la rama antes de fusionar
# 4. Si está verde → Merge pull request
# 5. Publica la nueva versión certificada:
git tag v1.1.0
git push origin v1.1.0
# 6. Observa el CD en Actions → nuevo Release v1.1.0 con los CSV
```

**Pregunta para discutir:** si la expectativa nueva fuera imposible de cumplir (p. ej. 101 %
de éxito), ¿en qué paso exacto se rompería el flujo? ¿Se publicaría el Release v1.1.0?

### 🧪 Ejercicio opcional — Proteger `main` (5 min, solo instructor)

*Settings → Branches → Branch protection rule* sobre `main`: exige
*"Require status checks to pass"* → `Pipeline + quality gate (DEV)`. A partir de ahora,
**GitHub no permite fusionar un PR si el gate está rojo**: la política de calidad se vuelve
imposible de saltar, no solo difícil.

---

## 8. Solución de problemas frecuentes

| Síntoma | Causa probable | Solución |
|---|---|---|
| La pestaña Actions está vacía / no corre nada | `.github/workflows/` no se subió (¡es carpeta oculta!) | `git status`; asegúrate de que `git add .` la incluyó: `git ls-files .github` |
| El run falla en *Instalar dependencias* | Versión de Python o conflicto de paquetes | Compara el log con tu `make pipeline` local; el repo está probado con Python 3.12 |
| El workflow de CD no se dispara al hacer tag | El tag no coincide con `v*.*.*` o no se empujó | Los tags NO viajan con `git push` normal: usa `git push origin v1.0.0` |
| El CD corre pero no crea el Release | Ejecutaste el CD con `workflow_dispatch` (botón), no con tag | Es el comportamiento correcto: el paso del Release tiene `if: startsWith(github.ref, 'refs/tags/')` |
| "Permission denied" / "resource not accessible" al crear el Release | Falta `permissions: contents: write` | Ya está en el YAML; no lo elimines al editar |
| El run quedó "queued" mucho tiempo | Cola puntual de GitHub (raro) | Espera o reejecuta con **Re-run jobs** |
| El pipeline falla localmente pero no en CI (o viceversa) | Datos viejos en `data/` | `make limpiar` y vuelve a ejecutar; en CI siempre parte de cero (semilla 42 → mismo resultado) |
| `git push` pide contraseña y falla | GitHub exige token, no contraseña | Crea un PAT: *Settings → Developer settings → Personal access tokens* |

---

## 9. Glosario y referencia rápida

**Glosario mínimo:**

- **Quality gate:** barrera automática que mide la calidad (aquí: % de expectativas GX
  cumplidas) y bloquea la promoción si no alcanza el umbral del ambiente (DEV 95 %, PROD 100 %).
- **Artefacto:** archivo que un workflow conserva y ofrece para descarga (nuestros reportes).
- **Release:** publicación versionada en GitHub con archivos adjuntos (nuestros CSV certificados).
- **Tag:** etiqueta inmutable sobre un commit (`v1.0.0`); aquí actúa como botón de despliegue.
- **Runner:** máquina efímera de GitHub que ejecuta los jobs; nace y muere en cada run.
- **PAT:** *Personal Access Token*, la "contraseña" que git pide al hacer push hoy en día.

**Chuleta de comandos:**

```bash
# ── Local (referencia) ──────────────────────────────────────────
make setup            # venv + dependencias
make pipeline         # pipeline completo, umbral DEV 95 %
make prod             # umbral PROD 100 %
make raw-reportes     # revalida datos existentes (--skip-generate)
make limpiar          # borra data/ generada (seed 42 la regenera igual)

# ── CI/CD en GitHub ─────────────────────────────────────────────
git push origin main          # dispara CI (gate DEV 95 %)
git tag v1.0.0 && git push origin v1.0.0   # dispara CD (gate 100 % → Release)

# ── En la UI de GitHub ──────────────────────────────────────────
# Actions            → ejecuciones, logs, artefactos, Run workflow (manual)
# Releases           → datos certificados publicados
# Settings→Branches   → protección de main con el gate como check obligatorio
```

> 📚 Para profundizar: [documentación oficial de GitHub Actions](https://docs.github.com/es/actions)
> y [sintaxis de workflow](https://docs.github.com/es/actions/using-workflows/workflow-syntax-for-github-actions).

---

*Manual del Taller M5·U5 — PAE Data Engineer · Módulo 5: Calidad, DataOps y Producción Production-Ready.*
