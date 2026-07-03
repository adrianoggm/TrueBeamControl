import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator


energias_disponibles = ["6x", "6xFFF", "10xFFF", "15x"]

#Seleccionar energías
print("Energías disponibles:")
for i, e in enumerate(energias_disponibles):
    print(i, e)

idx = int(input("Selecciona opción: "))
energia = energias_disponibles[idx]
archivo = rf"C:\Users\alsansanc\Desktop\2026-06-29-09-07-55-{energia}.csv"


datos = pd.read_csv(archivo, header=None)


x = datos.iloc[:, 0]
y = pd.to_numeric(datos.iloc[:, 2], errors="coerce")

#Para eliminar filas en blanco
mask = x.notna() & y.notna()
x = x[mask]
y = y[mask]


plt.figure(figsize=(10, 5))
plt.plot(x, y, marker='o', linestyle='-')

#Para no poner todas las fechas
ax = plt.gca()
ax.xaxis.set_major_locator(MaxNLocator(3))  

#Para los colores de la tolerancia
ax.set_ylim(-2.5, +2.5)
ax.axhspan(2, ax.get_ylim()[1], color='red', alpha=0.3)
ax.axhspan(ax.get_ylim()[0], -2, color='red', alpha=0.3)
ax.axhspan(1, ax.get_ylim()[1], color='yellow', alpha=0.3)
ax.axhspan(ax.get_ylim()[0], -1, color='yellow', alpha=0.3)
plt.axhline(2, color="black", linestyle="-")
plt.axhline(-2, color="black", linestyle="-")
plt.axhline(1, color="black", linestyle="--")
plt.axhline(-1, color="black", linestyle="--")


plt.title(energia)
plt.xlabel("Fechas")
plt.ylabel("%")
plt.grid(False)

plt.show()