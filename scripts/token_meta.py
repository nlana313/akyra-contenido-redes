#!/usr/bin/env python3
"""Convierte un token corto de Meta en uno de larga duración y lo guarda en GitHub.

Es el camino alternativo al usuario del sistema del Business Manager. Ese camino
da un token que no vence, pero exige que el portfolio comercial reconozca la app
y que el usuario del sistema tenga rol sobre ella — una cadena de permisos que
puede trabarse en cualquiera de sus eslabones. Este camino no necesita nada de
eso: alcanza con ser administrador de la app y de la cuenta.

La contra es que el token dura 60 días y hay que renovarlo. El script avisa la
fecha exacta de vencimiento al terminar.

Nada de lo que pedís acá se muestra en pantalla ni queda en un archivo: el app
secret y el token se leen ocultos, el token final va directo al almacén cifrado
de GitHub.

Uso:
    python3 scripts/token_meta.py
"""
import getpass
import json
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta

sys.path.insert(0, __file__.rsplit("/", 1)[0])
import meta  # noqa: E402  (usa su misma versión de API y verificación)

REPO = "nlana313/akyra-contenido-redes"


def pedir(texto, oculto=False):
    valor = (getpass.getpass(texto) if oculto else input(texto)).strip()
    if not valor:
        print("No puede quedar vacío.", file=sys.stderr)
        sys.exit(1)
    return valor


def intercambiar(app_id, app_secret, token_corto):
    """Cambia un token de ~1 hora por uno de ~60 días."""
    q = urllib.parse.urlencode({
        "grant_type": "fb_exchange_token",
        "client_id": app_id,
        "client_secret": app_secret,
        "fb_exchange_token": token_corto,
    })
    url = f"https://graph.facebook.com/{meta.VERSION}/oauth/access_token?{q}"
    try:
        with urllib.request.urlopen(url, timeout=60) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        cuerpo = e.read().decode("utf-8", "replace")
        try:
            msg = json.loads(cuerpo)["error"]["message"]
        except Exception:
            msg = cuerpo[:300]
        print(f"\nMeta rechazó el intercambio: {msg}", file=sys.stderr)
        sys.exit(1)


def main():
    print(__doc__.split("Uso:")[0].strip())
    print("\nSacá el ID y el secreto de la app de:")
    print("  developers.facebook.com/apps → tu app → Configuración → Información básica")
    print("\nY el token corto de:")
    print("  developers.facebook.com/tools/explorer")
    print("  (elegí tu app, 'Generate Access Token', y aceptá los 4 permisos:")
    print("   instagram_basic, instagram_content_publish, pages_show_list,")
    print("   pages_read_engagement)\n")

    app_id = pedir("ID de la app: ")
    app_secret = pedir("Secreto de la app (no se ve al escribir): ", oculto=True)
    token_corto = pedir("Token del explorador (no se ve al escribir): ", oculto=True)

    print("\nIntercambiando por un token de larga duración…")
    r = intercambiar(app_id, app_secret, token_corto)
    token = r.get("access_token")
    if not token:
        print(f"Meta no devolvió token: {r}", file=sys.stderr)
        return 1

    segundos = r.get("expires_in")
    vence = (datetime.now() + timedelta(seconds=int(segundos))) if segundos else None

    print("Verificando que el token funcione…")
    try:
        datos = meta.verificar_credenciales(token=token)
    except meta.ErrorMeta as e:
        print(f"\nEl token se generó pero no sirve para publicar: {e}", file=sys.stderr)
        print("Revisá que los 4 permisos estén aceptados y que la cuenta de Instagram "
              "sea Business/Creator y esté vinculada a la Página.", file=sys.stderr)
        return 1

    print(f"  cuenta: @{datos.get('username')} · "
          f"{datos.get('followers_count')} seguidores · "
          f"{datos.get('media_count')} piezas")

    print("\nGuardando en GitHub…")
    p = subprocess.run(["gh", "secret", "set", "META_ACCESS_TOKEN", "--repo", REPO],
                       input=token, text=True, capture_output=True)
    if p.returncode != 0:
        print(f"No se pudo guardar el secret: {p.stderr}", file=sys.stderr)
        return 1

    print("Listo. El motor ya puede publicar directo por Meta.")
    if vence:
        print(f"\n⚠️  Este token vence el {vence.strftime('%d/%m/%Y')}. "
              "Volvé a correr este script antes de esa fecha.")
        print("   (Hay un recordatorio programado que te va a avisar dos semanas antes.)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
