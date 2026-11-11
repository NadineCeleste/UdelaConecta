# Guion de demo y casos de verificación

> Duración objetivo: 10–12 minutos. Antes de empezar, levantar el stack y aplicar migraciones
> y seed. Tener dos pestañas: una con la aplicación (`http://localhost:4200`) y otra con n8n
> (`http://localhost:5678`).

## 1. Preparación

```bash
npm run local:up
# Si es la primera vez o cambió el esquema:
docker compose -f infra/local/docker-compose.yml exec backend alembic upgrade head
# El backend con AUTO_SEED=true crea los datos demo; también se puede forzar:
docker compose -f infra/local/docker-compose.yml exec backend python -m app.seeds.seed_demo
# Importar workflows en n8n (una vez)
docker compose -f infra/local/docker-compose.yml exec n8n \
  n8n import:workflow --separate --input=/workflows
```

Credenciales demo (contraseña `Udela1234!`):

- Estudiante: `dev@udelaconecta.edu.ar` (Valentina, con Angular/Python/SQL).
- Empresa: `empresa@udelaconecta.edu.ar`.
- Otros estudiantes: `lucas.fernandez@`, `camila.rios@`, `tomas.acosta@`,
  `julieta.medina@`, `martina.sosa@udelaconecta.edu.ar`.

En n8n, antes de la demo: credencial `Udela-Secret` (header `X-Udela-Secret` con el valor de
`N8N_AUTOMATION_SECRET`), credencial `DeepSeek account` y workflows activos. Si no hay
DeepSeek configurado, la demo funciona igual: se muestra el fallback.

## 2. Guion paso a paso

### Paso 1 — La empresa crea una oferta con requisitos (1:30)

1. Entrar como `empresa@udelaconecta.edu.ar`.
2. Ir a **Mi proyecto → Nueva oferta** (o editar una existente).
3. Completar título, descripción, modalidad y seniority.
4. En **Requisitos del puesto**, agregar:
   - `Python`, nivel `intermedio`, exigencia `excluyente`, tipo `técnica`.
   - `PostgreSQL`, nivel `principiante`, exigencia `deseable`, tipo `técnica`.
   - `Docker`, nivel `principiante`, exigencia `se aprende en el puesto`, tipo `técnica`.
   - `Comunicación`, nivel `principiante`, exigencia `deseable`, tipo `blanda`.
5. Mostrar los chips y el texto de ayuda: “Los requisitos excluyentes son los que la
   empresa necesita desde el inicio…”.

**Qué destacar:** los requisitos son estructurados, no texto libre. Una oferta sin
requisitos se puede publicar, pero la UI avisa que no habrá informe.

### Paso 2 — El estudiante ve el checklist (1:30)

1. Cerrar sesión y entrar como `dev@udelaconecta.edu.ar`.
2. Ir a **Contratos** y abrir una oferta con requisitos (por ejemplo, “Backend FastAPI de
   conciliaciones”, donde ya está postulado).
3. Mostrar:
   - el resumen “Cumplís X de Y requisitos (Z %)”, con chip de nivel;
   - el checklist con estados **Cumple / A capacitar / A reforzar / Se aprende en el
     puesto / A evaluar en entrevista**;
   - el texto “Este análisis se basa en tu perfil declarado. No es una evaluación ni un
     ranking. **Podés postularte igual.**”;
   - el indicador compacto en la tarjeta de la lista.

**Qué destacar:** el botón “Postularme” no se bloquea por falta de requisitos. El orden de
las ofertas no cambia.

### Paso 3 — Postulación e informe de tres secciones (2:00)

1. En una oferta libre, pulsar **Postularme Ahora**.
2. Abrir **Mis postulaciones** y seleccionar la oferta.
3. Mostrar las tres secciones:
   - **Nivel de coincidencia** (porcentaje y “X de Y requisitos compatibles”);
   - **Aptitudes compatibles** (verde);
   - **Aptitudes a capacitar** (ámbar).
4. Mostrar las notas de “Se aprende en el puesto” y “A evaluar en entrevista”.
5. Pulsar **Generar orientación** (o **Regenerar**).

**Qué destacar:** el informe es determinista; la orientación es solo para el estudiante y
no implica rechazo. Si n8n está configurado, el texto viene de DeepSeek; si no, se guarda
el fallback y se muestra igual.

### Paso 4 — La empresa ve el informe determinista (1:30)

1. Volver a entrar como `empresa@udelaconecta.edu.ar`.
2. Abrir la oferta y bajar a **Postulaciones Recibidas**.
3. Mostrar el indicador compacto de cada postulante.
4. Pulsar un postulante para abrir el modal: se ve el mismo informe determinista, con
   compatibles y a capacitar.
5. Señalar que **no** aparece el texto de orientación de IA y que la asignación no se
   deshabilita ni se ordena por porcentaje.

### Paso 5 — n8n: decisión y validación (2:00)

1. Abrir `http://localhost:5678` y el workflow **Udela Conecta – Orientación de
   postulación**.
2. Mostrar la decisión **¿Hay brechas?**:
   - rama sí → **Prompt Orientación → Modelo (DeepSeek) → Validar → ¿Texto válido?**;
   - rama no → **Sin brechas** (mensaje fijo);
   - si el texto es inválido → **Fallback**.
3. Abrir **Validar** y mostrar que rechaza vacío, >600 caracteres y frases como “no
   calificás”, “rechazado”, “no sos apto”, “no cumple”, “no sirve”.
4. Si hay ejecuciones, abrir una y mostrar el texto generado.
5. Mostrar el workflow **Digest de oportunidades**: Schedule lunes 9:00 → HTTP GET
   `/api/automatizacion/digests` → ¿Hay novedades? → Enviar (deshabilitado sin SMTP) /
   Sin novedades.

**Qué destacar:** la IA no calcula el porcentaje. El workflow recibe el resultado ya
calculado por Python.

### Paso 6 — Chatbot y cierre (1:30)

1. Abrir el widget del chat y preguntar, por ejemplo: “¿Qué me falta para la oferta de
   Backend FastAPI?”.
2. Mostrar que el asistente responde con datos del backend (si el workflow del chatbot
   está activo y con credenciales).
3. Cerrar con los principios: la herramienta acerca, no descarta; no hay ranking; la
   empresa decide; el núcleo funciona sin IA.

## 3. Casos de prueba manuales

| # | Caso | Resultado esperado | Cómo verificarlo |
|---|---|---|---|
| 1 | Estudiante con algunas skills se postula a una oferta con requisitos | Postulación registrada; historial con las tres secciones | Valentina → oferta “Backend FastAPI…” → **Mis postulaciones** |
| 2 | Estudiante con todas las skills | 100 %, sin “a capacitar”; orientación breve y positiva | Editar el perfil para declarar todos los requisitos y recargar |
| 3 | Estudiante sin skills | 0 %, todo “a capacitar”; la postulación se registra igual | Crear usuario nuevo sin habilidades o vaciar las de un perfil de prueba |
| 4 | Oferta sin requisitos | “La oferta no especificó requisitos”; no se genera orientación; no rompe | Crear oferta sin requisitos y abrirla como estudiante; `POST orientación` devuelve 400 |
| 5 | Requisito “se aprende en el puesto” | No cuenta como brecha; aparece como oportunidad | Oferta con Docker `se_aprende`; verificar que no está en “a capacitar” |
| 6 | Requisito blando | No se puntúa; aparece “a evaluar en entrevista” | Oferta con Comunicación `blanda`; verificar que no entra en el porcentaje |
| 7 | n8n apagado | La postulación funciona; la orientación usa fallback | `docker compose stop n8n` → generar orientación → estado “sin IA disponible” |
| 8 | IA devuelve texto inválido | Se guarda fallback; no se muestra texto ofensivo | Forzar en n8n un texto vacío/>600/con “rechazado” o simular con un test |
| 9 | Estudiante actualiza su perfil | El indicador sube al recargar; la orientación se puede regenerar | Agregar una habilidad faltante → volver a Contratos → **Regenerar** |
| 10 | Empresa ve postulantes | Ve indicador y listas; no ve la orientación de IA | Abrir el modal de un postulante como empresa |
| 11 | Otro estudiante intenta ver el informe | 403 | `GET /api/postulaciones/{id}/orientacion` con token de otro estudiante |
| 12 | Gerente intenta ver el informe de un estudiante | 403 | Llamar el endpoint de orientación con token de gerente |
| 13 | Oferta con muchos postulantes | La vista no se rompe; el cálculo es correcto | Agregar varios emails al array `postulaciones` o postularse con varias cuentas |
| 14 | Seed ejecutado dos veces | No duplica datos | `python -m app.seeds.seed_demo` dos veces; contar 11 ofertas y 11 con requisitos |

Los casos 1–14 también están cubiertos, en lo que corresponde, por
`apps/backend/tests/test_compatibilidad.py` y
`apps/backend/tests/test_postulaciones_informe.py`.

## 4. Casos de error para mostrar

1. **n8n apagado.** Detener el servicio y generar la orientación: se guarda el fallback con
   estado `fallback`; la postulación y el informe determinista siguen funcionando.
2. **Oferta sin requisitos.** El detalle muestra “La oferta no especificó requisitos”; el
   endpoint de orientación responde 400 con un mensaje explicativo, sin romper la UI.
3. **Texto de IA inválido.** n8n usa **Fallback**; el backend también valida y guarda
   fallback si la respuesta no cumple. Nunca se muestra un texto con frases de rechazo.
4. **Perfil sin skills.** 0 % y todo “a capacitar”; el botón de postulación sigue activo.
5. **Migración sin aplicar.** `alembic upgrade head`; `alembic check` debe decir “No new
   upgrade operations detected”.

## 5. Frases para cerrar la demo

- “El porcentaje lo calcula Python puro; la IA solo escribe una orientación.”
- “No hay ranking ni puntaje global: el informe es por postulación.”
- “La empresa ve el mismo resumen determinista, no el texto de IA.”
- “Si la IA falla, hay fallback y la postulación nunca se bloquea.”
- “La decisión de asignar sigue siendo de la empresa.”
