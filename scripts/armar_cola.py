#!/usr/bin/env python3
"""Arma `cola.json` a partir de las carpetas de piezas generadas por el motor.

Corre en la Mac, después de la corrida semanal de `akyra-estrategia-semanal` y
antes de la aprobación humana. Hace tres cosas:

  1. Lee cada carpeta `AAAA-MM-DD/` del repo, detecta qué formato es cada pieza
     por los archivos que hay adentro, y saca el caption del `pieza.md`.
  2. Convierte los PNG a JPEG en `publicar/`, porque Instagram (vía Windsor)
     solo acepta JPEG y los renders del motor salen en PNG.
  3. Escribe/actualiza `cola.json`, que es lo único que el worker de la nube
     mira para saber qué publicar y cuándo.

El lote nace con `"aprobado": false`. El worker NO publica nada de un lote sin
aprobar — es la compuerta humana de la regla 7 de `akyra-branding-base`.

Uso:
    python3 scripts/armar_cola.py                 # toma las carpetas futuras
    python3 scripts/armar_cola.py 2026-10-19      # una fecha puntual
    python3 scripts/armar_cola.py --rehacer       # recalcula el lote entero
"""
import json
import os
import re
import subprocess
import sys
from datetime import datetime

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG = json.load(open(os.path.join(RAIZ, "config.json"), encoding="utf-8"))
COLA = os.path.join(RAIZ, "cola.json")

DIA_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
SLIDE_RE = re.compile(r"^Slide (\d+)-\d+\.png$", re.IGNORECASE)


def carpetas_de_piezas():
    """Carpetas `AAAA-MM-DD/` en la raíz, ordenadas. `publicado/` queda afuera."""
    return sorted(d for d in os.listdir(RAIZ)
                  if DIA_RE.match(d) and os.path.isdir(os.path.join(RAIZ, d)))


def subcarpeta_motor(dia_dir):
    """Las piezas viven en `v2_motor/` (o directamente en la carpeta del día)."""
    sub = os.path.join(dia_dir, "v2_motor")
    return sub if os.path.isdir(sub) else dia_dir


def leer_caption(ruta_md):
    """Saca el caption del `pieza.md`: el bloque "Copy Instagram" + los hashtags.

    El `pieza.md` está escrito para que lo lea una persona (tabla de slides,
    fuentes, notas de producción). Lo único que va al post es el copy y los
    hashtags, así que el resto se descarta acá en vez de pedirle a quien escribe
    la pieza que mantenga el texto duplicado en dos formatos.
    """
    if not os.path.exists(ruta_md):
        return None, "no existe pieza.md"
    txt = open(ruta_md, encoding="utf-8").read()

    m = re.search(r"^##\s*Copy Instagram.*?$(.*?)(?=^\*\*Hashtags|^##\s)", txt,
                  re.MULTILINE | re.DOTALL)
    if not m:
        return None, "no se encontró la sección 'Copy Instagram'"
    copy = m.group(1).strip()

    h = re.search(r"^\*\*Hashtags[^:]*:\*\*\s*(.+?)$", txt, re.MULTILINE)
    hashtags = h.group(1).strip() if h else ""

    caption = f"{copy}\n\n{hashtags}".strip()
    tope = CONFIG["reglas_duras"]["caption_max_caracteres"]
    if len(caption) > tope:
        return None, f"caption de {len(caption)} caracteres (tope {tope})"
    return caption, None


def a_jpeg(origen, destino):
    """PNG -> JPEG con `sips` (viene con macOS, no agrega dependencias).

    Instagram rechaza PNG en la API de publicación; el motor renderiza en PNG
    porque es lo correcto para archivar la pieza sin pérdida. La conversión vive
    acá y no en `render.py` para que el archivo maestro siga siendo el PNG.
    """
    os.makedirs(os.path.dirname(destino), exist_ok=True)
    subprocess.run(["sips", "-s", "format", "jpeg", "-s", "formatOptions", "92",
                    origen, "--out", destino],
                   check=True, capture_output=True)
    mb = os.path.getsize(destino) / 1024 / 1024
    if mb > 8:
        raise RuntimeError(f"{destino} pesa {mb:.1f} MB — Instagram acepta hasta 8 MB")
    return os.path.relpath(destino, RAIZ)


def detectar_piezas(dia):
    """Devuelve la lista de piezas de ese día (puede ser más de una: feed + historia)."""
    carpeta = subcarpeta_motor(os.path.join(RAIZ, dia))
    archivos = sorted(os.listdir(carpeta))
    caption, err_caption = leer_caption(os.path.join(carpeta, "pieza.md"))
    piezas = []

    slides = sorted(((int(SLIDE_RE.match(a).group(1)), a) for a in archivos if SLIDE_RE.match(a)))
    videos = [a for a in archivos if a.lower().endswith((".mp4", ".mov"))
              and not a.lower().startswith("historia")]
    historias = [a for a in archivos if a.lower().startswith("historia")
                 and a.lower().endswith((".png", ".jpg", ".jpeg", ".mp4"))]

    if slides:
        assets = [a_jpeg(os.path.join(carpeta, nombre),
                         os.path.join(RAIZ, "publicar", dia, f"{n:02d}.jpg"))
                  for n, nombre in slides]
        piezas.append(nueva_pieza(dia, "carrusel", assets, caption, err_caption))

    for v in videos:
        piezas.append(nueva_pieza(dia, "reel", [os.path.relpath(os.path.join(carpeta, v), RAIZ)],
                                  caption, err_caption))

    for h in historias:
        if h.lower().endswith(".png"):
            asset = a_jpeg(os.path.join(carpeta, h),
                           os.path.join(RAIZ, "publicar", dia, "historia.jpg"))
        else:
            asset = os.path.relpath(os.path.join(carpeta, h), RAIZ)
        # Instagram no acepta caption en historias.
        piezas.append(nueva_pieza(dia, "historia", [asset], None, None))

    return piezas


def nueva_pieza(dia, formato, assets, caption, err_caption):
    hora = CONFIG["horarios_por_defecto"][formato]
    pieza = {
        "id": f"{dia}-{formato}",
        "fecha": dia,
        "formato": formato,
        "fecha_hora_local": f"{dia}T{hora}:00",
        "assets": assets,
        "caption": caption,
        "estado": "pendiente",
        "media_id": None,
        "permalink": None,
        "publicado_el": None,
        "intentos": 0,
        "ultimo_error": None,
    }
    problemas = []
    if err_caption and formato != "historia":
        problemas.append(err_caption)
    if formato == "carrusel":
        n = len(assets)
        mn = CONFIG["reglas_duras"]["slides_min"]
        mx = CONFIG["reglas_duras"]["slides_max"]
        if not (mn <= n <= mx):
            problemas.append(f"{n} slides (Instagram acepta de {mn} a {mx})")
    if problemas:
        pieza["estado"] = "bloqueado"
        pieza["ultimo_error"] = " · ".join(problemas)
    return pieza


def verificar_tope_feed(piezas):
    """Regla dura de `akyra-estrategia-semanal` v1.12: 1 pieza de FEED por día."""
    feed = CONFIG["reglas_duras"]["formatos_feed"]
    por_dia = {}
    for p in piezas:
        if p["formato"] in feed:
            por_dia.setdefault(p["fecha"], []).append(p["id"])
    return {d: ids for d, ids in por_dia.items()
            if len(ids) > CONFIG["reglas_duras"]["max_piezas_feed_por_dia"]}


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    rehacer = "--rehacer" in sys.argv

    cola = {"version": "1.0", "zona_horaria": CONFIG["zona_horaria"], "lotes": []}
    if os.path.exists(COLA) and not rehacer:
        cola = json.load(open(COLA, encoding="utf-8"))

    dias = args or carpetas_de_piezas()
    ya_en_cola = {p["id"] for lote in cola["lotes"] for p in lote["piezas"]}

    piezas = []
    for dia in dias:
        for p in detectar_piezas(dia):
            if p["id"] in ya_en_cola and not rehacer:
                print(f"  = {p['id']} ya estaba en la cola, se deja como está")
                continue
            piezas.append(p)
            marca = "!" if p["estado"] == "bloqueado" else "+"
            print(f"  {marca} {p['id']}: {len(p['assets'])} archivo(s)"
                  + (f" — {p['ultimo_error']}" if p["ultimo_error"] else ""))

    if not piezas:
        print("\nNo hay piezas nuevas para sumar a la cola.")
        return 0

    choques = verificar_tope_feed(piezas)
    if choques:
        print("\n⚠️  Tope duro de 1 pieza de feed por día (akyra-estrategia-semanal v1.12):")
        for d, ids in choques.items():
            print(f"   {d}: {', '.join(ids)}")
        print("   Resolver antes de aprobar el lote.")

    lote = {
        "id": f"lote-{datetime.now().strftime('%Y%m%d-%H%M')}",
        "rango": f"{piezas[0]['fecha']} a {piezas[-1]['fecha']}",
        "creado_el": datetime.now().isoformat(timespec="seconds"),
        "aprobado": False,
        "aprobado_por": None,
        "aprobado_el": None,
        "piezas": piezas,
    }
    cola["lotes"] = [l for l in cola["lotes"] if l["piezas"]] + [lote]
    json.dump(cola, open(COLA, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    print(f"\nLote {lote['id']} escrito en cola.json con {len(piezas)} pieza(s).")
    print("Queda SIN APROBAR. Para que el worker lo publique:")
    print("  python3 scripts/aprobar.py " + lote["id"] + " --por 'Nicolás'")
    return 0


if __name__ == "__main__":
    sys.exit(main())
