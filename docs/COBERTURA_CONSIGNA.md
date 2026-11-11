# Matriz de cobertura de la consigna

> Cada requisito de la guía con su evidencia concreta en el repositorio. Los tests se
> ejecutan con `pytest`; la UI se verifica con `npm run build` y los casos de
> [`DEMO.md`](./DEMO.md).

## 1. Requisitos técnicos

| Requisito | Estado | Evidencia |
|---|---|---|
| **4.1 Python: módulos, funciones, validación y excepciones** | Cumplido | `apps/backend/app/dominio/compatibilidad.py` (normalización, sinónimos, sanitización, comparación, fallback); tests en `apps/backend/tests/test_compatibilidad.py` (12) |
| **4.2 FastAPI: ≥ 5 endpoints funcionales** | Cumplido | `GET /api/mis-postulaciones`, `GET /api/postulaciones/{id}/orientacion`, `POST /api/postulaciones/{id}/orientacion`, `POST /api/automatizacion/postulaciones/{id}/{email}/orientacion`, `GET /api/automatizacion/digests`; además `GET /api/contratoslibres` y `GET /api/contratos/{email}` enriquecidos |
| **4.3 Angular: formularios y resultados** | Cumplido | `views/formcreatecontract` (constructor de requisitos), `componentes/contrato-detail` (checklist, informe de 3 secciones, orientación, modal de postulantes), `componentes/contratos` (indicador e historial) |
| **4.4 n8n: ≥ 3 workflows con decisión** | Cumplido | `infra/n8n/udela-chatbot.json`, `udela-orientacion.json` (IF “¿Hay brechas?” + IF “¿Texto válido?”), `udela-digest.json` (IF “¿Hay novedades?”) |
| **4.5 IA integrada, justificación y supervisión** | Cumplido | Orientación por postulación; prompt acotado en `udela-orientacion.json`; validación en n8n y backend; fallback determinista; texto visible solo para el estudiante; `docs/ARQUITECTURA.md` §2.4 y `docs/BITACORA_IA.md` |
| **4.6 Persistencia** | Cumplido | PostgreSQL 16; `contrato.requisitos` (JSONB) y tabla `informe_postulacion`; migración `0004_requisitos_e_informes.py`; seed idempotente |
| **4.7 Docker** | Cumplido | `infra/local/docker-compose.yml` con `postgres`, `backend`, `frontend`, `adminer` y `n8n`; variables y volúmenes documentados |
| **5. Bitácora de IA** | Cumplido | `docs/BITACORA_IA.md` |
| **6. Repositorio** | Cumplido | `README.md` (sección “Compatibilidad y orientación”), workflows JSON, seed, `apps/backend/requirements.txt`, `.gitignore`, `docs/ARQUITECTURA.md` |
| **7. Verificación** | Cumplido | `docs/DEMO.md` con guion y 14 casos; suite de tests; build de Angular |
| **9. Entrega** | Cumplido | README actualizado, diagramas Mermaid, workflows, bitácora, responsabilidades y esta matriz |
| **11. Evaluación** | Cumplido | Proceso completo empresa → oferta → postulación → informe → orientación → vista de empresa, en Docker, con Python/FastAPI/Angular/n8n/IA |

## 2. Principios no negociables

| Principio | Cómo se garantiza | Dónde verificarlo |
|---|---|---|
| El cálculo lo hace Python, sin LLM/embeddings | `comparar()` solo usa `unicodedata` y `typing`; no hay imports de IA en `dominio/` | `test_compatibilidad.py`; revisar imports del módulo |
| La IA no calcula el indicador | n8n recibe `coincidencia`, `compatibles` y `a_capacitar` ya calculados | `routers/postulaciones.py` (payload) y `udela-orientacion.json` |
| La IA no evalúa blandas | Las blandas van a `blandas`/checklist con estado `blanda`; nunca al porcentaje | `test_blanda_no_cuenta_en_el_total` |
| La postulación nunca se bloquea | El botón no consulta requisitos; solo se bloquea si la oferta está ocupada | `contrato-detail.html` y flujo existente de postulación |
| No hay ranking global | No se persiste puntaje ni se ordena por coincidencia | `GET /api/contratoslibres` conserva el orden; `mis-postulaciones` ordena por `Contrato.id.desc()` |
| No se dice “no calificás”/“rechazado” | Textos de UI y validación de frases prohibidas | `test_postulaciones_informe.py`; `FRASES_RECHAZO`; textos del detalle |
| La empresa decide | La asignación no se automatiza ni se ordena por porcentaje | Modal de postulantes; endpoint de asignación sin cambios |
| La orientación es solo del estudiante | Endpoints con 403 para otro estudiante o gerente; la empresa no recibe `orientacion` | `test_estudiante_no_ve_orientacion_ajena`, `test_gerente_no_ve_orientacion_de_estudiante` |
| El núcleo funciona sin n8n/IA | `POST orientación` guarda fallback si no hay URL o falla la llamada | `test_orientacion_sin_n8n_guarda_fallback` |
| Los datos son declarados | Texto obligatorio “Este análisis se basa en tu perfil declarado.” | `contrato-detail.html` y `mis-postulaciones` |
| No se usan datos sensibles | El payload a n8n y el informe no incluyen teléfono, fecha de nacimiento ni género | `test_informe_no_incluye_datos_sensibles` |
| No ordenar ofertas por coincidencia | El backend no ordena por `mi_resultado` | `GET /api/contratoslibres` |
| No ocultar ofertas | No hay filtro por compatibilidad | `GET /api/contratoslibres` devuelve todas las libres |
| No mostrar un porcentaje grande y rojo antes de postular | Indicador compacto y paleta verde/ámbar/gris/azul | `contratos.css`, `contrato-detail.css` |
| No enviar el texto de IA a la empresa | `resultados_postulantes` solo incluye el resultado determinista | `test_empresa_ve_resultados_solo_en_sus_contratos` |
| No agregar puntaje acumulado | No hay columnas de score; el resultado se calcula al vuelo | `entities.py`; `comparar()` en cada request |
| No modificar el flujo de asignación | Se reutiliza el endpoint existente; solo se agrega el informe | `routers/contratos.py` |

## 3. Trazabilidad de tests

### Dominio (`tests/test_compatibilidad.py`, 12 tests)

| Test | Qué cubre |
|---|---|
| `test_perfil_sin_habilidades_todo_a_capacitar` | 0 %, todas las técnicas a capacitar |
| `test_perfil_completo_da_cien_y_nivel_alta` | 100 %, nivel alta |
| `test_nivel_menor_es_parcial` | Nivel declarado menor al mínimo → `parcial` |
| `test_sinonimos_y_tildes` | Normalización de nombres |
| `test_sinonimo_de_js_y_powerbi` | Sinónimos acotados |
| `test_se_aprende_no_cuenta_en_el_total` | `se_aprende` fuera del porcentaje |
| `test_blanda_no_cuenta_en_el_total` | Blandas fuera del porcentaje |
| `test_oferta_sin_requisitos_no_divide_por_cero` | `sin_requisitos` |
| `test_requisito_sin_nombre_no_rompe_y_se_registra` | Requisitos inválidos |
| `test_requisitos_y_habilidades_duplicadas_no_duplican` | Deduplicación |
| `test_sanitizar_requisitos_aplica_defaults_y_descarta_vacios` | Sanitización en el borde |
| `test_fallback_sin_y_con_brechas` | Texto determinista sin/con brechas |

### API (`tests/test_postulaciones_informe.py`, 16 tests)

| Test | Qué cubre |
|---|---|
| `test_mis_postulaciones_devuelve_resultado_determinista` | Historial con resultado |
| `test_orientacion_sin_n8n_guarda_fallback` | Fallback sin n8n |
| `test_orientacion_con_n8n_guarda_generado` | Integración con n8n |
| `test_regenerar_actualiza_el_mismo_informe` | Upsert por postulación |
| `test_respuesta_invalida_de_ia_usa_fallback` | Validación de frases prohibidas |
| `test_texto_demasiado_largo_usa_fallback` | Límite de 600 |
| `test_estudiante_no_ve_orientacion_ajena` | 403 entre estudiantes |
| `test_gerente_no_ve_orientacion_de_estudiante` | 403 para gerente |
| `test_empresa_ve_resultados_solo_en_sus_contratos` | Autorización por dueño; sin texto IA |
| `test_contratoslibres_trae_mi_resultado` | `mi_resultado` al vuelo |
| `test_oferta_sin_requisitos_no_rompe_ni_genera_orientacion` | 400 explicativo |
| `test_estudiante_sin_postulaciones_recibe_lista_vacia` | Historial vacío |
| `test_informe_no_incluye_datos_sensibles` | Privacidad |
| `test_automatizacion_exige_secreto` | Header secreto |
| `test_digests_devuelve_oportunidades_por_estudiante` | Digest > 60 %, top 3 |
| `test_automatizacion_guarda_orientacion_con_secreto` | Endpoint para n8n |

## 4. Verificación de integración

| Verificación | Comando | Resultado |
|---|---|---|
| Tests backend | `pytest -q` | 86 aprobados |
| Migración | `alembic upgrade head` + `alembic check` | Sin operaciones pendientes |
| Seed idempotente | `python -m app.seeds.seed_demo` dos veces | 11 ofertas, 11 con requisitos, sin duplicados |
| Build frontend | `npm run build` | Compilación correcta |
| Importación n8n | `n8n import:workflow --separate --input=/workflows` | 3 workflows importados |
| Docker Compose | `docker compose config` | Configuración válida |

## 5. Fuera del alcance (no implementado a propósito)

- Ranking de candidatos o tabla de posiciones.
- Puntaje global acumulado del estudiante.
- Evaluación automática de habilidades blandas.
- Rechazo automático de postulaciones.
- Recomendación automática de contratación.
- Matching semántico con embeddings o modelos de lenguaje.
- Nuevas rutas de Angular para una “página de scoring”.
