# grafi

Grafica informes de control de calidad de un acelerador a partir de CSVs.
Normaliza las fechas de distintos formatos de exportacion y dibuja el cambio (%)
con bandas de tolerancia. Esta preparado para anadir en el futuro una interfaz
con distintas graficas por informe (agregados por fecha, etc.).

## Requisitos

- Python 3.10+ (se usan anotaciones tipo `str | None`)
- `pandas` y `matplotlib`

```bash
pip install pandas matplotlib
```

## Uso rapido

```bash
python programa_graficar.py
```

Muestra las energias disponibles, eliges una y abre la grafica de ese informe
de haz.

Para graficar un CSV concreto (cualquiera de los dos formatos), sin pasar por el
selector:

```bash
GRAFI_FILE="data/Measdata 2026-07-03 12'31'42.csv" python programa_graficar.py
```

En Windows (PowerShell):

```powershell
$env:GRAFI_FILE = "data\Measdata 2026-07-03 12'31'42.csv"; python programa_graficar.py
```

## Configuracion por variables de entorno

Todo se configura con variables `GRAFI_*` (todas tienen valor por defecto):

| Variable | Por defecto | Que hace |
|----------|-------------|----------|
| `GRAFI_DATA_DIR` | `data` | Carpeta donde estan los CSV. |
| `GRAFI_DATE_FORMAT` | `%d/%m/%Y %H:%M` | Formato de fecha mostrado en el eje X (dia/mes/ano hora). |
| `GRAFI_DATE_COL` | `Date` | Nombre de la columna de fechas. |
| `GRAFI_VALUE_COL` | `BeamGroup/BeamOutputChange [%]` | Columna numerica a graficar. |
| `GRAFI_PLOT` | `tolerancia` | Que grafica generar (ver `PLOTTERS`). |
| `GRAFI_ENERGIA` | — | Energia a graficar sin preguntar (p.ej. `6x`). |
| `GRAFI_ENERGIAS` | `6x,6xFFF,10xFFF,15x` | Lista de energias del selector. |
| `GRAFI_FILE` | — | Ruta a un CSV concreto; salta el selector de energia. |
| `GRAFI_DEMO` | — | Si esta definida, ejecuta el autochequeo en vez de graficar. |

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

## Estructura del codigo

Todo esta en `programa_graficar.py`, con las responsabilidades separadas:

- **`Config`** — dataclass con la configuracion; `Config.from_env()` la lee del
  entorno.
- **`normalize_dates(df, date_cols)`** — pasa a `datetime` las columnas de fecha
  (nucleo reutilizable, cubre ambos formatos).
- **`load_beam_report` / `load_measdata`** — loaders especificos de cada formato.
- **`load_report(path)`** — elige el loader segun el nombre del fichero.
- **`plot_tolerancia(df, config, titulo)`** — la grafica actual (cambio % con
  bandas de tolerancia +/-1 y +/-2).
- **`PLOTTERS`** — diccionario `nombre -> funcion`. Punto de extension: para una
  grafica nueva, anade una funcion y referenciala por `GRAFI_PLOT`, sin tocar el
  resto.
- **`main()`** — orquesta: lee config, elige fichero (energia o `GRAFI_FILE`),
  carga y grafica.

## Anadir una grafica nueva

```python
def plot_agregado_mensual(df, config, titulo=""):
    ...

PLOTTERS["agregado_mensual"] = plot_agregado_mensual
```

Y se usa con `GRAFI_PLOT=agregado_mensual`.

## Autochequeo

```bash
GRAFI_DEMO=1 python programa_graficar.py
```

Comprueba que la normalizacion de fechas funciona para ambos formatos e imprime
`demo OK`.
