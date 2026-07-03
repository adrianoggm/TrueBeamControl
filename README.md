# grafi

Herramienta de control de calidad diario del acelerador **TrueBeam 2** a partir
de sus CSVs. Normaliza fechas de distintos formatos, dibuja la evolucion de cada
prueba y calcula estadisticas frente a sus tolerancias.

Reune dos pruebas diarias en un mismo panel:

- **MPC Output change (%)** — de los CSV de haz (uno por energia: 6X, 6FFF, 10,
  15). Tolerancia +/-2% (aviso a +/-1%). Se actualizan a diario.
- **QuickCheck CAX (% de nominal)** — del fichero Measdata, filtrando la unidad
  `TRUEBEAM-2` y la columna `CAX.2`. Nominal 100%, tolerancia 98-102%. Measdata
  contiene varios aceleradores y se actualiza esporadicamente con todo el
  historico.

Tiene dos formas de uso:

- **App interactiva** (`app.py`, Streamlit): panel con las dos pruebas apiladas,
  selector de energia, filtro de fechas compartido y estadisticas por energia.
- **Script de linea de comandos** (`programa_graficar.py`): genera una grafica
  suelta de un CSV, configurable por variables de entorno. Sirve tambien como
  libreria de datos que reutiliza la app.

## Requisitos

- Python 3.10+ (se usan anotaciones tipo `str | None`)
- Dependencias en `requirements.txt`: `pandas`, `matplotlib`, `streamlit`, `plotly`

```bash
pip install -r requirements.txt
```

## Uso

### App interactiva (recomendado)

```bash
streamlit run app.py
```

Si `streamlit` no esta en el PATH, funciona igual llamandolo como modulo de
Python:

```bash
python -m streamlit run app.py
```

Se abre en el navegador y muestra dos graficas apiladas (MPC arriba, QuickCheck
CAX abajo), cada una con su tabla de estadisticas por energia. En la barra
lateral izquierda:

- **Actualizar datos** — vuelve a leer los CSV de la carpeta (los ficheros se
  releen en cada recarga; este boton la fuerza).
- **Energia** — `Todas` (superpone las 4) o una concreta (6X, 6FFF, 10FFF, 15).
- **Rango de fechas** — slider compartido por las dos graficas.
- **Agregacion** — `Punto a punto` (cada medida) o agrupar por `Dia` / `Semana`
  / `Mes`.
- **Funcion** — al agregar, si tomar la `media`, el `maximo` o el `minimo` de
  cada periodo (desactivada en punto a punto).

Cada grafica es interactiva (zoom, desplazamiento, hover, descargar PNG) e
incluye sus lineas de tolerancia. Debajo, una tabla por energia con nº de
puntos, media, desviacion, minimo, maximo y % de puntos fuera de tolerancia,
que se recalcula al mover cualquier control.

La carpeta de datos es `data` por defecto; se cambia con `GRAFI_DATA_DIR`. De
cada tipo de fichero se usa el mas reciente por nombre.

### Script de linea de comandos

```bash
python programa_graficar.py
```

Muestra las energias disponibles, eliges una y abre la grafica de ese informe
de haz.

Para graficar un CSV concreto (cualquiera de los dos formatos) sin pasar por el
selector:

```bash
GRAFI_FILE="data/Measdata 2026-07-03 12'31'42.csv" python programa_graficar.py
```

En Windows (PowerShell):

```powershell
$env:GRAFI_FILE = "data\Measdata 2026-07-03 12'31'42.csv"; python programa_graficar.py
```

## Configuracion

La configuracion se lee de variables de entorno con prefijo `GRAFI_`, y tambien
de un fichero `.env` en la raiz del proyecto (se carga automaticamente; una
variable definida en la terminal tiene prioridad sobre el `.env`). Edita el
`.env` para cambiar los valores por defecto.

| Variable | Por defecto | Que hace | La usa |
|----------|-------------|----------|--------|
| `GRAFI_DATA_DIR` | `data` | Carpeta donde estan los CSV. | app + script |
| `GRAFI_DATE_FORMAT` | `%d/%m/%Y %H:%M` | Formato de fecha en el eje X (dia/mes/ano hora). | script |
| `GRAFI_DATE_COL` | `Date` | Nombre de la columna de fechas. | app + script |
| `GRAFI_VALUE_COL` | `BeamGroup/BeamOutputChange [%]` | Columna numerica por defecto. | app + script |
| `GRAFI_PLOT` | `tolerancia` | Que grafica generar (ver `PLOTTERS`). | script |
| `GRAFI_ENERGIA` | — | Energia a graficar sin preguntar (p.ej. `6x`). | script |
| `GRAFI_ENERGIAS` | `6x,6xFFF,10xFFF,15x` | Lista de energias del selector. | script |
| `GRAFI_FILE` | — | Ruta a un CSV concreto; salta el selector de energia. | script |
| `GRAFI_DEMO` | — | Si esta definida, ejecuta el autochequeo en vez de graficar. | script |

## Formatos de CSV soportados

El programa detecta el formato por el nombre del fichero (`load_report`):

- **Informe de haz** (`2026-...-6x.csv`, `-15x.csv`, ...): separado por comas, una
  fila de cabecera, fechas en formato `DD/MM/YYYY H:MM:SS`.
- **Measdata** (`Measdata ....csv`): separado por `;`, cabecera en la tercera fila
  (`Worklist;Date;...`) con un subencabezado que se descarta, decimales con coma
  y fechas ISO `YYYY-MM-DD HH:MM:SS`.

En ambos casos, `normalize_dates()` convierte la columna de fecha a `datetime`
(`format="mixed", dayfirst=True`), asi que los dos formatos se unifican y las
fechas invalidas quedan como `NaT`.

## Estructura del proyecto

```
grafi/
├── app.py                 # Frontend interactivo (Streamlit)
├── programa_graficar.py   # Script CLI + libreria de datos/graficas
├── .env                   # Configuracion editable
├── requirements.txt       # Dependencias
└── data/                  # CSVs de los informes
```

### `programa_graficar.py`

Datos y grafica, con las responsabilidades separadas:

- **`load_dotenv(path)`** — carga el `.env` al entorno (parser minimo stdlib).
- **`Config`** — dataclass con la configuracion; `Config.from_env()` la lee del
  entorno.
- **`normalize_dates(df, date_cols)`** — pasa a `datetime` las columnas de fecha
  (nucleo reutilizable, cubre ambos formatos).
- **`load_beam_report` / `load_measdata`** — loaders especificos de cada formato.
- **`load_report(path)`** — elige el loader segun el nombre del fichero.
- **`plot_tolerancia(df, config, titulo)`** — grafica del script (cambio % con
  bandas de tolerancia +/-1 y +/-2, en matplotlib).
- **`PLOTTERS`** — diccionario `nombre -> funcion`. Punto de extension del script:
  para una grafica nueva, anade una funcion y referenciala por `GRAFI_PLOT`.
- **`main()`** — orquesta: lee config, elige fichero (energia o `GRAFI_FILE`),
  carga y grafica.

### `app.py`

Panel Streamlit del TrueBeam 2 que reutiliza los loaders y la `Config` del
script. La logica de datos vive en funciones puras (testeables sin Streamlit):

- **`ENERGIAS`** — mapa `etiqueta -> (sufijo del fichero de haz, MV, FFF)`. Une
  las energias de las dos pruebas (p.ej. `"6FFF" -> ("6xFFF", 6, "Yes")`).
- **`SECCIONES`** — config de cada grafica: titulo, limites de tolerancia y
  lineas a dibujar (MPC centrado en 0 +/-2; CAX centrado en 100, 98-102).
- **`load_mpc(config)`** — arma un DataFrame largo `(Date, energia, valor)` con
  el Output change de los 4 ficheros de haz.
- **`load_quickcheck_cax(config, unidad)`** — igual pero con la columna `CAX.2`
  de Measdata, filtrando `TRUEBEAM-2` y separando por energia (MV + FFF).
- **`preparar_serie(df, columna, rango, regla, func)`** — filtra por rango de
  fechas y, si se indica, agrega por periodo (`resample` de pandas).
- **`estadisticas(y, limites)`** — resumen (nº puntos, media, desviacion, min,
  max y, si hay limites, % de puntos fuera de ellos).
- **`main()`** — construye la interfaz (sidebar + las dos secciones).

Para otra unidad o parametro, se ajustan `ENERGIAS`/`SECCIONES` y los loaders.

## Anadir una grafica nueva al script

```python
def plot_agregado_mensual(df, config, titulo=""):
    ...

PLOTTERS["agregado_mensual"] = plot_agregado_mensual
```

Y se usa con `GRAFI_PLOT=agregado_mensual`.

## Autochequeos

Ninguno necesita levantar la interfaz:

```bash
# Normalizacion de fechas (ambos formatos)
GRAFI_DEMO=1 python programa_graficar.py

# Logica de datos de la app (filtro, agregacion, estadisticas)
python app.py
```

Ambos imprimen `demo OK` si todo va bien.
