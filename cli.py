"""CLI principal de Bicimotos_reporte.

Ejemplo:
    python cli.py reporte --input "C:/.../Reporte bicimotos.xlsx" \
        --out "reportes/bicimotos.html"
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from src import io_loader, matriz, nopagos as nopagos_mod, report_html


def cmd_reporte(args: argparse.Namespace) -> int:
    excel_path = Path(args.input).expanduser().resolve()
    if not excel_path.exists():
        print(f"[ERROR] No existe el archivo: {excel_path}", file=sys.stderr)
        return 2

    out_path = Path(args.out).expanduser().resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"[1/3] Cargando {excel_path.name}...")
    df = io_loader.load_excel(excel_path, sheet_name=args.sheet)
    mov = io_loader.filter_movimientos(df)
    all_placas = sorted(df["placa"].dropna().astype(str).unique())
    placas_sin_mov = sorted(set(all_placas) - set(mov["placa"].astype(str).unique()))
    print(f"      {len(df)} filas totales | {len(mov)} movimientos | "
          f"{len(all_placas)} placas ({len(placas_sin_mov)} sin recorrido)")

    if mov.empty:
        print("[ERROR] No hay movimientos validos en el archivo.", file=sys.stderr)
        return 3

    rango = (
        f"{mov['comienzo_dt'].min().date()} a {mov['comienzo_dt'].max().date()}"
    )

    morosos = None
    if args.nopagos:
        nopagos_path = Path(args.nopagos).expanduser().resolve()
        if not nopagos_path.exists():
            print(f"[ERROR] No existe el archivo de nopagos: {nopagos_path}",
                  file=sys.stderr)
            return 4
        print(f"[2/3] Cargando nopagos {nopagos_path.name}...")
        np_df = nopagos_mod.load_nopagos(nopagos_path)
        cfg = matriz.MatrizConfig()
        km_por_placa: dict[str, float] = {}
        for placa in np_df["placa"].unique():
            m = matriz.build_matriz_km(mov, placa, cfg)
            if not m.empty:
                km_por_placa[placa] = float(m.sum().sum(skipna=True))
        morosos = nopagos_mod.top_morosos(np_df, km_por_placa=km_por_placa, n=10)
        print(f"      {len(np_df)} clientes en mora | "
              f"top renderizado por # cuotas adeudadas")

    print(f"[3/3] Renderizando HTML... (rango: {rango})")
    html = report_html.generar_html(
        mov, rango_label=rango, all_placas=all_placas, morosos=morosos
    )

    print(f"      Escribiendo {out_path}...")
    out_path.write_text(html, encoding="utf-8")

    if morosos:
        print_path = out_path.parent / "imprimir.html"
        html_print = report_html.generar_html_print(morosos, rango_label=rango)
        print_path.write_text(html_print, encoding="utf-8")
        print(f"      Escribiendo {print_path}...")

    print(f"OK -> {out_path}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="bicimotos",
        description="Genera el reporte HTML de recorridos por hora para Bicimotos.",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    rep = sub.add_parser("reporte", help="Genera el HTML ejecutivo")
    rep.add_argument("--input", required=True, help="Ruta al Excel de Bicimotos")
    rep.add_argument("--sheet", default="Report", help="Hoja del Excel (default: Report)")
    rep.add_argument(
        "--out",
        default="reportes/bicimotos_recorridos.html",
        help="Ruta de salida del HTML",
    )
    rep.add_argument(
        "--nopagos",
        default=None,
        help="Ruta opcional al Excel de nopagos. Si se pasa, el Top 10 "
             "muestra clientes con mas cuotas adeudadas (en vez de mas km).",
    )
    rep.set_defaults(func=cmd_reporte)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
