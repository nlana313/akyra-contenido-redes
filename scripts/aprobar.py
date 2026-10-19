#!/usr/bin/env python3
"""Aprueba un lote de `cola.json` — la compuerta humana del motor.

Hasta que un lote no pasa por acá, el worker de la nube no publica nada de ese
lote. Es la traducción operativa de la regla 7 de `akyra-branding-base`
("falta aprobación humana") a algo que una máquina puede verificar.

Uso:
    python3 scripts/aprobar.py --listar
    python3 scripts/aprobar.py lote-20261019-1247 --por "Nicolás"
    python3 scripts/aprobar.py lote-20261019-1247 --por "Joaquín" --salvo 2026-10-23-carrusel
    python3 scripts/aprobar.py lote-20261019-1247 --revocar
"""
import argparse
import json
import os
import sys
from datetime import datetime

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COLA = os.path.join(RAIZ, "cola.json")

SIMBOLO = {"pendiente": "·", "publicado": "✓", "bloqueado": "!",
           "error": "✗", "vencido": "⏰", "omitido": "—"}


def listar(cola):
    for lote in cola["lotes"]:
        estado = "APROBADO" if lote["aprobado"] else "sin aprobar"
        quien = f" por {lote['aprobado_por']}" if lote.get("aprobado_por") else ""
        print(f"\n{lote['id']}  ({lote['rango']})  — {estado}{quien}")
        for p in lote["piezas"]:
            s = SIMBOLO.get(p["estado"], "?")
            extra = f"  ← {p['ultimo_error']}" if p.get("ultimo_error") else ""
            print(f"   {s} {p['fecha_hora_local'][:16]}  {p['formato']:9s} "
                  f"{p['id']}{extra}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("lote", nargs="?")
    ap.add_argument("--por", help="quién aprueba (queda registrado en la cola)")
    ap.add_argument("--salvo", nargs="*", default=[],
                    help="ids de piezas que NO se publican (quedan en 'omitido')")
    ap.add_argument("--revocar", action="store_true")
    ap.add_argument("--listar", action="store_true")
    a = ap.parse_args()

    cola = json.load(open(COLA, encoding="utf-8"))
    if a.listar or not a.lote:
        listar(cola)
        return 0

    lote = next((l for l in cola["lotes"] if l["id"] == a.lote), None)
    if not lote:
        print(f"No existe el lote {a.lote}.", file=sys.stderr)
        listar(cola)
        return 1

    if a.revocar:
        lote["aprobado"] = False
        lote["aprobado_por"] = None
        lote["aprobado_el"] = None
        print(f"Lote {lote['id']} vuelve a estado SIN APROBAR.")
    else:
        if not a.por:
            print("Falta --por: la aprobación tiene que quedar a nombre de alguien.",
                  file=sys.stderr)
            return 1
        bloqueadas = [p["id"] for p in lote["piezas"] if p["estado"] == "bloqueado"]
        if bloqueadas:
            print("No se puede aprobar: hay piezas bloqueadas por una regla dura:",
                  file=sys.stderr)
            for p in lote["piezas"]:
                if p["estado"] == "bloqueado":
                    print(f"   {p['id']}: {p['ultimo_error']}", file=sys.stderr)
            return 1
        for p in lote["piezas"]:
            if p["id"] in a.salvo:
                p["estado"] = "omitido"
                p["ultimo_error"] = f"excluida al aprobar el lote ({a.por})"
        lote["aprobado"] = True
        lote["aprobado_por"] = a.por
        lote["aprobado_el"] = datetime.now().isoformat(timespec="seconds")
        listos = sum(1 for p in lote["piezas"] if p["estado"] == "pendiente")
        print(f"Lote {lote['id']} APROBADO por {a.por} — {listos} pieza(s) "
              f"quedan listas para publicarse en su horario.")
        if a.salvo:
            print(f"Excluidas: {', '.join(a.salvo)}")

    json.dump(cola, open(COLA, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print("\nRecordá pushear para que el worker de la nube vea el cambio:")
    print("  git add cola.json && git commit -m 'Aprueba lote' && git push")
    return 0


if __name__ == "__main__":
    sys.exit(main())
