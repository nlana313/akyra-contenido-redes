#!/usr/bin/env python3
"""Publica en Instagram por la API de Meta, sin intermediarios.

Es la misma API que Windsor usa por debajo, pero llamada directo: publicar no
tiene costo y no hay cuota de un plan de terceros en el medio, que es lo que
venía rebotando una de cada tres piezas.

El flujo de Meta es siempre en dos tiempos — primero se crea un "contenedor"
con el archivo y el caption, después se publica ese contenedor:

    imagen    → crear contenedor → publicar
    carrusel  → un contenedor por slide → contenedor padre → publicar
    reel      → crear contenedor → ESPERAR a que Meta procese el video → publicar
    historia  → crear contenedor → publicar

La espera del reel no es opcional: Meta descarga y transcodifica el video, y si
se publica el contenedor antes de que termine, la llamada falla. Por eso se
consulta el estado hasta que diga FINISHED.

Credenciales (como variables de entorno):
    META_ACCESS_TOKEN   token de acceso con permiso de publicación
    IG_USER_ID          id de la cuenta de Instagram (opcional: sale de config.json)
"""
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG = json.load(open(os.path.join(RAIZ, "config.json"), encoding="utf-8"))

VERSION = CONFIG.get("meta", {}).get("api_version", "v26.0")
BASE = f"https://graph.facebook.com/{VERSION}"

ESPERA_REEL_SEGUNDOS = 15
INTENTOS_REEL = 40  # hasta 10 minutos: un reel de 1080x1920 tarda bastante


class ErrorMeta(Exception):
    """Error devuelto por la API, ya con el mensaje legible que manda Meta."""


def _llamar(ruta, params, token, metodo="POST"):
    params = dict(params, access_token=token)
    datos = urllib.parse.urlencode(params).encode("utf-8")
    url = f"{BASE}/{ruta}"
    if metodo == "GET":
        url += "?" + datos.decode("utf-8")
        datos = None
    req = urllib.request.Request(url, data=datos, method=metodo)
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        cuerpo = e.read().decode("utf-8", "replace")
        try:
            err = json.loads(cuerpo).get("error", {})
            msg = err.get("error_user_msg") or err.get("message") or cuerpo
            raise ErrorMeta(f"{msg} (código {err.get('code')})") from None
        except json.JSONDecodeError:
            raise ErrorMeta(f"HTTP {e.code}: {cuerpo[:300]}") from None


def _contenedor(ig_user, params, token):
    r = _llamar(f"{ig_user}/media", params, token)
    if "id" not in r:
        raise ErrorMeta(f"Meta no devolvió id de contenedor: {r}")
    return r["id"]


def _esperar_procesado(ig_user, contenedor, token):
    """Espera a que Meta termine de procesar un video.

    Meta descarga el archivo desde la URL pública y lo transcodifica; hasta que
    eso no termina, publicar el contenedor falla. El estado pasa por IN_PROGRESS
    y termina en FINISHED o ERROR.
    """
    for intento in range(INTENTOS_REEL):
        r = _llamar(contenedor, {"fields": "status_code,status"}, token, metodo="GET")
        estado = r.get("status_code")
        if estado == "FINISHED":
            return
        if estado == "ERROR":
            raise ErrorMeta(f"Meta no pudo procesar el video: {r.get('status')}")
        if estado == "EXPIRED":
            raise ErrorMeta("el contenedor venció antes de publicarse")
        time.sleep(ESPERA_REEL_SEGUNDOS)
    raise ErrorMeta(f"el video sigue procesándose después de "
                    f"{INTENTOS_REEL * ESPERA_REEL_SEGUNDOS // 60} minutos")


def _publicar(ig_user, contenedor, token):
    r = _llamar(f"{ig_user}/media_publish", {"creation_id": contenedor}, token)
    if "id" not in r:
        raise ErrorMeta(f"Meta no devolvió id del post publicado: {r}")
    return r["id"]


def publicar(pieza, urls, token=None, ig_user=None):
    """Publica una pieza y devuelve el id del medio publicado.

    `urls` son las URLs públicas de los archivos, ya en el orden correcto.
    """
    token = token or os.environ.get("META_ACCESS_TOKEN")
    ig_user = (ig_user or os.environ.get("IG_USER_ID")
               or CONFIG["cuenta_instagram"]["account_id"])
    if not token:
        raise ErrorMeta("falta META_ACCESS_TOKEN")

    formato = pieza["formato"]
    caption = pieza.get("caption") or ""

    if formato == "imagen":
        c = _contenedor(ig_user, {"image_url": urls[0], "caption": caption}, token)

    elif formato == "carrusel":
        hijos = [_contenedor(ig_user, {"image_url": u, "is_carousel_item": "true"}, token)
                 for u in urls]
        c = _contenedor(ig_user, {"media_type": "CAROUSEL",
                                  "children": ",".join(hijos),
                                  "caption": caption}, token)

    elif formato == "reel":
        c = _contenedor(ig_user, {
            "media_type": "REELS",
            "video_url": urls[0],
            "caption": caption,
            # Meta publica todo video suelto como Reel; esto controla si además
            # aparece en la grilla del perfil.
            "share_to_feed": "true",
        }, token)
        _esperar_procesado(ig_user, c, token)

    elif formato == "historia":
        es_video = urls[0].lower().split("?")[0].endswith((".mp4", ".mov"))
        params = {"media_type": "STORIES"}
        params["video_url" if es_video else "image_url"] = urls[0]
        c = _contenedor(ig_user, params, token)
        if es_video:
            _esperar_procesado(ig_user, c, token)

    else:
        raise ErrorMeta(f"formato desconocido: {formato}")

    return _publicar(ig_user, c, token)


def verificar_credenciales(token=None, ig_user=None):
    """Comprueba que el token sirve y a qué cuenta apunta, sin publicar nada."""
    token = token or os.environ.get("META_ACCESS_TOKEN")
    ig_user = (ig_user or os.environ.get("IG_USER_ID")
               or CONFIG["cuenta_instagram"]["account_id"])
    if not token:
        raise ErrorMeta("falta META_ACCESS_TOKEN")
    r = _llamar(ig_user, {"fields": "username,followers_count,media_count"},
                token, metodo="GET")
    return r


if __name__ == "__main__":
    import sys
    try:
        datos = verificar_credenciales()
        print("Credenciales OK")
        print(f"  cuenta:      @{datos.get('username')}")
        print(f"  seguidores:  {datos.get('followers_count')}")
        print(f"  piezas:      {datos.get('media_count')}")
        print(f"  API:         {VERSION}")
    except ErrorMeta as e:
        print(f"No se pudo verificar: {e}", file=sys.stderr)
        sys.exit(1)
