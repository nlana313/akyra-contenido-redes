#!/usr/bin/env python3
"""Publica en Instagram las piezas de `cola.json` que ya llegaron a su horario.

Corre en GitHub Actions cada hora, sin intervención. Es el único componente que
toca Instagram, y tiene cuatro candados antes de publicar algo:

  1. El lote tiene que estar `"aprobado": true` (compuerta humana — regla 7 de
     `akyra-branding-base`). Un lote sin aprobar no se publica nunca, por más
     que le haya pasado el horario.
  2. La hora local de la pieza ya pasó, y hace menos de `ventana_publicacion_minutos`.
     Si una pieza quedó mucho tiempo atrás (la Action estuvo caída, el lote se
     aprobó tarde), NO se publica a destiempo: queda `vencido` para que una
     persona decida si todavía tiene sentido.
  3. La pieza sigue en estado `pendiente` y no agotó los reintentos.
  4. No se publicó ya otra pieza de feed ese mismo día (tope duro de
     `akyra-estrategia-semanal` v1.12).

Cada publicación se confirma en `cola.json` y se commitea en el acto, así una
corrida interrumpida nunca republica lo que ya salió.

Variables de entorno:
    WINDSOR_API_KEY   obligatoria
    DRY_RUN=1         simula todo sin tocar Instagram (default en ejecución manual)
"""
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG = json.load(open(os.path.join(RAIZ, "config.json"), encoding="utf-8"))
COLA = os.path.join(RAIZ, "cola.json")

API = "https://connectors.windsor.ai/{connector}/actions"
# Base pública desde donde Instagram descarga los archivos. El repo es público,
# así que `raw.githubusercontent.com` alcanza para las imágenes. Para video
# conviene GitHub Pages, que lo sirve como `video/mp4` en vez de
# `application/octet-stream` (ver LEEME_Automatizacion.md).
_URLS = CONFIG.get("urls_publicas", {})
BASE_IMAGENES = os.environ.get("BASE_URL") or _URLS.get(
    "imagenes", "https://raw.githubusercontent.com/nlana313/akyra-contenido-redes/main")
VIDEO_EXT = (".mp4", ".mov")


def _commit_actual():
    """SHA del commit publicado, para armar URLs de video inmutables."""
    sha = os.environ.get("GITHUB_SHA")
    if sha:
        return sha
    try:
        import subprocess
        return subprocess.run(["git", "-C", RAIZ, "rev-parse", "HEAD"],
                              capture_output=True, text=True, check=True).stdout.strip()
    except Exception:
        return "main"


BASE_VIDEOS = (os.environ.get("BASE_URL_VIDEOS")
               or _URLS.get("videos", BASE_IMAGENES)).replace("{sha}", _commit_actual())

ACCIONES = {
    "carrusel": "create_carousel_post",
    "reel": "create_video_post",
    "imagen": "create_image_post",
    "historia": "create_story",
}


def url_publica(ruta_relativa):
    base = BASE_VIDEOS if ruta_relativa.lower().endswith(VIDEO_EXT) else BASE_IMAGENES
    return f"{base}/{urllib.parse.quote(ruta_relativa)}"


def armar_params(pieza):
    """Traduce una pieza de la cola a los params que espera la acción de Windsor."""
    urls = [url_publica(a) for a in pieza["assets"]]
    fmt = pieza["formato"]
    if fmt == "carrusel":
        return {"image_urls": urls, "caption": pieza["caption"]}
    if fmt == "reel":
        return {"video_url": urls[0], "caption": pieza["caption"], "share_to_feed": True}
    if fmt == "imagen":
        return {"image_url": urls[0], "caption": pieza["caption"]}
    if fmt == "historia":
        clave = "video_url" if pieza["assets"][0].lower().endswith((".mp4", ".mov")) else "image_url"
        return {clave: urls[0]}
    raise ValueError(f"formato desconocido: {fmt}")


def ejecutar(pieza, api_key):
    cuenta = CONFIG["cuenta_instagram"]
    cuerpo = json.dumps({
        "account": cuenta["account_id"],
        "action": ACCIONES[pieza["formato"]],
        "params": armar_params(pieza),
    }).encode("utf-8")
    url = API.format(connector=cuenta["connector"]) + f"?api_key={api_key}"
    req = urllib.request.Request(url, data=cuerpo, method="POST",
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=300) as r:
        return json.loads(r.read().decode("utf-8"))


def id_de_media(respuesta):
    """Windsor devuelve el id del media publicado; el nombre del campo puede
    variar entre acciones, así que se buscan los candidatos conocidos en vez de
    asumir uno solo y perder la trazabilidad del post."""
    if not isinstance(respuesta, dict):
        return None
    for capa in (respuesta, respuesta.get("result") or {}, respuesta.get("data") or {}):
        if isinstance(capa, dict):
            for k in ("media_id", "id", "post_id", "ig_media_id"):
                if capa.get(k):
                    return str(capa[k])
    return None


def _sin_secretos(texto):
    """Saca de un mensaje de error cualquier cosa con forma de credencial.

    Windsor devuelve la API key DENTRO del cuerpo del error ("Please check the
    API key used: <key>"), y ese cuerpo se guardaba tal cual en cola.json, que se
    commitea a un repositorio público. Así se filtró la key el 22/10/2026. Nada
    que venga de una respuesta HTTP se guarda sin pasar por acá.
    """
    if not texto:
        return texto
    clave = os.environ.get("WINDSOR_API_KEY")
    if clave and len(clave) > 6:
        texto = texto.replace(clave, "[API KEY OCULTA]")
    # Red de seguridad: cualquier cadena hexadecimal larga suelta en el mensaje.
    texto = re.sub(r"\b[0-9a-f]{24,}\b", "[OCULTO]", texto, flags=re.IGNORECASE)
    return texto


def guardar(cola):
    json.dump(cola, open(COLA, "w", encoding="utf-8"), ensure_ascii=False, indent=2)


def commit(mensaje):
    """Confirma el cambio de estado en el acto, para que una corrida cortada a
    la mitad no vuelva a publicar lo que ya salió."""
    if os.environ.get("DRY_RUN") == "1":
        return
    os.system('git -C "%s" config user.name "AKYRA Motor de Redes"' % RAIZ)
    os.system('git -C "%s" config user.email "motor@akyra.local"' % RAIZ)
    os.system('git -C "%s" add cola.json' % RAIZ)
    os.system('git -C "%s" commit -q -m "%s" || true' % (RAIZ, mensaje))
    os.system('git -C "%s" push -q || true' % RAIZ)


def auto_aprobar(lote, ahora):
    """Aprueba un lote sin intervención humana, pero solo si se ganó el derecho.

    La compuerta humana no desaparece: se invierte. En vez de esperar un "sí",
    se espera una objeción durante `horas_de_objecion`. Y el permiso para que eso
    ocurra lo da `verificar.py`: si encontró un solo bloqueo contra las reglas de
    marca, este lote no se auto-aprueba nunca — se queda esperando a una persona,
    por más días que pasen.
    """
    cfg = CONFIG.get("auto_aprobacion", {})
    if not cfg.get("habilitada") or lote.get("aprobado"):
        return False

    ver = lote.get("verificacion") or {}
    if cfg.get("exige_verificacion_limpia", True):
        if ver.get("estado") != "ok":
            return False

    creado = lote.get("creado_el")
    if not creado:
        return False
    transcurridas = (ahora - datetime.fromisoformat(creado).replace(tzinfo=ahora.tzinfo))
    if transcurridas < timedelta(hours=cfg.get("horas_de_objecion", 36)):
        return False

    lote["aprobado"] = True
    lote["aprobado_por"] = "auto (verificación limpia + ventana de objeción)"
    lote["aprobado_el"] = ahora.isoformat(timespec="seconds")
    print(f"~ lote {lote['id']}: auto-aprobado "
          f"(verificado el {ver.get('verificado_el','?')}, {ver.get('avisos',0)} aviso(s), "
          f"sin objeciones en {cfg.get('horas_de_objecion',36)} h)")
    return True


def main():
    dry = os.environ.get("DRY_RUN") == "1"
    api_key = os.environ.get("WINDSOR_API_KEY")
    if not api_key and not dry:
        print("ERROR: falta WINDSOR_API_KEY", file=sys.stderr)
        return 1

    tz = ZoneInfo(CONFIG["zona_horaria"])
    ahora = datetime.now(tz)
    ventana = timedelta(minutes=CONFIG["ventana_publicacion_minutos"])
    cola = json.load(open(COLA, encoding="utf-8"))

    publicados_hoy = {
        p["fecha"] for lote in cola["lotes"] for p in lote["piezas"]
        if p["estado"] == "publicado" and p["formato"] in CONFIG["reglas_duras"]["formatos_feed"]
    }
    algo = False

    for lote in cola["lotes"]:
        if auto_aprobar(lote, ahora):
            algo = True
        for pieza in lote["piezas"]:
            if pieza["estado"] != "pendiente":
                continue
            cuando = datetime.fromisoformat(pieza["fecha_hora_local"]).replace(tzinfo=tz)

            if cuando > ahora:
                continue
            if not lote["aprobado"]:
                print(f"- {pieza['id']}: le pasó el horario pero el lote {lote['id']} "
                      f"sigue SIN APROBAR — no se publica")
                continue
            if ahora - cuando > ventana:
                pieza["estado"] = "vencido"
                pieza["ultimo_error"] = (
                    f"el horario era {pieza['fecha_hora_local']} y la ventana es de "
                    f"{CONFIG['ventana_publicacion_minutos']} min; requiere decisión humana")
                print(f"! {pieza['id']}: VENCIDO — {pieza['ultimo_error']}")
                algo = True
                continue
            es_feed = pieza["formato"] in CONFIG["reglas_duras"]["formatos_feed"]
            if es_feed and pieza["fecha"] in publicados_hoy:
                pieza["estado"] = "bloqueado"
                pieza["ultimo_error"] = ("ya salió otra pieza de feed el " + pieza["fecha"] +
                                         " — tope duro de 1/día (estrategia-semanal v1.12)")
                print(f"! {pieza['id']}: {pieza['ultimo_error']}")
                algo = True
                continue
            if pieza["intentos"] >= CONFIG["max_intentos"]:
                pieza["estado"] = "error"
                print(f"! {pieza['id']}: agotó los {CONFIG['max_intentos']} intentos")
                algo = True
                continue

            print(f"> publicando {pieza['id']} ({pieza['formato']}, "
                  f"{len(pieza['assets'])} archivo(s))")
            if dry:
                print("  [DRY_RUN] params:",
                      json.dumps(armar_params(pieza), ensure_ascii=False)[:300])
                continue

            pieza["intentos"] += 1
            try:
                resp = ejecutar(pieza, api_key)
                pieza["estado"] = "publicado"
                pieza["media_id"] = id_de_media(resp)
                pieza["publicado_el"] = ahora.isoformat(timespec="seconds")
                pieza["ultimo_error"] = None
                if es_feed:
                    publicados_hoy.add(pieza["fecha"])
                print(f"  ✓ publicado — media_id {pieza['media_id']}")
            except urllib.error.HTTPError as e:
                detalle = _sin_secretos(e.read().decode("utf-8", "replace")[:500])
                pieza["ultimo_error"] = f"HTTP {e.code}: {detalle}"
                print(f"  ✗ {pieza['ultimo_error']}")
            except Exception as e:  # red caída, timeout de Instagram, etc.
                pieza["ultimo_error"] = _sin_secretos(f"{type(e).__name__}: {e}")
                print(f"  ✗ {pieza['ultimo_error']}")

            algo = True
            guardar(cola)
            commit(f"Publicación automática: {pieza['id']} ({pieza['estado']})")

    if algo and dry:
        print("\n[DRY_RUN] no se escribió cola.json ni se publicó nada.")
    elif algo:
        guardar(cola)
        commit("Actualiza estado de la cola de publicación")
    else:
        print("Nada para publicar en esta corrida.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
