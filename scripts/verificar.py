#!/usr/bin/env python3
"""Revisa cada pieza contra las reglas de marca de `reglas.json` antes de publicarla.

Es la red de seguridad que hace que valga la pena automatizar la aprobación: el
motor no se auto-aprueba porque sí, se auto-aprueba cuando pasó una revisión
que verifica, una por una, las reglas que Nicolás y Joaquín fueron fijando — las
que ya estaban escritas en las skills y las que se aprendieron corrigiendo
piezas reales.

Una regla `bloquea` impide la auto-aprobación. Una regla `advierte` no frena
nada, pero queda anotada para que quien revise la vea.

Uso:
    python3 scripts/verificar.py                      # el último lote
    python3 scripts/verificar.py lote-20261019-1247
    python3 scripts/verificar.py --json               # salida para la Action
"""
import json
import os
import re
import sys
import unicodedata
from datetime import datetime, timedelta

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REGLAS = json.load(open(os.path.join(RAIZ, "reglas.json"), encoding="utf-8"))["reglas"]
COLA = os.path.join(RAIZ, "cola.json")
OFERTAS = ("/Users/nicolaslanacastro/Desktop/AKYRA - Ingeniería con Propósito/"
           "AKYRA_HERRAMIENTAS/Motor_Redes_AKYRA/Estado/Ofertas_Activas.md")


# --- lectura de la pieza -----------------------------------------------------

def partes_de_pieza(ruta_md):
    """Parte el `pieza.md` en los pedazos que las reglas saben mirar."""
    txt = open(ruta_md, encoding="utf-8").read()
    p = {"texto_completo": txt, "hook": "", "slides": [], "copy": "",
         "hashtags": "", "eyebrows": [], "es_historia": False}

    m = re.search(r"^\*\*T[ií]tulo:\*\*\s*(.+?)(?:\s*\(\d+\s*palabras?\))?\s*$",
                  txt, re.MULTILINE)
    if m:
        p["hook"] = m.group(1).strip()

    # Filas de la tabla de slides: | n | eyebrow | headline | sub |
    for fila in re.findall(r"^\|\s*([^|]+?)\s*\|([^|]*)\|([^|]*)\|([^|]*)\|\s*$",
                           txt, re.MULTILINE):
        etiqueta = fila[0].strip().lower()
        if etiqueta.startswith(("slide", "---", "bloque")) and "eyebrow" in etiqueta:
            continue
        if re.match(r"^(\d|bloque)", etiqueta):
            p["eyebrows"].append(fila[1].strip())
            p["slides"].append(" ".join(c.strip() for c in fila[1:]))

    m = re.search(r"^##\s*Copy Instagram.*?$(.*?)(?=^\*\*Hashtags|^##\s)", txt,
                  re.MULTILINE | re.DOTALL)
    if m:
        p["copy"] = m.group(1).strip()

    m = re.search(r"^\*\*Hashtags[^:]*:\*\*\s*(.+?)$", txt, re.MULTILINE)
    if m:
        p["hashtags"] = m.group(1).strip()

    p["es_historia"] = bool(re.search(r"(?i)^##\s*Historia", txt, re.MULTILINE))
    return p


def campo(p, nombre):
    if nombre == "hook":
        return p["hook"]
    if nombre == "slides":
        return "\n".join(p["slides"])
    if nombre == "copy":
        return p["copy"]
    if nombre == "hashtags":
        return p["hashtags"]
    if nombre in ("pieza", "historia"):
        return p["texto_completo"]
    return ""


def texto_de(p, regla):
    return "\n".join(campo(p, c) for c in regla.get("aplica_a", ["pieza"]))


def hay_oferta_activa():
    """Una oferta solo cuenta como abierta si tiene instancia programada."""
    if not os.path.exists(OFERTAS):
        return False
    t = open(OFERTAS, encoding="utf-8").read().lower()
    return "sin instancia programada" not in t and "cerrada" not in t


# --- evaluación de reglas ----------------------------------------------------

def evaluar(regla, p, contexto):
    """Devuelve una lista de hallazgos (vacía si la pieza cumple)."""
    t = regla["tipo"]
    fallos = []

    if t in ("prohibido", "prohibido_condicional"):
        if t == "prohibido_condicional" and regla.get("permitido_si_ofertas_activas") \
                and hay_oferta_activa():
            return []
        texto = texto_de(p, regla)
        for m in re.finditer(regla["patron"], texto):
            fragmento = texto[max(0, m.start() - 30):m.end() + 30].replace("\n", " ")
            if any(re.search(e, fragmento) for e in regla.get("excepciones", [])):
                continue
            fallos.append(f"«{m.group(0)}» en: …{fragmento.strip()}…")

    elif t == "requerido":
        texto = p["texto_completo"]
        cond = regla.get("condicion_patron")
        if cond and not re.search(cond, texto):
            return []
        if regla.get("aplica_a") == ["historia"] and not p["es_historia"]:
            return []
        if not re.search(regla["requiere_patron"], texto):
            fallos.append("falta " + regla["requiere_patron"])
        elif regla.get("requiere_ademas") and not re.search(regla["requiere_ademas"], texto):
            fallos.append("falta " + regla["requiere_ademas"])

    elif t == "limite":
        texto = texto_de(p, regla)
        if not texto.strip():
            return []
        n = len(texto.split()) if regla["metrica"] == "palabras" else len(texto.split("#")) - 1
        if regla.get("maximo") is not None and n > regla["maximo"]:
            fallos.append(f"{n} (máximo {regla['maximo']})")
        if regla.get("minimo") is not None and n < regla["minimo"]:
            fallos.append(f"{n} (mínimo {regla['minimo']})")

    elif t == "limite_por_slide":
        for i, s in enumerate(p["slides"], 1):
            n = len(re.findall(regla["patron"], s))
            if n > regla["maximo"]:
                fallos.append(f"slide {i}: {n} resaltados (máximo {regla['maximo']})")

    elif t == "exclusion_mutua":
        texto = p["texto_completo"]
        if regla.get("excepcion_si") and re.search(regla["excepcion_si"], texto):
            return []
        presentes = [pat for pat in regla["patrones"] if re.search(pat, texto)]
        if len(presentes) > 1:
            fallos.append("conviven " + " + ".join(presentes))

    elif t == "mapa_pilar_color":
        texto = p["texto_completo"].lower()
        m = re.search(r"\*\*pilar:\*\*\s*([^·\n]+)", texto)
        a = re.search(r"\*\*acento:\*\*\s*([^·\n`]+)", texto)
        if m and a:
            pilar, acento = m.group(1).strip(), _sin_tildes(a.group(1))
            esperado = next((v for k, v in regla["mapa"].items() if k in pilar), None)
            if esperado and _sin_tildes(esperado) not in acento:
                fallos.append(f"pilar «{pilar}» con acento «{a.group(1).strip()}» "
                              f"(se esperaba familia {esperado})")

    elif t == "anti_repeticion_estructura":
        actual = [e.lower() for e in p["eyebrows"] if e and e != "—"]
        if len(actual) >= 3:
            for otra_id, otros in contexto.get("eyebrows_recientes", {}).items():
                if not otros:
                    continue
                comunes = len(set(actual) & set(otros))
                sim = comunes / max(len(actual), len(otros))
                if sim >= regla["umbral_similitud"]:
                    fallos.append(f"{int(sim*100)}% de eyebrows compartidos con {otra_id}")

    return fallos


def _sin_tildes(s):
    return "".join(c for c in unicodedata.normalize("NFD", s.lower())
                   if unicodedata.category(c) != "Mn")


# --- recorrido del lote ------------------------------------------------------

def ruta_pieza_md(fecha):
    for sub in ("v2_motor", ""):
        r = os.path.join(RAIZ, fecha, sub, "pieza.md") if sub else os.path.join(RAIZ, fecha, "pieza.md")
        if os.path.exists(r):
            return r
    arch = os.path.join(RAIZ, "publicado", fecha, "v2_motor", "pieza.md")
    return arch if os.path.exists(arch) else None


def eyebrows_recientes(excepto, dias):
    """Eyebrows de las piezas publicadas en los últimos N días, para R-013."""
    fuera = {}
    corte = datetime.now() - timedelta(days=dias)
    base = os.path.join(RAIZ, "publicado")
    if not os.path.isdir(base):
        return fuera
    for d in os.listdir(base):
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", d) or d in excepto:
            continue
        try:
            if datetime.strptime(d, "%Y-%m-%d") < corte:
                continue
        except ValueError:
            continue
        md = os.path.join(base, d, "v2_motor", "pieza.md")
        if os.path.exists(md):
            fuera[d] = [e.lower() for e in partes_de_pieza(md)["eyebrows"] if e and e != "—"]
    return fuera


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    como_json = "--json" in sys.argv

    cola = json.load(open(COLA, encoding="utf-8"))
    lote = next((l for l in cola["lotes"] if l["id"] == args[0]), None) if args \
        else (cola["lotes"][-1] if cola["lotes"] else None)
    if not lote:
        print("No hay lote para verificar.", file=sys.stderr)
        return 1

    fechas = {p["fecha"] for p in lote["piezas"]}
    contexto = {"eyebrows_recientes": eyebrows_recientes(fechas, 21)}

    resultado = {"lote": lote["id"], "bloqueos": [], "avisos": [], "verificado_el":
                 datetime.now().isoformat(timespec="seconds")}
    vistas = set()

    for pieza in lote["piezas"]:
        if pieza["fecha"] in vistas:
            continue
        vistas.add(pieza["fecha"])
        md = ruta_pieza_md(pieza["fecha"])
        if not md:
            resultado["avisos"].append({"pieza": pieza["fecha"], "regla": "—",
                                        "detalle": "no se encontró el pieza.md"})
            continue
        p = partes_de_pieza(md)
        for regla in REGLAS:
            for f in evaluar(regla, p, contexto):
                destino = "bloqueos" if regla["severidad"] == "bloquea" else "avisos"
                resultado[destino].append({
                    "pieza": pieza["fecha"], "regla": regla["id"],
                    "titulo": regla["titulo"], "detalle": f,
                    "mensaje": regla["mensaje"], "origen": regla["origen"]})

    resultado["estado"] = "ok" if not resultado["bloqueos"] else "bloqueado"

    # Se guarda en la cola: es lo que después mira la auto-aprobación.
    lote["verificacion"] = {k: resultado[k] for k in ("estado", "verificado_el")}
    lote["verificacion"]["bloqueos"] = len(resultado["bloqueos"])
    lote["verificacion"]["avisos"] = len(resultado["avisos"])
    json.dump(cola, open(COLA, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    if como_json:
        print(json.dumps(resultado, ensure_ascii=False, indent=2))
        return 0 if resultado["estado"] == "ok" else 1

    print(f"Verificación del lote {lote['id']} — {len(vistas)} pieza(s), "
          f"{len(REGLAS)} reglas\n")
    for clave, simbolo in (("bloqueos", "✗"), ("avisos", "⚠")):
        for h in resultado[clave]:
            print(f"{simbolo} [{h['regla']}] {h['pieza']} — {h.get('titulo','')}")
            print(f"    {h['detalle']}")
            if h.get("mensaje"):
                print(f"    → {h['mensaje']}")
            if h.get("origen"):
                print(f"    origen: {h['origen']}")
            print()
    if resultado["estado"] == "ok" and not resultado["avisos"]:
        print("Todo en orden: ninguna regla incumplida.")
    elif resultado["estado"] == "ok":
        print(f"Sin bloqueos. {len(resultado['avisos'])} aviso(s) para mirar, "
              "no frenan la publicación.")
    else:
        print(f"{len(resultado['bloqueos'])} bloqueo(s): el lote NO se puede "
              "auto-aprobar hasta resolverlos.")
    return 0 if resultado["estado"] == "ok" else 1


if __name__ == "__main__":
    sys.exit(main())
