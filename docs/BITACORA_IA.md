# Bitácora de IA — TP2

> Registro de cómo se usó IA en esta entrega. No se inventa participación: la
> implementación se realizó en una sesión de desarrollo asistida por IA, a partir de la
> guía funcional y las decisiones de producto del equipo. Cada cambio se verificó con
> tests, build y revisión del diff antes de commitear.

## 1. Herramientas usadas

| Herramienta | Dónde | Para qué |
|---|---|---|
| **DeepSeek Chat** (asistente de código en el entorno de desarrollo) | Sesión de implementación | Leer la guía, proponer el diseño, escribir código y tests, ejecutar verificaciones y redactar documentación |
| **DeepSeek** (`deepseek-chat`) vía n8n | Runtime de la orientación | Redactar el texto de orientación a partir del resultado determinista |
| **n8n 1.70** | Runtime de automatización | Orquestar la decisión “¿Hay brechas?”, validar el texto y preparar el digest |
| **pytest + httpx** | Verificación | Tests unitarios del dominio y de la API con SQLite en memoria y `MockTransport` |
| **Angular CLI / Nx** | Verificación | `npm run build` para validar plantillas y tipos |

No se usaron embeddings, modelos de similitud semántica ni servicios de scoring. La IA no
interviene en el cálculo.

## 2. Para qué se usó la IA

- Traducir la guía `GUIA_IMPLEMENTACION.md` a un plan por fases.
- Escribir el comparador determinista y sus casos de prueba.
- Escribir la migración `0004`, el seed y los endpoints de informe/orientación/digest.
- Escribir los componentes y estilos de Angular para requisitos, checklist, informe y
  vista de postulantes.
- Generar y validar los workflows exportables de n8n.
- Redactar esta documentación y el guion de demo.
- Revisar textos para evitar lenguaje de rechazo y referencias a ranking.

## 3. Decisiones técnicas tomadas con ayuda de IA

1. **Dominio puro y aislado.** `app/dominio/compatibilidad.py` solo usa `unicodedata` y
   `typing`. Así se puede testear sin base de datos, sin red y sin n8n.
2. **Requisitos en JSONB.** Se descartó una tabla normalizada de requisitos para no romper
   el contrato actual de `contrato` y simplificar el seed. La sanitización se hace en el
   borde de la API.
3. **Resultado calculado al vuelo.** No se persiste el porcentaje: se evita un dato que
   envejece y se garantiza que el indicador suba cuando el estudiante mejora su perfil.
4. **Orientación con doble validación.** n8n valida longitud y frases prohibidas; el
   backend vuelve a validar antes de guardar. Si algo falla, se guarda fallback.
5. **Un registro por postulación.** `UniqueConstraint(contrato_id, estudiante_email)` y
   upsert para que “Regenerar” actualice, no duplique.
6. **La empresa no ve la orientación de IA.** Recibe el mismo informe determinista. Esto
   evita usar el texto generado como filtro de selección.
7. **Sin ranking ni bloqueo.** Se mantiene el orden original de las ofertas y el botón
   “Postularme” sigue disponible aunque falten requisitos.
8. **n8n opcional.** La ausencia de n8n no rompe la postulación ni el informe; solo cambia
   el estado de la orientación a `fallback`.

## 4. Dificultades y correcciones

| Dificultad | Corrección |
|---|---|
| El entorno de la sesión no tenía dependencias Python instaladas | Los tests se ejecutaron dentro de la imagen Docker `udela-local-backend:latest`, montando `apps/backend` |
| Un test esperaba “no es una evaluación” y el fallback dice “no una evaluación” | Se ajustó la aserción al texto real del fallback |
| `alembic check` necesitaba PostgreSQL real | Se levantó un contenedor temporal `postgres:16-alpine`, se aplicó `upgrade head`, se corrió `check` y se validó el seed dos veces |
| El CLI de n8n 1.70 no importa un workflow exportado como objeto único | Se documentó `n8n import:workflow --separate --input=/workflows`; los archivos incluyen `active: false` para satisfacer la base de n8n |
| El schedule semanal esperaba un array en `triggerAtDay` | Se corrigió a `[1]` (lunes) y se reimportaron los tres workflows |
| El front necesitaba mostrar la orientación sin recargar toda la página | Se agregó el output `orientacionActualizada` y un `Map` en `Contratos` para conservar la orientación por contrato |
| Riesgo de mostrar textos ofensivos generados por IA | Validación de ≤600 caracteres y frases de rechazo en n8n **y** en el backend; fallback determinista |
| Riesgo de que el informe se lea como ranking | Textos explícitos (“No es una evaluación ni un ranking”), sin orden por coincidencia y sin posición |

## 5. Verificación realizada

- `pytest -q` en Docker: **86 tests aprobados** (12 de dominio + 16 de informe/orientación
  + suite existente).
- `alembic upgrade head` y `alembic check`: sin operaciones nuevas detectadas.
- Seed ejecutado dos veces: 11 ofertas, 11 con requisitos, 6 estudiantes y 4 gerentes, sin
  duplicados.
- `npm run build`: compilación de producción correcta (solo advertencias de presupuesto de
  CSS preexistentes en otros componentes).
- n8n 1.70: los tres workflows se importan correctamente (`Successfully imported 3
  workflows`).
- Revisión de los textos de la UI contra la lista de textos obligatorios.

## 6. Qué no se delegó a la IA

- **El cálculo de compatibilidad:** es Python puro, con reglas explícitas y tests.
- **Las decisiones de producto:** qué se muestra, a quién, y qué lenguaje se usa.
- **La validación de seguridad:** autorización por dueño, secreto de automatización,
  exclusión de datos sensibles.
- **La aprobación final de la demo:** el equipo debe revisar el guion y ejecutarlo en su
  entorno.
- **La configuración de credenciales reales:** DeepSeek, Header Auth y SMTP se configuran
  en n8n; el repositorio solo referencia nombres de credenciales.

## 7. Prompts relevantes

El prompt de orientación está en `infra/n8n/udela-orientacion.json` (nodo **Prompt
Orientación**) y en `docs/ARQUITECTURA.md`. Sus reglas principales:

- no decir que la persona no califica, será rechazada o no es apta;
- no inventar requisitos;
- no evaluar habilidades blandas;
- no prometer resultados;
- empezar por la brecha más importante y sugerir un paso concreto;
- aclarar que es una orientación, no una evaluación;
- máximo 600 caracteres, texto plano, español rioplatense.

El chatbot existente no se modificó en su lógica de negocio; solo se agregó `active: false`
al JSON exportado para que el CLI de n8n 1.70 pueda importarlo junto con los otros dos.
