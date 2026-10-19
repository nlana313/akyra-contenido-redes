#!/usr/bin/env python3
"""Trae las métricas de Instagram de las piezas ya publicadas y las deja en `Metricas/`.

Cierra el eslabón que hoy tiene el motor roto: `akyra-aprendizaje` está bien
diseñada pero desde el 15/09/2026 no tiene con qué trabajar, porque las carpetas
`Metricas/` quedaron vacías — nadie cargó los números a mano. Este script los
carga solo, una vez por semana, desde el mismo conector que ya usa el motor.

Corre con 72 h de rezago sobre la publicación: una pieza recién publicada
todavía no acumuló el alcance real, y medirla antes ensucia el histórico con el
que después `akyra-aprendizaje` saca conclusiones.

Escribe un archivo por semana en `Metricas/AAAA-Www_Metricas.md`, con una fila
por pieza y el permalink para poder abrir el post real, más el `media_id` que
`publicar.py` ya había guardado en la cola.

Uso:
    python3 scripts/metricas.py                 # semana que cerró
    python3 scripts/metricas.py 2026-10-19 2026-10-24
"""
import json
import os
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timedelta

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG = json.load(open(os.path.join(RAIZ, "config.json"), encoding="utf-8"))
COLA = os.path.join(RAIZ, "cola.json")
DESTINO = os.path.join(RAIZ, "Metricas")

LECTURA = "https://connectors.windsor.ai/{connector}"
# Campos de Instagram Insights que el motor ya usa (akyra-metricas RS-MET-001).
CAMPOS = ["date", "media_permalink", "media_id", "timestamp", "media_type",
          "media_reach", "media_like_count", "media_comments_count",
          "media_saved", "media_shares", "media_engagement"]
REZAGO_HORAS = 72


def traer(api_key, desde, hasta):
    q = urllib.parse.urlencode({
        "api_key": api_key,
        "fields": ",".join(CAMPOS),
        "date_from": desde,
        "date_to": hasta,
    })
    url = LECTURA.format(connector=CONFIG["cuenta_instagram"]["connector"]) + "?" + q
    with urllib.request.urlopen(url, timeout=120) as r:
        return json.loads(r.read().decode("utf-8")).get("data", [])


def num(v):
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return None


def main():
    api_key = os.environ.get("WINDSOR_API_KEY")
    if not api_key:
        print("ERROR: falta WINDSOR_API_KEY", file=sys.stderr)
        return 1

    if len(sys.argv) >= 3:
        desde, hasta = sys.argv[1], sys.argv[2]
    else:
        hoy = datetime.now()
        hasta = (hoy - timedelta(hours=REZAGO_HORAS)).strftime("%Y-%m-%d")
        desde = (hoy - timedelta(days=10)).strftime("%Y-%m-%d")

    filas = traer(api_key, desde, hasta)
    if not filas:
        print(f"Windsor no devolvió datos para {desde} a {hasta}. "
              "Puede ser que las piezas sean muy recientes o que no haya publicaciones.")
        return 0

    # Cruce con la cola: así cada número queda pegado a la pieza que lo generó
    # (formato, fecha planificada), no solo al permalink suelto de Instagram.
    cola = json.load(open(COLA, encoding="utf-8")) if os.path.exists(COLA) else {"lotes": []}
    por_media = {p["media_id"]: p for lote in cola["lotes"] for p in lote["piezas"]
                 if p.get("media_id")}

    os.makedirs(DESTINO, exist_ok=True)
    semana = datetime.strptime(desde, "%Y-%m-%d").strftime("%Y-W%V")
    salida = os.path.join(DESTINO, f"{semana}_Metricas.md")

    lineas = [
        f"# AKYRA — Métricas de Instagram · {desde} a {hasta}",
        "",
        f"Capturado automáticamente el {datetime.now().strftime('%d/%m/%Y %H:%M')} "
        f"desde Windsor.ai (conector `instagram`, cuenta "
        f"`{CONFIG['cuenta_instagram']['usuario']}`), con {REZAGO_HORAS} h de rezago "
        "sobre la publicación para que el alcance esté asentado.",
        "",
        "| Fecha | Pieza | Formato | Alcance | Likes | Coment. | Guard. | Comp. | "
        "Engagement | Tasa | Permalink |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]

    for f in sorted(filas, key=lambda x: str(x.get("timestamp") or x.get("date") or "")):
        mid = str(f.get("media_id") or "")
        pieza = por_media.get(mid)
        alcance = num(f.get("media_reach"))
        eng = num(f.get("media_engagement"))
        tasa = f"{100 * eng / alcance:.1f}%" if alcance and eng is not None and alcance > 0 else "—"
        lineas.append(
            f"| {str(f.get('date') or '')[:10]} "
            f"| {pieza['id'] if pieza else '(fuera de la cola)'} "
            f"| {pieza['formato'] if pieza else (f.get('media_type') or '')} "
            f"| {alcance if alcance is not None else '—'} "
            f"| {num(f.get('media_like_count')) if f.get('media_like_count') is not None else '—'} "
            f"| {num(f.get('media_comments_count')) if f.get('media_comments_count') is not None else '—'} "
            f"| {num(f.get('media_saved')) if f.get('media_saved') is not None else '—'} "
            f"| {num(f.get('media_shares')) if f.get('media_shares') is not None else '—'} "
            f"| {eng if eng is not None else '—'} "
            f"| {tasa} "
            f"| {f.get('media_permalink') or '—'} |")

    sin_cruce = [f for f in filas if str(f.get("media_id") or "") not in por_media]
    if sin_cruce:
        lineas += ["", f"> **Nota:** {len(sin_cruce)} publicación(es) de este período no "
                       "cruzan con ninguna pieza de `cola.json` — son posts hechos por "
                       "fuera del motor (a mano desde el celular, por ejemplo). Quedan "
                       "igual en la tabla, marcadas como *(fuera de la cola)*, porque "
                       "compiten por el mismo alcance y afectan la lectura del período."]

    lineas += ["", "---", "", "Fuente de este archivo: `scripts/metricas.py` (automático). "
               "Lo consume `akyra-aprendizaje` (RS-APR-001) en el cierre mensual y "
               "`akyra-estrategia-semanal` (Paso 0.7) antes de armar la semana siguiente."]

    open(salida, "w", encoding="utf-8").write("\n".join(lineas) + "\n")
    print(f"Escrito {salida} con {len(filas)} pieza(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
