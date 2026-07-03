"""Grafica informes de control de calidad a partir de CSVs.

Configurable por variables de entorno (prefijo ``GRAFI_``). Separa carga,
normalizacion de fechas y dibujo para poder anadir en el futuro una interfaz
que genere distintas graficas por informe (agregados por fecha, etc.).

Variables de entorno:
    GRAFI_DATA_DIR     Carpeta con los CSV (por defecto: ``data``).
    GRAFI_DATE_FORMAT  Formato de salida de fechas (por defecto: dia/mes/ano hora).
    GRAFI_ENERGIAS     Energias disponibles separadas por coma.
    GRAFI_VALUE_COL    Columna numerica a graficar en los informes de haz.
    GRAFI_DATE_COL     Nombre de la columna de fechas (por defecto: ``Date``).
    GRAFI_PLOT         Grafica a generar (ver PLOTTERS; por defecto ``tolerancia``).
    GRAFI_ENERGIA      Energia a graficar sin preguntar (opcional).
    GRAFI_FILE         Ruta a un CSV concreto; salta el selector de energia.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd


DATE_FORMAT = "%d/%m/%Y %H:%M"  # dia mes ano hora
DEFAULT_VALUE_COL = "BeamGroup/BeamOutputChange [%]"


def load_dotenv(path=".env"):
    """Carga variables de un .env al entorno (sin sobrescribir las ya puestas).

    ponytail: parser minimo (KEY=VALUE, ignora comentarios); si necesitas
    comillas o multilinea, usa python-dotenv.
    """
    env = Path(path)
    if not env.exists():
        return
    for linea in env.read_text(encoding="utf-8").splitlines():
        linea = linea.strip()
        if not linea or linea.startswith("#") or "=" not in linea:
            continue
        clave, _, valor = linea.partition("=")
        os.environ.setdefault(clave.strip(), valor.strip())


@dataclass
class Config:
    """Configuracion leida del entorno."""

    data_dir: Path = Path("data")
    date_format: str = DATE_FORMAT
    date_col: str = "Date"
    value_col: str = DEFAULT_VALUE_COL
    plot: str = "tolerancia"
    energia: str | None = None
    energias: list[str] = field(
        default_factory=lambda: ["6x", "6xFFF", "10xFFF", "15x"]
    )

    @classmethod
    def from_env(cls) -> "Config":
        return cls(
            data_dir=Path(os.environ.get("GRAFI_DATA_DIR", "data")),
            date_format=os.environ.get("GRAFI_DATE_FORMAT", DATE_FORMAT),
            date_col=os.environ.get("GRAFI_DATE_COL", "Date"),
            value_col=os.environ.get("GRAFI_VALUE_COL", DEFAULT_VALUE_COL),
            plot=os.environ.get("GRAFI_PLOT", "tolerancia"),
            energia=os.environ.get("GRAFI_ENERGIA") or None,
            energias=os.environ.get(
                "GRAFI_ENERGIAS", "6x,6xFFF,10xFFF,15x"
            ).split(","),
        )


def normalize_dates(df, date_cols):
    """Convierte a datetime las columnas indicadas (admite dia-primero e ISO).

    ``format="mixed"`` con ``dayfirst=True`` cubre tanto ``DD/MM/YYYY H:MM:SS``
    (informes de haz) como ``YYYY-MM-DD HH:MM:SS`` (Measdata). Las fechas
    invalidas quedan como ``NaT``.
    """
    if isinstance(date_cols, str):
        date_cols = [date_cols]
    for col in date_cols:
        df[col] = pd.to_datetime(
            df[col], dayfirst=True, format="mixed", errors="coerce"
        )
    return df


def load_csv(path, date_cols="Date", sep=",", header=0):
    """Lee un CSV y normaliza sus columnas de fecha a datetime."""
    df = pd.read_csv(path, sep=sep, header=header)
    return normalize_dates(df, date_cols)


def load_beam_report(path, date_col="Date"):
    """Informe de haz: coma, una cabecera, fecha dia-primero."""
    return load_csv(path, date_cols=date_col, sep=",", header=0)


def load_measdata(path):
    """Measdata: punto y coma, cabecera en la fila 1, decimales con coma.

    Cabecera en la fila 2 (``Worklist;Date;...``); la fila 3 es un subencabezado
    (Min/Max/Target/Norm) que se descarta.

    ponytail: solo se normaliza la fecha; el resto de columnas se dejan crudas
    hasta que haga falta graficarlas.
    """
    df = pd.read_csv(path, sep=";", header=2, skiprows=[3], decimal=",")
    return normalize_dates(df, "Date")


def load_report(path):
    """Carga un CSV eligiendo el loader por el nombre del fichero."""
    path = Path(path)
    if path.name.lower().startswith("measdata"):
        return load_measdata(path)
    return load_beam_report(path)


def plot_tolerancia(df, config, titulo=""):
    """Grafica el cambio (%) con bandas de tolerancia +/-1 y +/-2."""
    import matplotlib.pyplot as plt
    from matplotlib.ticker import MaxNLocator

    x = df[config.date_col]
    y = pd.to_numeric(df[config.value_col], errors="coerce")
    mask = x.notna() & y.notna()
    x, y = x[mask], y[mask]

    plt.figure(figsize=(10, 5))
    plt.plot(x, y, marker="o", linestyle="-")

    ax = plt.gca()
    ax.xaxis.set_major_locator(MaxNLocator(3))
    ax.set_ylim(-2.5, 2.5)
    ax.axhspan(2, ax.get_ylim()[1], color="red", alpha=0.3)
    ax.axhspan(ax.get_ylim()[0], -2, color="red", alpha=0.3)
    ax.axhspan(1, ax.get_ylim()[1], color="yellow", alpha=0.3)
    ax.axhspan(ax.get_ylim()[0], -1, color="yellow", alpha=0.3)
    for level, style in ((2, "-"), (-2, "-"), (1, "--"), (-1, "--")):
        plt.axhline(level, color="black", linestyle=style)

    ax.xaxis.set_major_formatter(
        plt.matplotlib.dates.DateFormatter(config.date_format)
    )
    plt.title(titulo)
    plt.xlabel("Fechas")
    plt.ylabel("%")
    plt.grid(False)
    plt.show()


# Registro de graficas: anade aqui nuevas funciones (agregados por fecha, etc.).
PLOTTERS = {
    "tolerancia": plot_tolerancia,
}


def elegir_energia(config):
    """Devuelve la energia de GRAFI_ENERGIA o la pide por consola."""
    if config.energia:
        return config.energia
    print("Energias disponibles:")
    for i, e in enumerate(config.energias):
        print(i, e)
    return config.energias[int(input("Selecciona opcion: "))]


def main():
    config = Config.from_env()
    fichero = os.environ.get("GRAFI_FILE")
    if fichero:
        archivo = Path(fichero)
        titulo = archivo.stem
    else:
        energia = elegir_energia(config)
        archivo = config.data_dir / f"2026-06-29-09-07-55-{energia}.csv"
        titulo = energia

    df = load_report(archivo)
    PLOTTERS[config.plot](df, config, titulo=titulo)


def demo():
    """Autochequeo: la normalizacion cubre ambos formatos de fecha."""
    df = pd.DataFrame({"Date": ["04/09/2020 9:02:27", "2025-12-18 10:41:43", ""]})
    out = normalize_dates(df, "Date")
    assert out["Date"].iloc[0] == pd.Timestamp("2020-09-04 09:02:27")
    assert out["Date"].iloc[1] == pd.Timestamp("2025-12-18 10:41:43")
    assert pd.isna(out["Date"].iloc[2])
    assert out["Date"].iloc[0].strftime(DATE_FORMAT) == "04/09/2020 09:02"
    print("demo OK")


if __name__ == "__main__":
    load_dotenv()
    if os.environ.get("GRAFI_DEMO"):
        demo()
    else:
        main()
