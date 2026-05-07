"""Renderer del HTML ejecutivo con selector de placa y matriz dias x horas."""

from __future__ import annotations

from datetime import date, datetime, timezone

import pandas as pd

from . import matriz as matriz_mod


def _version_tag() -> str:
    """Timestamp UTC para cache-busting de los links cruzados index <-> imprimir.

    Se incrusta como ``?v=YYYYMMDDHHMMSS`` en cada regeneracion para que el
    browser no sirva la version cacheada al navegar entre paginas.
    """
    return datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")

CSS = """
:root{
  --bg:#0f172a;--panel:#1e293b;--text:#e2e8f0;--muted:#94a3b8;
  --accent:#38bdf8;--border:#334155;
}
*{box-sizing:border-box}
body{margin:0;font-family:-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,sans-serif;
  background:var(--bg);color:var(--text);line-height:1.4}
header{padding:24px 32px;border-bottom:1px solid var(--border);background:#0b1220}
header h1{margin:0 0 4px 0;font-size:22px;font-weight:600}
header .sub{color:var(--muted);font-size:13px}
main{padding:24px 32px;max-width:1400px;margin:0 auto}
.controls{display:flex;gap:16px;align-items:center;margin-bottom:20px;flex-wrap:wrap}
.controls label{font-size:13px;color:var(--muted)}
.controls select{
  padding:8px 12px;background:var(--panel);color:var(--text);
  border:1px solid var(--border);border-radius:6px;font-size:14px;min-width:160px
}
.kpis{display:flex;gap:12px;margin-bottom:20px;flex-wrap:wrap}
.kpi{background:var(--panel);border:1px solid var(--border);border-radius:8px;
  padding:12px 16px;flex:1;min-width:140px}
.kpi .label{color:var(--muted);font-size:12px;text-transform:uppercase;letter-spacing:.5px}
.kpi .value{font-size:24px;font-weight:600;color:var(--accent);margin-top:4px}
.matriz-wrap{background:var(--panel);border:1px solid var(--border);
  border-radius:8px;padding:16px;overflow-x:auto}
table.matriz{border-collapse:collapse;width:100%;font-size:12px}
table.matriz th,table.matriz td{
  padding:6px 8px;text-align:center;border:1px solid var(--border);
  white-space:nowrap
}
table.matriz th{background:#0b1220;font-weight:600;color:var(--muted);font-size:11px}
table.matriz td.dia{text-align:left;font-weight:500;background:#0b1220;
  color:var(--text);min-width:160px}
table.matriz td.total,table.matriz th.total{
  background:#0b1220;font-weight:600;color:var(--accent)
}
table.matriz tfoot td{background:#0b1220;font-weight:600;color:var(--accent)}
table.matriz th.hl-col,table.matriz td.hl-col{
  background:#ef4444 !important;color:#fff !important}
.empty{color:#475569}
.placa-section{display:none}
.placa-section.active{display:block}
.top-section{margin-top:32px;background:var(--panel);border:1px solid var(--border);
  border-radius:8px;padding:20px}
.top-section h2{margin:0 0 4px 0;font-size:18px;font-weight:600}
.top-section .sub{color:var(--muted);font-size:12px;margin-bottom:14px}
table.top{border-collapse:collapse;width:100%;font-size:13px}
table.top th,table.top td{padding:8px 12px;border-bottom:1px solid var(--border);
  text-align:left}
table.top th{color:var(--muted);font-size:11px;text-transform:uppercase;
  letter-spacing:.5px;font-weight:600}
table.top td.rank{font-weight:600;color:var(--accent);width:40px;text-align:center}
table.top td.placa{font-weight:500}
table.top td.num{text-align:right;font-variant-numeric:tabular-nums;width:120px}
.bar{position:relative;height:6px;background:#0b1220;border-radius:3px;
  overflow:hidden;width:100%;min-width:80px}
.bar > span{display:block;height:100%;background:linear-gradient(90deg,#0ea5e9,#ef4444)}
table.top tr.row-no-km{background:rgba(239,68,68,0.10)}
table.top tr.row-no-km td{border-bottom-color:rgba(239,68,68,0.25)}
.badge-alert{display:inline-block;padding:2px 8px;border-radius:10px;
  background:rgba(239,68,68,0.20);color:#fca5a5;font-size:11px;font-weight:600;
  letter-spacing:.3px;white-space:nowrap}
.top-header{display:flex;justify-content:space-between;align-items:center;
  flex-wrap:wrap;gap:12px;margin-bottom:4px}
.top-header h2{margin:0}
.print-link{padding:8px 14px;background:rgba(56,189,248,0.15);
  color:var(--accent);text-decoration:none;border-radius:6px;
  border:1px solid rgba(56,189,248,0.30);font-size:13px;font-weight:500;
  white-space:nowrap}
.print-link:hover{background:rgba(56,189,248,0.25)}
footer{padding:20px 32px;color:var(--muted);font-size:12px;text-align:center;
  border-top:1px solid var(--border);margin-top:32px}
"""

JS = """
function selectPlaca(placa){
  document.querySelectorAll('.placa-section').forEach(function(el){
    el.classList.remove('active');
  });
  var target = document.getElementById('placa-' + placa);
  if(target){ target.classList.add('active'); }
}
document.addEventListener('DOMContentLoaded', function(){
  var sel = document.getElementById('placa-select');
  sel.addEventListener('change', function(){ selectPlaca(this.value); });
  selectPlaca(sel.value);
});
"""


def _color_for_km(km: float, vmax: float) -> str:
    """Devuelve un background-color CSS proporcional al km de la celda."""
    if vmax <= 0 or pd.isna(km) or km <= 0:
        return ""
    intensity = min(km / vmax, 1.0)
    r = int(15 + (239 - 15) * intensity)
    g = int(23 + (68 - 23) * intensity)
    b = int(42 + (68 - 42) * intensity)
    text_color = "#fff" if intensity > 0.5 else "var(--text)"
    return f"background:rgb({r},{g},{b});color:{text_color};"


def _franja_pico(matriz: pd.DataFrame, franjas: list[str]) -> str | None:
    """Devuelve la franja horaria con mayor total de km en la semana, o None."""
    totales = {f: float(matriz[f].sum(skipna=True)) for f in franjas}
    if not any(v > 0 for v in totales.values()):
        return None
    return max(totales, key=totales.get)


def _render_matriz_table(
    matriz: pd.DataFrame,
    vmax_global: float,
    highlight_franja: str | None = None,
) -> str:
    cfg = matriz_mod.MatrizConfig()
    franjas = [cfg.franja_label(h) for h in cfg.franjas()]

    if matriz.empty:
        return (
            "<div class='matriz-wrap'>"
            "<p class='empty' style='margin:0;padding:20px;text-align:center'>"
            "Esta placa no registra recorridos en el periodo."
            "</p></div>"
        )

    def _hl(f: str) -> str:
        return " hl-col" if highlight_franja and f == highlight_franja else ""

    head = "<tr><th class='dia'>Dia</th>"
    for f in franjas:
        head += f"<th class='franja{_hl(f)}'>{f}</th>"
    head += "<th class='total'>Total km</th></tr>"

    body_rows = []
    total_general = 0.0
    for fecha in matriz.index:
        label = matriz_mod.fecha_label(fecha)
        row = f"<tr><td class='dia'>{label}</td>"
        fila_total = 0.0
        fila_tiene_dato = False
        for f in franjas:
            v = matriz.at[fecha, f]
            hl = _hl(f)
            if pd.isna(v) or v <= 0:
                row += f"<td class='empty{hl}'>&mdash;</td>"
            else:
                fila_tiene_dato = True
                fila_total += float(v)
                style = _color_for_km(float(v), vmax_global)
                cls = f" class='{hl.strip()}'" if hl else ""
                row += f"<td{cls} style='{style}'>{v:.2f}</td>"
        if fila_tiene_dato:
            row += f"<td class='total'>{fila_total:.2f}</td>"
        else:
            row += "<td class='empty'>&mdash;</td>"
        row += "</tr>"
        body_rows.append(row)
        total_general += fila_total

    foot = "<tr><td class='dia'>Total semana</td>"
    for f in franjas:
        col_total = float(matriz[f].sum(skipna=True))
        hl = _hl(f)
        if col_total > 0:
            cls = f" class='{hl.strip()}'" if hl else ""
            foot += f"<td{cls}>{col_total:.2f}</td>"
        else:
            foot += f"<td class='empty{hl}'>&mdash;</td>"
    foot += f"<td class='total'>{total_general:.2f}</td></tr>"

    return (
        "<div class='matriz-wrap'><table class='matriz'>"
        f"<thead>{head}</thead>"
        f"<tbody>{''.join(body_rows)}</tbody>"
        f"<tfoot>{foot}</tfoot>"
        "</table></div>"
    )


def _render_kpis(resumen: dict) -> str:
    return (
        "<div class='kpis'>"
        f"<div class='kpi'><div class='label'>Total km</div>"
        f"<div class='value'>{resumen['total_km']:.2f}</div></div>"
        f"<div class='kpi'><div class='label'>Dias activos</div>"
        f"<div class='value'>{resumen['dias_activos']} / {resumen['dias_totales']}</div></div>"
        f"<div class='kpi'><div class='label'>Promedio km / dia activo</div>"
        f"<div class='value'>{resumen['promedio_dia']:.2f}</div></div>"
        "</div>"
    )


def _render_top_placas(top: list[dict]) -> str:
    if not top:
        return ""
    max_km = top[0]["total_km"] or 1.0
    rows = []
    for i, t in enumerate(top, start=1):
        pct = min(t["total_km"] / max_km, 1.0) * 100
        rows.append(
            f"<tr>"
            f"<td class='rank'>{i}</td>"
            f"<td class='placa'>{t['placa']}</td>"
            f"<td class='num'>{t['total_km']:.2f} km</td>"
            f"<td><div class='bar'><span style='width:{pct:.1f}%'></span></div></td>"
            f"<td class='num'>{t['dias_activos']}</td>"
            f"<td class='num'>{t['promedio_dia']:.2f} km</td>"
            f"</tr>"
        )
    return (
        "<section class='top-section'>"
        "<h2>Top 10 placas con mas km recorridos</h2>"
        "<div class='sub'>Ordenadas por km totales en la ventana 5h-20h del periodo.</div>"
        "<table class='top'>"
        "<thead><tr>"
        "<th>#</th><th>Placa</th><th>Total km</th>"
        "<th>Distribucion</th><th>Dias act.</th><th>Prom/dia</th>"
        "</tr></thead>"
        f"<tbody>{''.join(rows)}</tbody>"
        "</table></section>"
    )


def _fmt_money(v: float) -> str:
    """Formato $1.234 con separador de miles, sin decimales."""
    return f"${v:,.0f}".replace(",", ".")


def _render_top_morosos(top: list[dict], print_url: str | None = None) -> str:
    if not top:
        return ""
    max_cuotas = top[0]["num_cuotas"] or 1.0
    rows = []
    sin_recorrido = 0
    for i, t in enumerate(top, start=1):
        pct = min(t["num_cuotas"] / max_cuotas, 1.0) * 100
        km = t.get("km_recorridos")
        if km is None:
            row_class = " class='row-no-km'"
            km_cell = "<span class='badge-alert'>Sin recorrido</span>"
            sin_recorrido += 1
        else:
            row_class = ""
            km_cell = f"{km:.2f} km"
        rows.append(
            f"<tr{row_class}>"
            f"<td class='rank'>{i}</td>"
            f"<td class='placa'>{t['placa']}</td>"
            f"<td>{t['conductor']}</td>"
            f"<td class='num'>{t['num_cuotas']:.1f}</td>"
            f"<td><div class='bar'><span style='width:{pct:.1f}%'></span></div></td>"
            f"<td class='num'>{_fmt_money(t['deuda'])}</td>"
            f"<td class='num'>{km_cell}</td>"
            f"</tr>"
        )
    leyenda = ""
    if sin_recorrido:
        leyenda = (
            f" <span class='badge-alert' style='margin-left:8px'>"
            f"{sin_recorrido} sin recorrido</span>"
            "<div class='sub' style='margin-top:8px'>"
            "Filas marcadas: cliente debe pero la moto no registra movimiento "
            "en el periodo (parqueada o no usada)."
            "</div>"
        )
    print_btn = ""
    if print_url:
        print_btn = (
            f"<a href='{print_url}' class='print-link no-print'>"
            "Imprimir / Ver PDF &rarr;</a>"
        )
    return (
        "<section class='top-section'>"
        "<div class='top-header'>"
        f"<h2>Top 10 clientes con mas cuotas adeudadas{leyenda}</h2>"
        f"{print_btn}"
        "</div>"
        "<div class='sub'>Ordenados por cantidad de cuotas en mora. "
        "Km del periodo cruzado con el reporte de recorridos.</div>"
        "<table class='top'>"
        "<thead><tr>"
        "<th>#</th><th>Placa</th><th>Conductor</th>"
        "<th># Cuotas</th><th>Distribucion</th>"
        "<th>Deuda</th><th>Km periodo</th>"
        "</tr></thead>"
        f"<tbody>{''.join(rows)}</tbody>"
        "</table></section>"
    )


def _render_placa_section(
    placa: str, matriz: pd.DataFrame, vmax_global: float
) -> str:
    resumen = matriz_mod.resumen_placa(matriz)
    return (
        f"<section class='placa-section' id='placa-{placa}'>"
        f"{_render_kpis(resumen)}"
        f"{_render_matriz_table(matriz, vmax_global)}"
        "</section>"
    )


def generar_html(
    movimientos: pd.DataFrame,
    rango_label: str = "",
    all_placas: list[str] | None = None,
    morosos: list[dict] | None = None,
) -> str:
    """Genera el HTML completo, una seccion por placa, con dropdown.

    ``all_placas`` permite incluir en el dropdown placas que no se movieron
    en el periodo (aparecen con la matriz vacia). Si es ``None``, se usan
    solo las placas con movimientos.

    ``morosos`` activa el Top 10 por cuotas adeudadas (ya pre-calculado en
    el CLI con ``nopagos.top_morosos``). Si es ``None``, se renderiza el
    Top 10 por km recorridos como fallback.
    """
    cfg = matriz_mod.MatrizConfig()
    if all_placas is not None:
        placas = sorted(set(all_placas))
    else:
        placas = sorted(movimientos["placa"].dropna().unique())

    matrices: dict[str, pd.DataFrame] = {}
    vmax_global = 0.0
    for placa in placas:
        m = matriz_mod.build_matriz_km(movimientos, placa, cfg)
        matrices[placa] = m
        if not m.empty:
            local_max = float(m.max().max(skipna=True))
            if local_max > vmax_global:
                vmax_global = local_max

    options = "".join(f"<option value='{p}'>{p}</option>" for p in placas)
    sections = "".join(
        _render_placa_section(p, matrices[p], vmax_global) for p in placas
    )

    if morosos is not None:
        top_html = _render_top_morosos(
            morosos, print_url=f"imprimir.html?v={_version_tag()}"
        )
    else:
        top = matriz_mod.top_placas(movimientos, cfg, n=10)
        top_html = _render_top_placas(top)

    sub = f"Recorrido por hora ({cfg.hora_inicio}h-{cfg.hora_fin}h)"
    if rango_label:
        sub += f" &middot; {rango_label}"

    return f"""<!doctype html>
<html lang='es'><head><meta charset='utf-8'>
<title>Bicimotos - Recorridos por hora</title>
<style>{CSS}</style></head>
<body>
<header>
  <h1>Bicimotos &mdash; Matriz de recorridos por hora</h1>
  <div class='sub'>{sub}</div>
</header>
<main>
  <div class='controls'>
    <label for='placa-select'>Placa</label>
    <select id='placa-select'>{options}</select>
  </div>
  {sections}
  {top_html}
</main>
<footer>Generado automaticamente desde el Excel de Bicimotos.</footer>
<script>{JS}</script>
</body></html>"""


PRINT_CSS = """
.print-actions{display:flex;gap:12px;align-items:center;margin-bottom:20px}
.print-btn{padding:10px 18px;background:var(--accent);color:#0b1220;
  border:none;border-radius:6px;font-size:14px;font-weight:600;cursor:pointer}
.print-btn:hover{filter:brightness(1.1)}
.print-actions a{color:var(--accent);font-size:13px;text-decoration:none}
.print-actions a:hover{text-decoration:underline}
.placa-print{margin-top:20px}
.placa-print h3{margin:0 0 8px 0;font-size:15px;font-weight:600;color:var(--text)}
.matrices-print-header{margin-top:32px}
.matrices-print-header h2{margin:0 0 4px 0;font-size:18px;font-weight:600}
.matrices-print-header .sub{color:var(--muted);font-size:12px;margin-bottom:8px}
.sin-recorrido-section{margin-top:24px;background:var(--panel);
  border:1px solid var(--border);border-radius:8px;padding:16px}
.sin-recorrido-section h2{margin:0 0 4px 0;font-size:16px;font-weight:600}
.sin-recorrido-section .sub{color:var(--muted);font-size:12px;margin-bottom:10px}
.sin-recorrido-section ul{margin:0;padding-left:20px;color:var(--text);font-size:13px}
.sin-recorrido-section li{margin:2px 0}
@media print{
  body{background:#fff;color:#000}
  header{background:#fff;color:#000;border-bottom:1px solid #ccc}
  header .sub{color:#666}
  main{padding:0;max-width:none}
  .no-print{display:none !important}
  .top-section{background:#fff;border:none;padding:0;margin-top:0}
  .top-section h2{color:#000}
  .top-section .sub{color:#666}
  table.top th{background:#f5f5f5;color:#333;border-bottom:1px solid #999}
  table.top td{border-bottom-color:#ddd;color:#000}
  table.top td.rank,table.top td.num{color:#000}
  .empty{color:#999}
  table.top tr.row-no-km{background:#fee !important;
    -webkit-print-color-adjust:exact;print-color-adjust:exact}
  .badge-alert{background:#fee !important;color:#c33 !important;
    -webkit-print-color-adjust:exact;print-color-adjust:exact}
  .bar{background:#eee !important;-webkit-print-color-adjust:exact;
    print-color-adjust:exact}
  .bar > span{-webkit-print-color-adjust:exact;print-color-adjust:exact}
  .matrices-print-header h2{color:#000}
  .matrices-print-header .sub{color:#666}
  .placa-print{page-break-inside:avoid;margin-top:16px}
  .placa-print h3{color:#000}
  .matriz-wrap{background:#fff;border:1px solid #ccc;padding:6px}
  table.matriz th{background:#f5f5f5 !important;color:#333 !important;
    border:1px solid #ccc;-webkit-print-color-adjust:exact;
    print-color-adjust:exact}
  table.matriz td{border:1px solid #ddd;color:#000 !important;
    background:transparent !important}
  table.matriz td[style]{background:transparent !important;color:#000 !important}
  table.matriz td.dia{background:#f5f5f5 !important;color:#000 !important;
    font-weight:600;-webkit-print-color-adjust:exact;print-color-adjust:exact}
  table.matriz td.total,table.matriz th.total{background:#f5f5f5 !important;
    color:#0369a1 !important;-webkit-print-color-adjust:exact;
    print-color-adjust:exact}
  table.matriz tfoot td{background:#f5f5f5 !important;color:#0369a1 !important;
    -webkit-print-color-adjust:exact;print-color-adjust:exact}
  table.matriz th.hl-col,table.matriz td.hl-col{
    background:#ef4444 !important;color:#fff !important;
    -webkit-print-color-adjust:exact;print-color-adjust:exact}
  .sin-recorrido-section{background:#fff;border:1px solid #ccc;
    page-break-inside:avoid}
  .sin-recorrido-section h2{color:#000}
  .sin-recorrido-section .sub{color:#666}
  .sin-recorrido-section li{color:#000}
  footer{display:none}
}
"""


def _render_matrices_print(
    morosos: list[dict],
    matrices: dict[str, pd.DataFrame],
    vmax: float,
) -> str:
    """Bloques de matriz por placa del top + seccion de placas sin recorrido."""
    cfg = matriz_mod.MatrizConfig()
    franjas = [cfg.franja_label(h) for h in cfg.franjas()]

    bloques: list[str] = []
    sin_rec: list[dict] = []
    for t in morosos:
        m = matrices.get(t["placa"])
        if m is None or m.empty:
            sin_rec.append(t)
            continue
        pico = _franja_pico(m, franjas)
        bloques.append(
            "<article class='placa-print'>"
            f"<h3>{t['placa']} &mdash; {t['conductor']}</h3>"
            f"{_render_matriz_table(m, vmax, highlight_franja=pico)}"
            "</article>"
        )

    out = ""
    if bloques:
        out += (
            "<section class='matrices-print-header'>"
            "<h2>Matrices de recorrido (Top 10 con km en el periodo)</h2>"
            "<div class='sub'>Franja con mayor total semanal en rojo.</div>"
            f"{''.join(bloques)}"
            "</section>"
        )
    if sin_rec:
        items = "".join(
            f"<li>{t['placa']} &mdash; {t['conductor']}</li>" for t in sin_rec
        )
        out += (
            "<section class='sin-recorrido-section'>"
            "<h2>Top sin recorrido en el periodo</h2>"
            "<div class='sub'>Estas placas estan en el top de morosos pero no se "
            "muestra matriz porque no registran km en el periodo consultado.</div>"
            f"<ul>{items}</ul>"
            "</section>"
        )
    return out


def generar_html_print(
    morosos: list[dict] | None,
    rango_label: str = "",
    matrices: dict[str, pd.DataFrame] | None = None,
    vmax: float = 0.0,
    back_url: str = "index.html",
) -> str:
    """HTML minimo con Top 10 morosos + matrices por placa, optimizado para PDF.

    Reusa el mismo renderer ``_render_top_morosos`` que el reporte principal.
    Si ``matrices`` viene (dict ``placa -> DataFrame``), debajo del top se
    renderiza una matriz por placa con la franja horaria de mayor total
    semanal resaltada en rojo. Las placas del top sin recorrido se listan
    aparte para no imprimir matrices vacias.
    """
    if not morosos:
        body = (
            "<p style='padding:24px;color:var(--muted)'>"
            "No hay datos de morosos para imprimir."
            "</p>"
        )
    else:
        body = _render_top_morosos(morosos)
        if matrices is not None:
            body += _render_matrices_print(morosos, matrices, vmax)

    sub = "Vista para impresion / PDF"
    if rango_label:
        sub += f" &middot; {rango_label}"

    actions = (
        "<div class='print-actions no-print'>"
        "<button class='print-btn' onclick='window.print()'>Imprimir / Guardar PDF</button>"
        f"<a href='{back_url}?v={_version_tag()}'>&larr; Volver al reporte completo</a>"
        "</div>"
    )

    return f"""<!doctype html>
<html lang='es'><head><meta charset='utf-8'>
<title>Bicimotos - Top 10 morosos (imprimible)</title>
<style>{CSS}{PRINT_CSS}</style></head>
<body>
<header>
  <h1>Bicimotos &mdash; Top 10 clientes con mas cuotas adeudadas</h1>
  <div class='sub'>{sub}</div>
</header>
<main>
  {actions}
  {body}
</main>
</body></html>"""
