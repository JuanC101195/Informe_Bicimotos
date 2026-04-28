# Informe Bicimotos

Generador de reporte HTML ejecutivo para la flota de Bicimotos. Cruza el reporte semanal del GPS con el reporte de no pagos para producir un dashboard interactivo con la matriz de recorridos por hora de cada moto y un Top 10 de clientes con mas cuotas adeudadas.

>
> **[VER EL ULTIMO REPORTE EN LINEA](https://juanc101195.github.io/Informe_Bicimotos/)**
>

## Que muestra

**Selector de placa con todas las motos del periodo.** Para la placa elegida:

- **Matriz dias x franjas horarias.** Filas = dias con nombre y fecha (`Lunes 20-04-2026`); columnas = franjas de 1 hora desde 05-06 hasta 19-20 (15 columnas); celdas = km recorridos en esa franja, coloreadas como heatmap relativo al maximo de toda la flota.
- **Total km por dia** (columna derecha) y **total km por franja** en toda la semana (fila inferior).
- **KPIs por placa:** total km de la semana, dias activos / dias del rango, promedio km/dia activo.
- **Placas sin recorrido** aparecen igual en el dropdown con un mensaje claro: la moto fue monitoreada pero no se movio en el periodo.

**Top 10 clientes con mas cuotas adeudadas (al final del informe).**

- Ordenado por cantidad de cuotas en mora (columna `# Deuda` del reporte de no pagos).
- Cruza con la matriz de recorridos: muestra los **km del periodo** para cada cliente del top.
- **Filas resaltadas en rojo** cuando el cliente debe pero la moto **no registra movimiento** (parqueada o no usada). Combinacion mas urgente para cobranza.
- Incluye conductor, deuda en pesos y barra visual de distribucion.

## Calculo

Cada movimiento del Excel se prorratea entre las franjas horarias que cruza segun su duracion. Los movimientos fuera de la ventana 05h-20h se descartan completamente.

El cruce con no pagos se hace por placa: la primera columna del Excel de no pagos viene como `BI0028 - KAROLAY GOMEZ NAVAS` y se separa para extraer la placa que enlaza con el reporte de recorridos.

## Uso

```bash
# Crear venv (primera vez)
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt

# Generar el reporte (recorrido + no pagos)
python cli.py reporte \
    --input "ruta/al/Reporte bicimotos.xlsx" \
    --nopagos "ruta/al/nopagos.xlsx" \
    --out "reportes/bicimotos.html"

# Tests
pytest
```

El flag `--nopagos` es opcional. Si no se pasa, el Top 10 se construye por km recorridos (fallback util cuando aun no hay reporte de cobranza disponible).

## Estructura

```text
Informe_Bicimotos/
├── cli.py
├── src/
│   ├── parsers.py       # Parsers para fecha pegada, duracion "11h4min43s", km "0.68Km"
│   ├── io_loader.py     # Carga Excel de recorridos (doble cabecera) y normaliza columnas
│   ├── matriz.py        # Apportioning de km a franjas horarias y ranking por km
│   ├── nopagos.py       # Carga del Excel de no pagos y ranking de morosos
│   └── report_html.py   # Renderer HTML con dropdown, heatmap y Top 10
├── tests/               # 43 tests con pytest
├── docs/
│   └── index.html       # Reporte publicado por GitHub Pages
└── reportes/            # Output local (ignorado por git)
```

## Publicacion

El HTML publicado vive en `docs/index.html` y se sirve con GitHub Pages desde la rama principal. Para regenerarlo despues de cargar nuevos Excel:

```bash
python cli.py reporte \
    --input "Reporte bicimotos.xlsx" \
    --nopagos "nopagos.xlsx" \
    --out "docs/index.html"
git add docs/index.html
git commit -m "docs(pages): actualiza dashboard"
git push
```

## Privacidad

Los Excel de origen (recorridos y no pagos) **nunca se commitean al repo** — el `.gitignore` bloquea `*.xlsx`. Solo se publica el HTML estatico ya renderizado.
