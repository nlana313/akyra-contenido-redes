#!/usr/bin/env python3
"""Registra una corrección de Nicolás o Joaquín y la convierte en regla del motor.

Este es el mecanismo por el que el motor deja de repetir un error. Hoy, cuando
Nicolás corrige algo, la corrección queda en una conversación: se arregla esa
pieza y el motor vuelve a cometer lo mismo tres semanas después. Lo que no se
convierte en regla, se olvida.

Hay dos clases de corrección y las dos se registran, pero se tratan distinto:

  - **Verificable por máquina** (se pasó del largo, usó una palabra prohibida,
    le falta la fuente): se agrega como regla a `reglas.json` y a partir de ahí
    `verificar.py` la chequea sola en cada lote, para siempre. Nadie tiene que
    acordarse.
  - **De criterio editorial** (el ángulo no servía, el ejemplo no se entendía,
    el tono sonaba vendedor): no hay patrón que la detecte, así que queda en
    `Correcciones.md` para que la lea quien genera la semana siguiente — y para
    que `akyra-aprendizaje` la cruce contra las métricas en el cierre de mes.

Uso:
    # Corrección que se vuelve regla automática
    python3 scripts/corregir.py "No usar 'solución' en los hooks, suena a vendedor" \\
        --pieza 2026-10-22 --patron "(?i)\\bsoluci[oó]n" --donde hook --severidad advierte

    # Corrección de criterio (sin patrón)
    python3 scripts/corregir.py "El ejemplo de la bodega no aplica a San Rafael" \\
        --pieza 2026-10-22

    # Ver todo lo corregido (esto lee el motor antes de generar)
    python3 scripts/corregir.py --listar
"""
import argparse
import json
import os
import re
import sys
from datetime import datetime

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REGLAS_JSON = os.path.join(RAIZ, "reglas.json")
LEDGER = os.path.join(RAIZ, "Correcciones.md")

ENCABEZADO = """# AKYRA — Correcciones al motor de redes

Cada vez que Nicolás o Joaquín corrigen algo de una pieza, queda registrado acá.
Es la memoria de lo que el motor ya aprendió a no hacer.

**Antes de generar una semana nueva, leer este archivo.** Las correcciones
marcadas como *regla automática* ya las verifica `scripts/verificar.py` solo;
las de *criterio* dependen de que quien genera las tenga presentes.

| Fecha | Pieza | Qué se corrigió | Tipo | Regla |
|---|---|---|---|---|
"""


def proximo_id(reglas):
    nums = [int(m.group(1)) for r in reglas
            if (m := re.match(r"R-(\d+)$", r.get("id", "")))]
    return f"R-{max(nums, default=0) + 1:03d}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("correccion", nargs="?", help="qué se corrigió, en tus palabras")
    ap.add_argument("--pieza", help="fecha de la pieza corregida, ej. 2026-10-22")
    ap.add_argument("--patron", help="regex que detecta el error (la vuelve regla automática)")
    ap.add_argument("--donde", nargs="*", default=["hook", "slides", "copy"],
                    help="dónde aplica: hook slides copy hashtags pieza")
    ap.add_argument("--severidad", choices=["bloquea", "advierte"], default="advierte")
    ap.add_argument("--por", default="Nicolás")
    ap.add_argument("--listar", action="store_true")
    a = ap.parse_args()

    if a.listar or not a.correccion:
        if os.path.exists(LEDGER):
            print(open(LEDGER, encoding="utf-8").read())
        else:
            print("Todavía no hay correcciones registradas.")
        return 0

    hoy = datetime.now().strftime("%d/%m/%Y")
    regla_id = "—"

    if a.patron:
        try:
            re.compile(a.patron)
        except re.error as e:
            print(f"El patrón no es una expresión regular válida: {e}", file=sys.stderr)
            return 1

        datos = json.load(open(REGLAS_JSON, encoding="utf-8"))
        regla_id = proximo_id(datos["reglas"])
        datos["reglas"].append({
            "id": regla_id,
            "titulo": a.correccion[:80],
            "origen": f"Corrección de {a.por}, {hoy}"
                      + (f" (sobre la pieza del {a.pieza})" if a.pieza else ""),
            "tipo": "prohibido",
            "aplica_a": a.donde,
            "patron": a.patron,
            "excepciones": [],
            "severidad": a.severidad,
            "mensaje": a.correccion,
        })
        datos["actualizado"] = datetime.now().strftime("%Y-%m-%d")
        json.dump(datos, open(REGLAS_JSON, "w", encoding="utf-8"),
                  ensure_ascii=False, indent=2)
        print(f"Regla {regla_id} agregada a reglas.json — "
              f"{'bloquea' if a.severidad == 'bloquea' else 'avisa en'} cada lote nuevo.")
    else:
        print("Registrada como corrección de criterio (no hay patrón que la detecte "
              "sola).\nLa va a leer quien genere la próxima semana.")

    if not os.path.exists(LEDGER):
        open(LEDGER, "w", encoding="utf-8").write(ENCABEZADO)
    tipo = "regla automática" if a.patron else "criterio"
    fila = (f"| {hoy} | {a.pieza or '—'} | {a.correccion} | {tipo} | {regla_id} |\n")
    with open(LEDGER, "a", encoding="utf-8") as f:
        f.write(fila)

    print(f"Anotada en Correcciones.md.")
    if a.patron:
        print("\nConviene correr la verificación para ver si alguna pieza en cola "
              "ya incumple la regla nueva:\n  python3 scripts/verificar.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
