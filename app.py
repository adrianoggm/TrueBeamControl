"""Panel de QA diario del acelerador TrueBeam 2 (Streamlit).

Muestra dos pruebas diarias en un mismo panel:
  - MPC Output change (%): de los CSV de haz, una por energia.
  - QuickCheck CAX (% de nominal): de Measdata, filtrando TRUEBEAM-2.

Ejecutar con:  streamlit run app.py

Los ficheros se releen en cada recarga (sin cache), asi que el panel refleja
el estado actual de la carpeta de datos; el boton "Actualizar" fuerza recarga.

La logica de datos (carga, filtro, agregacion, estadisticas) vive en funciones
puras para poder testearla sin levantar Streamlit; ``demo()`` las autochequea.
"""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from programa_graficar import (
    Config,
    load_beam_report,
    load_dotenv,
    load_measdata,
)


# Energia -> (sufijo del fichero de haz, MV en Measdata, FFF en Measdata).
ENERGIAS = {
    "6X": ("6x", 6, "No"),
    "6FFF": ("6xFFF", 6, "Yes"),
    "10FFF": ("10xFFF", 10, "No"),
    "15": ("15x", 15, "No"),
}

AGREGADOS = {"Punto a punto": None, "Dia": "D", "Semana": "W", "Mes": "ME"}
FUNCS = {"media": "mean", "maximo": "max", "minimo": "min"}

# Cada seccion: titulo, columna origen y lineas de tolerancia (nivel, estilo).
SECCIONES = {
    "mpc": {
        "titulo": "MPC — Output change (%)",
        "eje_y": "output change",
        "limites": (-2.0, 2.0),
        "lineas": [(2, "solid"), (-2, "solid"), (1, "dash"), (-1, "dash"),
                   (0, "dot")],
    },
    "cax": {
        "titulo": "QuickCheck — CAX (% de nominal)",
        "eje_y": "%CAX",
        "limites": (98.0, 102.0),
        "lineas": [(102, "solid"), (98, "solid"), (100, "dot")],
    },
}


def _newest(data_dir, patron):
    """Fichero mas reciente que casa el patron (por nombre), o None."""
    ficheros = sorted(data_dir.glob(patron))
    return ficheros[-1] if ficheros else None


def _vacio():
    return pd.DataFrame({"Date": [], "energia": [], "valor": []})


def load_mpc(config):
    """MPC Output change por energia -> DataFrame largo (Date, energia, valor)."""
    filas = []
    for etiqueta, (sufijo, _, _) in ENERGIAS.items():
        path = _newest(config.data_dir, f"*-{sufijo}.csv")
        if path is None:
            continue
        df = load_beam_report(path, config.date_col)
        if config.value_col not in df.columns:
            continue
        filas.append(pd.DataFrame({
            "Date": df[config.date_col],
            "energia": etiqueta,
            "valor": pd.to_numeric(df[config.value_col], errors="coerce"),
        }))
    if not filas:
        return _vacio()
    return pd.concat(filas).dropna(subset=["Date", "valor"]).sort_values("Date")


def load_quickcheck_cax(config, unidad="TRUEBEAM-2"):
    """CAX de QuickCheck para una unidad -> DataFrame largo por energia."""
    path = _newest(config.data_dir, "Measdata*.csv")
    if path is None:
        return _vacio()
    df = load_measdata(path)
    df = df[df["TreatmentUnit"] == unidad]
    mv = pd.to_numeric(df["Energy[MV/MeV]"], errors="coerce")
    filas = []
    for etiqueta, (_, energia_mv, fff) in ENERGIAS.items():
        sub = df[(mv == energia_mv) & (df["FFF"] == fff)]
        filas.append(pd.DataFrame({
            "Date": sub["Date"],
            "energia": etiqueta,
            "valor": pd.to_numeric(sub["CAX.2"], errors="coerce"),
        }))
    if not filas:
        return _vacio()
    return pd.concat(filas).dropna(subset=["Date", "valor"]).sort_values("Date")


def preparar_serie(df, columna, rango, regla=None, func="mean", date_col="Date"):
    """Filtra por rango de fechas y, opcionalmente, agrega por periodo.

    Devuelve (x, y) listos para graficar. ``regla`` es una regla de resample de
    pandas (D/W/ME) o None para punto a punto.
    """
    ini, fin = rango
    d = df[(df[date_col] >= ini) & (df[date_col] <= fin)]
    d = d[[date_col, columna]].dropna()
    if regla:
        serie = d.set_index(date_col)[columna].resample(regla).agg(func).dropna()
        return serie.index, serie.values
    return d[date_col], d[columna].values


def estadisticas(y, limites=None):
    """Resumen estadistico; si hay limites, % de puntos fuera de ellos."""
    s = pd.Series(y, dtype="float64")
    res = {
        "puntos": int(s.count()),
        "media": s.mean(),
        "desv": s.std(),
        "min": s.min(),
        "max": s.max(),
    }
    if limites is not None and s.count():
        low, high = limites
        res["fuera %"] = ((s < low) | (s > high)).mean() * 100
    return res


def _seccion(df, seccion, energias_sel, rango, regla, func):
    """Dibuja una grafica (una traza por energia) y su tabla de estadisticas."""
    st.subheader(seccion["titulo"])
    if df.empty:
        st.info("Sin datos para esta prueba en la carpeta actual.")
        return

    fig = go.Figure()
    resumen = []
    for energia in energias_sel:
        sub = df[df["energia"] == energia]
        x, y = preparar_serie(sub, "valor", rango, regla, func)
        fig.add_scatter(x=x, y=y, mode="lines+markers", name=energia)
        resumen.append({"Energia": energia,
                        **estadisticas(y, seccion["limites"])})

    for nivel, estilo in seccion["lineas"]:
        color = "gray" if estilo == "dot" else "black"
        fig.add_hline(y=nivel, line_dash=estilo, line_color=color)
    fig.update_layout(xaxis_title="Fecha", yaxis_title=seccion["eje_y"],
                      height=380, margin=dict(t=10))
    # Mostrar el mes (no solo el año) y afinar la etiqueta al hacer zoom.
    fig.update_xaxes(tickformatstops=[
        dict(dtickrange=[None, "M1"], value="%d %b %Y"),
        dict(dtickrange=["M1", None], value="%b %Y"),
    ])
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(pd.DataFrame(resumen).round(3), hide_index=True,
                 use_container_width=True)


def main():
    load_dotenv()
    config = Config.from_env()

    st.set_page_config(page_title="TrueBeam 2 — QA", layout="wide")
    st.title("TrueBeam 2 — Panel de QA diario")

    if st.sidebar.button("🔄 Actualizar datos"):
        st.rerun()

    mpc = load_mpc(config)
    cax = load_quickcheck_cax(config)

    fechas = pd.concat([mpc["Date"], cax["Date"]]).dropna()
    if fechas.empty:
        st.warning(f"No hay datos en {config.data_dir}")
        st.stop()

    etiquetas = list(ENERGIAS)
    sel = st.sidebar.selectbox("Energia", ["Todas"] + etiquetas)
    energias_sel = etiquetas if sel == "Todas" else [sel]

    fmin, fmax = fechas.min().to_pydatetime(), fechas.max().to_pydatetime()
    rango = st.sidebar.slider("Rango de fechas", min_value=fmin, max_value=fmax,
                              value=(fmin, fmax))

    agg = st.sidebar.selectbox("Agregacion", list(AGREGADOS))
    regla = AGREGADOS[agg]
    func = st.sidebar.selectbox("Funcion", list(FUNCS), disabled=regla is None)

    st.sidebar.caption(
        f"MPC: {len(mpc)} medidas\n\nQuickCheck: {len(cax)} medidas"
    )

    _seccion(mpc, SECCIONES["mpc"], energias_sel, rango, regla, FUNCS[func])
    _seccion(cax, SECCIONES["cax"], energias_sel, rango, regla, FUNCS[func])


def demo():
    """Autochequeo de la logica de datos (sin Streamlit)."""
    fechas = pd.to_datetime(
        ["2024-01-01", "2024-01-02", "2024-02-01", "2024-02-02"]
    )
    df = pd.DataFrame({"Date": fechas, "valor": [1.0, 3.0, -1.0, 5.0]})
    rango = (fechas.min().to_pydatetime(), fechas.max().to_pydatetime())

    _, y = preparar_serie(df, "valor", rango)
    assert list(y) == [1.0, 3.0, -1.0, 5.0]

    _, y = preparar_serie(df, "valor", rango, regla="ME", func="mean")
    assert list(y) == [2.0, 2.0]  # media de enero y de febrero

    s = estadisticas([1.0, 3.0, -1.0, 5.0], limites=(-2, 2))
    assert s["puntos"] == 4 and s["max"] == 5.0
    assert s["fuera %"] == 50.0  # 3 y 5 superan |2| -> 2 de 4
    print("demo OK")


# Streamlit ejecuta el fichero como __main__, asi que distinguimos por runtime:
# "streamlit run app.py" -> main(); "python app.py" -> autochequeo.
if st.runtime.exists():
    main()
elif __name__ == "__main__":
    demo()
