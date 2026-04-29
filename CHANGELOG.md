# Changelog

Bitacora de cambios del Informe Bicimotos. Cada entrada describe que se hizo y por que, agrupada por fecha.

## 2026-04-28

### Reporte imprimible

- **Pagina de impresion (`imprimir.html`)** con solo el Top 10 de clientes con mas cuotas adeudadas, optimizada para imprimir o exportar como PDF (boton `window.print()`, fondo blanco, badges de alerta visibles en papel).
- **Link "Imprimir / Ver PDF"** en el header del Top del reporte principal, para abrir la version imprimible.
- **Matrices de recorrido por placa** debajo del Top 10 en el imprimible, una por cada placa con km en el periodo, con la **franja horaria de mayor total semanal resaltada en rojo**.
- **Seccion "Top sin recorrido en el periodo"** que lista las placas del top que no se movieron (no se imprime matriz vacia, queda como evidencia para cobranza).
- **Cache-busting** con `?v=YYYYMMDDHHMMSS` en los dos links cruzados (`index.html` <-> `imprimir.html`), para que el navegador no sirva la version cacheada al navegar entre paginas. El timestamp se renueva en cada regeneracion.

### Dashboard inicial

- **Selector de placa** con todas las motos del periodo (incluye las que no se movieron, con mensaje claro).
- **Matriz dias x franjas horarias** (15 columnas: 05-06 a 19-20) con km prorrateados por movimiento, coloreada como heatmap relativo al maximo de la flota.
- **KPIs por placa**: total km, dias activos / dias del rango, promedio km/dia activo.
- **Top 10 clientes con mas cuotas adeudadas** cruzado con el reporte de no pagos (placa + conductor + deuda + km del periodo). Filas en rojo cuando la moto no registra movimiento (combinacion mas urgente para cobranza).
- **Publicacion en GitHub Pages** desde `docs/index.html`.
