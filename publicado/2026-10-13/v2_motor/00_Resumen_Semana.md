# AKYRA — Semana 13-16/10/2026 (versión rehecha según el motor)
Código de referencia: RS-CONT-013-16OCT v2.0 · Emitido 13/10/2026 · Reemplaza a v1.2 (queda como OBSOLETO, no se borra)

## 1. Calendario

| Día | Fecha | Formato | Segmento | Tipo | Pilar | Modo CTA | Tema |
|---|---|---|---|---|---|---|---|
| Mar | 13/10 | Carrusel (6) | ICP1 | Nicho/Autoridad | Calidad-ISO (14001) | 3 · Invitación abierta | El agua no te va a esperar |
| Mié | 14/10 | Carrusel (6) | ICP2 | Venta educativa | IA aplicada | 3 · Invitación abierta | Usás IA y seguís haciendo todo vos |
| Jue | 15/10 | Reel motion graphic (listo, 12 s) · alternativa a cámara (Joaquín) | ICP1 | Nicho/Autoridad | Mejora continua | 1 · Interacción | La industria trabaja al 58%. ¿Y tu planta? |
| Vie | 16/10 | Carrusel (6) + Historia | ICP2 | Educativo | Calidad-ISO | 1 · Interacción | ¿Te reclaman siempre lo mismo? |

Una pieza de feed por día; la Historia del viernes es capa aparte. Pilares: los 3 de negocio tocados, Calidad-ISO ×2 (el más rezagado de octubre). Mix ICP1/ICP2: 2/2.

## 2. Análisis: dónde la versión anterior se salió del motor

| # | Desvío | Regla del motor | Piezas afectadas | Corrección |
|---|---|---|---|---|
| 1 | Acento cian oscuro en la pieza de agua | ISO 14001 / agroindustria → Verde Salvia; Cian solo en el CTA | 13/10 | Verde Salvia + CTA en Cian |
| 2 | Hooks de 11 y 14 palabras | Hook ≤ 8 palabras | 13, 14 | 6 y 7 palabras |
| 3 | Eyebrow "Contacto directo" a la vista | Nunca exponer códigos internos (ICP, nombres de modo) | 13, 14 | Eyebrows en lenguaje de cliente |
| 4 | CTA sin frase de acción completa ni palabra clave resaltada | Principio 4.3 | 13, 14, 16 | "Escribinos y hablamos" / "Respondenos esta historia y te contamos más" |
| 5 | Slides con 3-4 líneas de cuerpo | ≤ 3 líneas por slide | 13, 14 | 1-2 líneas |
| 6 | Copys de 120-170 palabras, 8 hashtags, con emojis | IG ≤ 80 palabras, 5 hashtags | 13, 14, 15 | 59-71 palabras, 5 hashtags, sin emojis |
| 7 | Archivos `slide-N.png` | `Slide NN-NN.png` generado por el motor | 13, 14 | Nombres canónicos |
| 8 | Historia de 6 líneas, CTA mal redactado, encuesta de 3 opciones | Texto corto; CTA "Respondenos esta historia…"; poll IG = 2 opciones | 16 | Historia de 1 headline + sticker Pregunta |
| 9 | **Faltaba la pieza de feed del 15 y la del 16 era solo Historia** | 1 pieza de feed por día | 15, 16 | Reel motion graphic ya renderizado (15) y carrusel nuevo (16) |
| 10 | Dato de capacidad instalada de dic. 2025 (53,8%) | Verificar vigencia (lección del 07/10 y 13/10) | 15 | INDEC julio 2026: 58,2% |
| 11 | Entrega en un único `.md`, sin carpeta por pieza ni checklist | Estructura de `akyra-estrategia-semanal` Paso 4.5 | Semana | Esta carpeta |
| 12 | "85% del agua va al agro" sin fuente confirmada | Verificación de exactitud | 13 | Quitado |

## 3. Pendientes antes de publicar (para vos)
1. **13/10**: abrir la nota de Economía Sustentable y confirmar "hasta 20% menos recursos hídricos para 2050" (no pude leer el texto).
2. **15/10**: contrastar 58,2% en el PDF del INDEC; el reel ya está listo para subir (motion graphic). El guion a cámara queda solo como alternativa si Joaquín prefiere grabarlo.
3. **16/10**: decidir si te sirve el tema de Calidad/reclamos o querés otro; sumar a mano el sticker Pregunta en la Historia.
4. `Ofertas_Activas.md` no está en el proyecto: asumí que no hay Taller de IA con inscripción abierta, por eso ningún CTA nombra "PLANTA" ni invita a anotarse.
5. **Gestión de mensajes:** las piezas del 13 y 14 (Modo 3) van a traer DMs y comentarios de interés real; responderlos con `akyra-mensajes-dm`, no de memoria.

## 4. Chequeo PO-COM-001 (bloques A-D) — resultado
Hook ≤ 8 palabras ✔ · una idea por slide ✔ · CTA con frase completa ✔ · fondo único por pieza ✔ · logo solo en cierre ✔ · sin numeración impresa ✔ · Montserrat/Outfit ✔ · sin "certificación" ✔ · 5 hashtags ✔ · fuentes con "Verificado" ✔ (con las dos salvedades de arriba) · Cian solo en CTA y IA ✔ · Ámbar y Verde nunca juntos ✔.

## 5. Registros a actualizar (los dejo como filas listas; no toqué `Temas_Publicados_AKYRA` ni `Banco_de_Hooks_Reales` del proyecto)

**Temas_Publicados — filas nuevas/corregidas**
| 13/10/2026 | ICP1 | Agua en Mendoza e ISO 14001 (rehecha) | Calidad-ISO | Nicho/Autoridad | Carrusel | Economía Sustentable 08/05/2026 | En uso |
| 14/10/2026 | ICP2 | IA que actúa vs. IA que responde (rehecha) | IA aplicada | Venta educativa | Carrusel | Sin dato externo | En uso |
| 15/10/2026 | ICP1 | Capacidad instalada 58,2% (jul-2026) y Lean — dato actualizado | Mejora continua | Nicho/Autoridad | Reel motion graphic | INDEC jul-2026 | En uso — motion graphic listo |
| 16/10/2026 | ICP2 | El reclamo como dato de calidad (NUEVA) | Calidad-ISO | Educativo | Carrusel | Sin dato externo | En uso |
| 16/10/2026 | Dual | Cierre de semana (Historia, sticker Pregunta) | Transversal/Marca | Humanización/CTA | Historia | — | En uso |

**Banco de Hooks — filas**
| 13/10 | ICP1 | Carrusel | "El agua no te va a esperar" | Afirmación | C | En uso |
| 14/10 | ICP2 | Carrusel | "Usás IA y seguís haciendo todo vos" | Afirmación (dolor) | B | En uso |
| 15/10 | ICP1 | Reel motion graphic | "La industria trabaja al 58%. ¿Y tu planta?" | Dato + pregunta | C | En uso |
| 16/10 | ICP2 | Carrusel | "¿Te reclaman siempre lo mismo?" | Pregunta | B | En uso |

**Balance de pilares octubre tras esta versión:** IA 4 · Calidad-ISO 3 · Lean 4 · Transversal 4 (no cuenta).

## 6. Registro de revisión PO-COM-001 (Anexo A) — lote completo, 13/10/2026

| Pieza | Bloque A Contenido | Bloque B CTA | Bloque C Marca/Visual | Bloque D Estrategia | Correcciones aplicadas en esta revisión |
|---|---|---|---|---|---|
| 13/10 Carrusel agua | ✅ | ✅ | ✅ | ✅ | Slide 3 como pregunta de dolor; bodegas/secaderos nombrados; CTA sin repetir pregunta |
| 14/10 Carrusel IA | ✅ | ✅ | ✅ | ✅ | Hook desde el dolor; ejemplo concreto en slide 5 |
| 15/10 Reel motion | ✅ | ✅ | ✅ (todo en Ámbar, regla de color único del motion) | ✅ | 3 puntos cortos legibles en el tiempo del motor |
| 16/10 Carrusel reclamos | ✅ | ✅ | ✅ | ⚠️ poco anclado a la zona (genérico para cualquier emprendedor) | Hook desde el dolor; CTA con opciones |
| 16/10 Historia | ✅ | ✅ | ✅ | ✅ | — |

**Decisión:** ⚠️ Aprobado con correcciones menores aplicadas — pendiente de aprobación humana (regla 7). Pendientes de fuente: nota de Economía Sustentable (13/10) y PDF del INDEC (15/10).

**Hallazgo para el motor (no se tocó `render.py`):** en `render_reel_motion` el Bloque B queda completo en pantalla solo 0,9 s (`T_B_HOLD_END = … + 0.9`) y el Bloque A ~2 s, sin importar el largo del texto. Con frases de más de 8 palabras no se llegan a leer. Propuesta: que el hold escale con la cantidad de palabras (≈ 0,25 s por palabra) o subir el hold fijo a ~2,5 s.
