# AKYRA — Contenido de redes

Repositorio de contenido publicado y por publicar de **AKYRA Consultora**
(`@akyraconsultora`). Desde el 19/10/2026 es además el que ejecuta la
publicación automática en Instagram.

El repositorio es **público a propósito**: Instagram descarga las imágenes y
los videos desde una URL pública, así que los archivos tienen que ser
accesibles sin credenciales. Lo que no es público es el motor que los genera
(ver "Dónde vive cada cosa").

---

## Cómo funciona

```
 1. GENERAR    en la Mac — akyra-estrategia-semanal + render.py producen
               AAAA-MM-DD/v2_motor/ con los PNG/MP4 y el pieza.md
 2. ARMAR      python3 scripts/armar_cola.py
               convierte a JPEG y escribe cola.json  ->  lote SIN APROBAR
 3. VERIFICAR  python3 scripts/verificar.py
               chequea cada pieza contra las reglas de marca de reglas.json
 4. APROBAR    automático a las 36 h si la verificación dio limpia,
               o a mano con scripts/aprobar.py. Con un solo bloqueo, el
               lote NUNCA se auto-aprueba: espera a una persona.
 5. PUBLICAR   GitHub Actions, cada hora, sin intervención
               publica cada pieza en su día y horario vía Windsor.ai
 6. MEDIR      GitHub Actions, los lunes
               trae Insights y los deja en Metricas/
 7. CORREGIR   python3 scripts/corregir.py "lo que estuvo mal" --pieza ...
               lo verificable se vuelve regla; el resto queda en Correcciones.md
 8. APRENDER   cierre mensual — akyra-aprendizaje cruza Metricas/ con
               Correcciones.md y actualiza el motor
```

Los pasos 4 y 5 corren en la nube: no hace falta que la Mac esté prendida ni
que haya una sesión de Claude abierta.

## Comandos del día a día

```bash
# Ver el estado de todo lo que está en cola
python3 scripts/aprobar.py --listar

# Sumar a la cola las piezas de la semana recién generada
python3 scripts/armar_cola.py

# Aprobar el lote completo
python3 scripts/aprobar.py lote-20261019-1247 --por "Nicolás"

# Aprobar todo menos una pieza
python3 scripts/aprobar.py lote-20261019-1247 --por "Nicolás" --salvo 2026-10-23-carrusel

# Dar marcha atrás (mientras no se haya publicado)
python3 scripts/aprobar.py lote-20261019-1247 --revocar

# Simular la publicación sin tocar Instagram
DRY_RUN=1 python3 scripts/publicar.py
```

Después de aprobar hay que `git push`: el worker de la nube lee `cola.json`
desde GitHub, no desde la Mac.

## Cómo aprende el motor

Son dos circuitos distintos y los dos terminan cambiando cómo se genera el contenido:

**De lo que corregís vos.** Cada vez que una pieza está mal, se registra:

```bash
# Si el error se puede detectar con una expresión regular, se vuelve regla
python3 scripts/corregir.py "No usar 'solución' en los hooks, suena a vendedor" \
    --pieza 2026-10-22 --patron "(?i)\bsoluci[oó]n" --donde hook

# Si es de criterio, queda anotada para quien genere la semana siguiente
python3 scripts/corregir.py "El ejemplo tiene que ser de la zona, no de Buenos Aires" \
    --pieza 2026-10-22
```

Una corrección con patrón se suma a `reglas.json` y a partir de ahí se verifica
sola en todos los lotes, para siempre. Ese es el punto: lo que se corrige una
vez no se vuelve a corregir.

**De los números.** La Action de los lunes carga las métricas, y el cierre
mensual de `akyra-aprendizaje` las cruza con `Correcciones.md` — buscando tanto
qué rinde como qué tipo de error se repite en lo que venís corrigiendo.

Ver `Correcciones.md` (la memoria) y `reglas.json` (lo ejecutable).

## Las reglas duras que el worker verifica solo

Están en `config.json` y salen del propio motor, no las inventó la
automatización:

| Regla | Origen |
|---|---|
| 1 sola pieza de **feed** por día (las historias no cuentan) | `akyra-estrategia-semanal` v1.12 y v1.15, sobre el análisis de 48 piezas de mayo-julio 2026 |
| Carruseles de 2 a 10 slides, JPEG, ratio 4:5 a 1.91:1 | límite de la API de Instagram |
| Caption de hasta 2200 caracteres | límite de la API de Instagram |
| Ningún lote se auto-aprueba con un bloqueo pendiente | la compuerta humana no desaparece: se invierte en ventana de objeción |
| Una pieza que se pasó más de 48 h de su horario espera decisión humana | pedido de Nicolás: que salga tarde antes que no salga, pero las piezas citan noticias con fecha |

Más las 13 reglas de marca de `reglas.json` (no certificar, voseo rioplatense,
hook de 8 palabras, sin emojis, fuente verificada, convivencia de colores,
matiz por pilar, anti-repetición de esqueleto…), cada una citando la skill y
versión de donde sale.

## Estructura

```
AAAA-MM-DD/v2_motor/   piezas de la semana en curso (PNG/MP4 + pieza.md)
publicado/             piezas ya publicadas, archivadas
publicar/              JPEG derivados que consume Instagram (generados)
Metricas/              métricas semanales (generadas por la Action)
scripts/               armar_cola - verificar - aprobar - publicar - metricas - corregir
cola.json              estado de publicación — la fuente de verdad del worker
config.json            cuenta, horarios, reglas duras y auto-aprobación
reglas.json            las reglas de marca, en forma ejecutable
Correcciones.md        memoria de todo lo que Nicolás y Joaquín corrigieron
```

## Dónde vive cada cosa

| Qué | Dónde |
|---|---|
| Motor visual (`render.py`, fuentes, logos) | `AKYRA - Ingeniería con Propósito/AKYRA_HERRAMIENTAS/Motor_Redes_AKYRA/Motor_Visual/` |
| Ledgers del motor (Bitácora, Temas, Hooks, Ofertas) | `.../Motor_Redes_AKYRA/Estado/` |
| Skills del motor (`akyra-*`) | cuenta de Claude, sincronizadas |
| Pipeline de publicación | este repositorio, `scripts/` |

El motor no está en este repo porque es público y el motor es propiedad
intelectual de AKYRA. Lo que sí está acá es la operación: qué se publica,
cuándo, y qué resultado dio.

## Configuración necesaria

El worker necesita un único secret en el repositorio
(Settings -> Secrets and variables -> Actions):

- `WINDSOR_API_KEY` — API key de Windsor.ai, la misma cuenta que ya tiene
  conectada `@akyraconsultora`.

Para los reels conviene además habilitar GitHub Pages (Settings -> Pages ->
Deploy from branch `main`), porque `raw.githubusercontent.com` sirve los `.mp4`
como `application/octet-stream` y Instagram a veces los rechaza. Con Pages
activo, pasar `BASE_URL=https://nlana313.github.io/akyra-contenido-redes` en el
workflow de publicación.
