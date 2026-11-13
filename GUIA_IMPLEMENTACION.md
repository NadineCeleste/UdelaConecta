# Guía de implementación — Comparador de compatibilidad y orientación

**Proyecto:** Udela Conecta
**Documento:** guía de modificaciones para la entrega del TP2
**Fecha:** 2026-11-11
**Estado:** propuesta para ejecutar
**Relacionado:** `consignas.docx`, `context_agent/AGENTS.md`, `context_agent/backend.md`,
`context_agent/endpoint.md`, `context_agent/n8n.md`

---

## 0. Objetivo

Implementar el proceso que hoy falta en la plataforma:

1. La empresa publica una oferta con **requisitos específicos**.
2. El estudiante se postula, aunque no cumpla todos.
3. El sistema compara su perfil con los requisitos usando **Python puro**.
4. Muestra un **informe de situación** con tres secciones:
   - nivel de coincidencia,
   - aptitudes compatibles,
   - aptitudes a capacitar.
5. Muestra una **orientación breve generada por IA** para el estudiante, dentro del
   historial de postulaciones, sin implicar rechazo.
6. Automatiza con n8n la generación de la orientación y la comunicación de resultados.

El resultado esperado es una herramienta que **acerca** estudiantes y empresas. No es un
ranking, no es un sistema de puntos y no decide el futuro de nadie.

---

## 1. Principios no negociables

Estas reglas deben respetarse en el código, en los textos y en la demo:

- **El cálculo lo hace Python.** Sin LLM, sin embeddings, sin Hugging Face.
- **La IA no calcula el indicador.** Solo redacta una orientación a partir del resultado.
- **La IA no evalúa habilidades blandas.** No las puntúa, no las infiere.
- **La postulación nunca se bloquea.** El botón “Postularme” siempre está disponible.
- **No hay ranking global ni tabla de posiciones.** El informe es por postulación.
- **No se muestra “no calificás” ni “rechazado”.** El lenguaje es de orientación.
- **La empresa decide.** El sistema informa; no filtra ni rechaza.
- **La orientación de IA es para el estudiante.** La empresa ve el informe determinista.
- **El núcleo funciona sin n8n y sin IA.** Si fallan, se muestra un fallback.
- **Los datos son declarados.** El informe debe aclarar que se basa en el perfil declarado.
- **No se usan datos sensibles.** Nada de edad, género, nacionalidad ni inferencias.

### 1.1 Qué NO hacer

- No ordenar las ofertas por coincidencia por defecto; el orden actual se mantiene.
- No ocultar ofertas “para las que no calificás”.
- No mostrar un porcentaje grande y rojo antes de postularse.
- No enviar el texto de IA a la empresa como criterio de selección.
- No agregar campos de “puntaje” acumulados por usuario.
- No modificar el flujo de asignación existente.

---

## 2. Alcance

### 2.1 Dentro del alcance

| # | Cambio | Capa |
|---|---|---|
| 1 | Requisitos estructurados en `contrato` | Backend / datos |
| 2 | Comparador determinista y tests | Backend / dominio |
| 3 | Endpoints de informe y orientación | Backend / API |
| 4 | Formulario de oferta con requisitos | Frontend |
| 5 | Checklist de requisitos en el detalle de la oferta | Frontend |
| 6 | Informe de tres secciones en “Mis postulaciones” | Frontend |
| 7 | Informe determinista por postulante para la empresa | Frontend / API |
| 8 | Orientación breve con IA + fallback | n8n / backend |
| 9 | Workflow de comunicación de resultados | n8n |
| 10 | n8n en Docker Compose | Infra |
| 11 | Documentación de entrega | Docs |

### 2.2 Fuera del alcance

- Ranking de candidatos.
- Puntaje global del estudiante.
- Evaluación automática de habilidades blandas.
- Rechazo automático de postulaciones.
- Recomendación automática de contratación.
- Matching semántico con modelos de lenguaje o embeddings.
- Nuevas rutas de Angular para una “página de scoring”.

---

## 3. Arquitectura objetivo

```
┌─────────────────────────────┐
│ Angular                     │
│  · oferta: requisitos       │
│  · historial: informe       │
│  · postulantes: informe     │
└──────────────┬──────────────┘
               │ HTTP JSON
┌──────────────▼──────────────┐
│ FastAPI                     │
│  · dominio/compatibilidad.py│  ← Python puro, sin IA
│  · routers/postulaciones.py │
│  · routers/contratos.py     │
└───────┬──────────────┬──────┘
        │              │
        │              └──────────────► PostgreSQL
        │                               (requisitos + informes IA)
        │
┌───────▼──────────────┐
│ n8n (opcional)       │
│  · workflow chatbot  │
│  · workflow orientación │
│  · workflow digest   │
└───────┬──────────────┘
        │
┌───────▼──────────────┐
│ IA (DeepSeek/Ollama) │
│  solo redacta       │
└─────────────────────┘
```

Regla de dependencia: **el comparador no importa nada de n8n ni de IA**. n8n consume los
endpoints; la IA consume el resultado del comparador.

---

## 4. Fase 0 — Preparación

- [ ] Crear rama `feat/compatibilidad` desde `main`.
- [ ] Verificar que el proyecto levante antes de tocar código:
  ```bash
  npm install
  npm run local:up
  npm run test:back
  npm run build
  ```
- [ ] Anotar en `context_agent/AGENTS.md` que se inicia el proceso de compatibilidad.
- [ ] Hacer commits pequeños por fase; no una única carga al final.

**Criterio de aceptación:** la app actual funciona igual antes de empezar.

---

## 5. Fase 1 — Datos

### 5.1 Modelo `Contrato`

Archivo: `apps/backend/app/models/entities.py`

Agregar a `Contrato`:

```python
requisitos: Mapped[list] = mapped_column(JsonType, default=list, nullable=False)
```

Cada requisito tiene esta forma:

```json
{
  "nombre": "Angular",
  "nivel_minimo": "intermedio",
  "exigencia": "excluyente",
  "tipo": "tecnica"
}
```

Valores permitidos:

| Campo | Valores | Default |
|---|---|---|
| `nombre` | texto libre, obligatorio | — |
| `nivel_minimo` | `principiante`, `intermedio`, `avanzado` | `principiante` |
| `exigencia` | `excluyente`, `deseable`, `se_aprende` | `deseable` |
| `tipo` | `tecnica`, `blanda` | `tecnica` |

Reglas:

- `tipo="blanda"` **no se puntúa**; se lista como “a evaluar en entrevista”.
- `exigencia="se_aprende"` **no se puntúa**; se lista como oportunidad.
- Solo `excluyente` y `deseable` de tipo `tecnica` entran al indicador.

### 5.2 Modelo `InformePostulacion`

Archivo: `apps/backend/app/models/entities.py`

```python
class InformePostulacion(Base):
    __tablename__ = "informe_postulacion"
    __table_args__ = (
        UniqueConstraint("contrato_id", "estudiante_email", name="uq_informe_postulacion"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    contrato_id: Mapped[int] = mapped_column(
        ForeignKey("contrato.id", ondelete="CASCADE"), nullable=False, index=True
    )
    estudiante_email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    texto: Mapped[str] = mapped_column(Text, default="")
    modelo: Mapped[str] = mapped_column(String(60), default="")
    estado: Mapped[str] = mapped_column(String(20), default="pendiente")
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_ahora)
    actualizado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_ahora, onupdate=_ahora
    )
```

Estados: `pendiente`, `generado`, `fallback`.

Exportar en `apps/backend/app/models/__init__.py`.

> **Decisión:** el indicador **no se persiste**. Se calcula al vuelo con el perfil actual.
> Solo se persiste el texto de IA, que es lo que cuesta generarlo. Si el estudiante mejora
> su perfil, el indicador sube automáticamente y la orientación se puede regenerar.

### 5.3 Migración `0004`

Archivo nuevo: `apps/backend/alembic/versions/0004_requisitos_e_informes.py`

Pasos:

1. Agregar `requisitos` a `contrato` como nullable.
2. Rellenar las filas existentes con `[]`.
3. Dejar la columna `NOT NULL`.
4. Crear `informe_postulacion` con FK, unique e índices.
5. En `downgrade`, borrar la tabla y la columna.

Esqueleto:

```python
revision = "0004"
down_revision = "0003"

JsonType = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")

def upgrade() -> None:
    op.add_column("contrato", sa.Column("requisitos", JsonType, nullable=True))
    op.execute("UPDATE contrato SET requisitos = '[]' WHERE requisitos IS NULL")
    op.alter_column("contrato", "requisitos", nullable=False)

    op.create_table(
        "informe_postulacion",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("contrato_id", sa.Integer(), nullable=False),
        sa.Column("estudiante_email", sa.String(255), nullable=False),
        sa.Column("texto", sa.Text(), nullable=False),
        sa.Column("modelo", sa.String(60), nullable=False),
        sa.Column("estado", sa.String(20), nullable=False),
        sa.Column("creado_en", sa.DateTime(timezone=True), nullable=False),
        sa.Column("actualizado_en", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["contrato_id"], ["contrato.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("contrato_id", "estudiante_email", name="uq_informe_postulacion"),
    )
    op.create_index("ix_informe_postulacion_contrato_id", "informe_postulacion", ["contrato_id"])
    op.create_index(
        "ix_informe_postulacion_estudiante_email", "informe_postulacion", ["estudiante_email"]
    )
```

Verificar:

```bash
cd apps/backend
poetry run alembic upgrade head
poetry run alembic check
```

### 5.4 Seed

Archivo: `apps/backend/app/seeds/seed_demo.py`

Agregar `requisitos` a cada una de las 11 ofertas. Mapeo sugerido:

| Oferta | Requisitos |
|---|---|
| Frontend Angular para el panel de pagos | Angular intermedio (excluyente), TypeScript intermedio (excluyente), CSS avanzado (deseable), Testing principiante (deseable), Docker principiante (se aprende), Trabajo en equipo (blanda) |
| Backend FastAPI de conciliaciones | Python intermedio (excluyente), FastAPI intermedio (excluyente), SQL intermedio (deseable), PostgreSQL principiante (deseable), Docker principiante (se aprende) |
| QA de la app móvil | Testing manual intermedio (excluyente), Playwright principiante (deseable), Comunicación (blanda) |
| Data Analyst Trainee para riesgo crediticio | Python intermedio (excluyente), SQL intermedio (excluyente), Pandas principiante (deseable), Power BI principiante (deseable) |
| Desarrollador/a Python para sensores IoT | Python intermedio (excluyente), PostgreSQL principiante (deseable), Docker principiante (se aprende), MQTT principiante (se aprende) |
| Data Engineer Junior | Python intermedio (excluyente), SQL intermedio (excluyente), Inglés B1 (deseable), Docker principiante (se aprende) |
| Frontend React para turnos online | React intermedio (excluyente), TypeScript intermedio (excluyente), CSS intermedio (deseable), Accesibilidad principiante (deseable) |
| Soporte técnico y QA manual | Testing manual principiante (excluyente), Comunicación (blanda), Inglés B1 (deseable) |
| Desarrollador/a Mobile Flutter | Flutter intermedio (excluyente), Dart intermedio (deseable), Firebase principiante (se aprende) |
| DevOps Junior: Docker y CI/CD | Docker intermedio (excluyente), Linux intermedio (excluyente), GitHub Actions principiante (deseable), Python principiante (deseable) |
| Analista funcional trainee | UML principiante (excluyente), Testing manual principiante (deseable), Comunicación (blanda), Inglés B1 (deseable) |

El seed debe seguir siendo idempotente. Si la oferta ya existe, no se toca. Para las
ofertas demo nuevas, `requisitos` viaja dentro del diccionario `oferta` y lo toma
`Contrato(**oferta)`.

**Criterios de aceptación:**

- [ ] `alembic upgrade head` funciona en una base limpia.
- [ ] `alembic check` no detecta diferencias.
- [ ] El seed corre dos veces sin duplicar.
- [ ] Las 11 ofertas demo tienen requisitos.
- [ ] Una oferta creada antes de la migración muestra `requisitos: []` y no rompe.

---

## 6. Fase 2 — Dominio: comparador en Python

### 6.1 Archivos

- `apps/backend/app/dominio/__init__.py` (nuevo)
- `apps/backend/app/dominio/compatibilidad.py` (nuevo)
- `apps/backend/tests/test_compatibilidad.py` (nuevo)

No importar FastAPI, SQLAlchemy ni nada de n8n en este módulo. Debe ser testeable con
diccionarios y objetos simples.

### 6.2 Reglas

1. Normalizar nombres: minúsculas, sin tildes, sin espacios extra.
2. Aplicar un diccionario de sinónimos:
   - `js` → `javascript`
   - `ts` → `typescript`
   - `postgres` → `postgresql`
   - `node` / `node.js` → `nodejs`
   - `powerbi` → `power bi`
   - `github actions` / `gh actions` → `github actions`
3. Mapear niveles: `principiante=1`, `básico=1`, `intermedio=2`, `avanzado=3`, `experto=4`.
4. Para cada requisito:
   - Si `tipo == "blanda"` → `blandas`, no cuenta.
   - Si `exigencia == "se_aprende"` → `se_aprenden`, no cuenta.
   - Si la skill no está declarada → `a_capacitar`, motivo `no_declarada`.
   - Si está declarada con nivel menor al mínimo → `a_capacitar`, motivo `nivel_menor`.
   - Si está declarada con nivel suficiente → `compatibles`.
5. El indicador es:
   ```python
   total = len(compatibles) + len(a_capacitar)
   coincidencia = round(100 * len(compatibles) / total) if total else 0
   ```
6. Etiqueta cualitativa:
   - `sin_requisitos` si `total == 0`
   - `alta` si `coincidencia >= 75`
   - `media` si `coincidencia >= 40`
   - `baja` si `coincidencia < 40`
7. Si el perfil no tiene habilidades, no lanzar excepción: devolver todo en
   `a_capacitar` y `coincidencia=0`.
8. Si un requisito no tiene `nombre`, ignorarlo y registrar una advertencia en el
   resultado (`requisitos_invalidos`).

### 6.3 Contrato de salida

```python
{
    "coincidencia": 25,
    "nivel": "baja",
    "total_requisitos": 4,
    "total_compatibles": 1,
    "sin_requisitos": False,
    "compatibles": [
        {"nombre": "Angular", "nivel": "intermedio"}
    ],
    "a_capacitar": [
        {
            "nombre": "TypeScript",
            "nivel_minimo": "intermedio",
            "motivo": "no_declarada"
        }
    ],
    "se_aprenden": ["Docker"],
    "blandas": ["Trabajo en equipo"],
    "checklist": [
        {
            "nombre": "Angular",
            "estado": "cumple",
            "nivel_minimo": "intermedio",
            "nivel_declarado": "intermedio"
        },
        {
            "nombre": "TypeScript",
            "estado": "falta",
            "nivel_minimo": "intermedio",
            "nivel_declarado": None
        },
        {
            "nombre": "Docker",
            "estado": "se_aprende",
            "nivel_minimo": "principiante",
            "nivel_declarado": None
        }
    ],
    "requisitos_invalidos": []
}
```

El `checklist` es lo que consume la UI para mostrar el detalle. Los estados posibles son:
`cumple`, `falta`, `parcial`, `se_aprende`, `blanda`.

### 6.4 Tests mínimos

- [ ] Perfil sin habilidades → 0 %, todo en `a_capacitar`.
- [ ] Perfil con todas las skills y niveles → 100 %, `nivel="alta"`.
- [ ] Skill con nivel menor → `parcial`, motivo `nivel_menor`.
- [ ] Sinónimos y tildes: `TS` contra `TypeScript`, `Postgres` contra `PostgreSQL`.
- [ ] `se_aprende` no cuenta en el total.
- [ ] `blanda` no cuenta en el total.
- [ ] Oferta sin requisitos → `sin_requisitos`, `coincidencia=0`, sin división por cero.
- [ ] Requisito sin nombre → no rompe y aparece en `requisitos_invalidos`.
- [ ] Skills duplicadas → no duplican el resultado.

**Criterio de aceptación:** `poetry run pytest tests/test_compatibilidad.py` pasa.

---

## 7. Fase 3 — API

### 7.1 Endpoints nuevos

Crear `apps/backend/app/routers/postulaciones.py` y registrarlo en `app/main.py`.

| Método | Ruta | Quién | Qué hace |
|---|---|---|---|
| GET | `/api/mis-postulaciones` | Estudiante | Devuelve sus postulaciones con contrato, resultado y orientación |
| GET | `/api/postulaciones/{contrato_id}/orientacion` | Estudiante | Lee la orientación guardada |
| POST | `/api/postulaciones/{contrato_id}/orientacion` | Estudiante | Genera o regenera la orientación con IA; si falla, guarda fallback |
| POST | `/api/automatizacion/postulaciones/{contrato_id}/{email}/orientacion` | n8n | Guarda la orientación generada por n8n (header secreto; opcional si se usa llamada síncrona) |
| GET | `/api/automatizacion/digests` | n8n | Devuelve oportunidades por estudiante para el workflow de comunicación |

### 7.2 Enriquecer contratos

Archivo: `apps/backend/app/routers/contratos.py`

- `GET /api/contratoslibres`: agregar `user: CurrentUser = Depends(get_current_user)`.
  Si el usuario es estudiante, agregar `mi_resultado` a cada contrato:
  ```python
  perfil = await db.scalar(select(Estudiante).where(Estudiante.email == user.email))
  datos["mi_resultado"] = comparar(perfil, c.requisitos) if perfil else None
  ```
- `GET /api/contratos/{email_gerente}`: si el usuario es el dueño, agregar
  `resultados_postulantes` a cada contrato:
  ```python
  resultados = []
  for email in c.postulaciones or []:
      estudiante = estudiantes_por_email.get(email)
      resultados.append({
          "email": email,
          "nombre": ...,
          "resultado": comparar(estudiante, c.requisitos),
      })
  datos["resultados_postulantes"] = resultados
  ```
  Hacer una sola consulta a `Estudiante` con `email.in_(emails)` para evitar N+1.

- Mantener el resto de la respuesta igual. No cambiar el orden ni los filtros actuales.

### 7.3 `GET /api/mis-postulaciones`

Respuesta:

```json
{
  "message": "Mis postulaciones",
  "count": 1,
  "data": [
    {
      "contrato": { "...": "contrato completo" },
      "resultado": { "...": "salida de comparar()" },
      "orientacion": {
        "texto": "Para esta búsqueda te conviene reforzar...",
        "estado": "generado",
        "modelo": "deepseek-chat",
        "actualizado_en": "2026-11-11T12:00:00+00:00"
      }
    }
  ]
}
```

Reglas:

- Solo el estudiante autenticado ve sus postulaciones.
- Incluir contratos libres y ocupados donde el email esté en `postulaciones`.
- Si no hay postulaciones, `data: []`.
- Si no hay orientación, `orientacion: null`.
- Orden: más recientes primero (por `contrato.id` descendente como aproximación).

### 7.4 `POST /api/postulaciones/{contrato_id}/orientacion`

Flujo:

1. Verificar que el contrato existe.
2. Verificar que `user.email` está en `contrato.postulaciones`.
3. Calcular el resultado con `comparar()`.
4. Si `sin_requisitos` → devolver 400 con un mensaje claro:
   “La oferta no tiene requisitos cargados; no se puede generar una orientación”.
5. Armar el payload para n8n:
   ```json
   {
     "contrato_id": 1,
     "email": "dev@udelaconecta.edu.ar",
     "oferta": "Frontend Angular para el panel de pagos",
     "compatibles": ["Angular"],
     "a_capacitar": ["TypeScript", "CSS"],
     "se_aprenden": ["Docker"],
     "blandas": ["Trabajo en equipo"],
     "coincidencia": 25
   }
   ```
6. Llamar a `N8N_ORIENTACION_WEBHOOK_URL` con `X-Udela-Secret`.
7. Validar la respuesta:
   - texto no vacío,
   - máximo 600 caracteres,
   - sin frases de rechazo (`no calificás`, `rechazado`, `no sos apto`, `no cumple`).
8. Guardar en `informe_postulacion` con `estado="generado"` o `"fallback"`.
9. Devolver el texto y el estado.

Si no hay webhook configurado, si n8n falla o si la respuesta es inválida, guardar el
**fallback determinista**:

> “Te faltan {lista}. Podés reforzarlos con cursos introductorios y proyectos pequeños.
> Esto es una orientación para prepararte, no una evaluación.”

El endpoint nunca debe devolver 500 por un fallo de IA.

### 7.5 Configuración

Archivo: `apps/backend/app/core/config.py`

Agregar:

```python
N8N_ORIENTACION_WEBHOOK_URL: str = ""
N8N_AUTOMATION_SECRET: str = ""
N8N_ORIENTACION_TIMEOUT_SEGUNDOS: float = 30
```

- Local: agregar a `infra/local/.env.chat` (fuera de git) o a `.env.local` si se usa
  un secreto de desarrollo.
- Producción: agregar a `infra/vps/.env.vps.example` y a `setup-env.sh`.
- El secreto debe ser el mismo que la credencial Header Auth de n8n.
- Usar `hmac.compare_digest` para comparar el secreto.

### 7.6 Permisos

- Un estudiante no puede pedir la orientación de otro email.
- Un gerente no puede pedir la orientación de un estudiante.
- La empresa solo ve `resultados_postulantes` de sus propios contratos.
- El endpoint de automatización exige `X-Udela-Secret`.
- Nunca devolver `telefono` ni `fecha_nacimiento` en el informe.

### 7.7 Tests de API

Archivo: `apps/backend/tests/test_postulaciones_informe.py`

- [ ] Estudiante se postula y `GET /api/mis-postulaciones` devuelve su resultado.
- [ ] El resultado coincide con el cálculo esperado.
- [ ] `POST .../orientacion` sin n8n configurado devuelve `estado="fallback"` y guarda.
- [ ] `POST .../orientacion` con n8n mockeado devuelve `estado="generado"`.
- [ ] Un estudiante no puede ver la orientación de otro.
- [ ] La empresa ve `resultados_postulantes` solo en sus contratos.
- [ ] Oferta sin requisitos → `sin_requisitos` y la orientación responde 400.
- [ ] Contrato sin postulaciones → `data: []`.
- [ ] El informe no incluye teléfono ni fecha de nacimiento.

Usar `httpx.MockTransport` como en `tests/test_chat.py` para simular n8n.

**Criterio de aceptación:** `poetry run pytest` pasa completo.

---

## 8. Fase 4 — Frontend

### 8.1 Modelos

Archivo: `apps/frontend/src/app/models/contrato.ts`

Agregar:

```ts
export class Requisito {
  nombre: string = '';
  nivel_minimo?: 'principiante' | 'intermedio' | 'avanzado';
  exigencia?: 'excluyente' | 'deseable' | 'se_aprende';
  tipo?: 'tecnica' | 'blanda';
}

export class ResultadoCompatibilidad {
  coincidencia: number = 0;
  nivel: string = '';
  total_requisitos: number = 0;
  total_compatibles: number = 0;
  sin_requisitos: boolean = false;
  compatibles: any[] = [];
  a_capacitar: any[] = [];
  se_aprenden: string[] = [];
  blandas: string[] = [];
  checklist: any[] = [];
}

export class Orientacion {
  texto: string = '';
  estado: 'pendiente' | 'generado' | 'fallback' = 'pendiente';
  modelo?: string;
  actualizado_en?: string;
}
```

Agregar a `Contrato`:

```ts
requisitos?: Requisito[];
mi_resultado?: ResultadoCompatibilidad;
resultados_postulantes?: any[];
```

### 8.2 Servicio

Archivo: `apps/frontend/src/app/servicios/contrato.ts`

Agregar:

```ts
getMisPostulaciones(): Observable<any> {
  return this._httpClient.get<any>(`${this._contratosUrl}mis-postulaciones`);
}

pedirOrientacion(contratoId: number): Observable<any> {
  return this._httpClient.post<any>(
    `${this._contratosUrl}postulaciones/${contratoId}/orientacion`,
    {}
  );
}
```

### 8.3 Formulario de oferta

Archivos:

- `apps/frontend/src/app/views/formcreatecontract/formcreatecontract.ts`
- `apps/frontend/src/app/views/formcreatecontract/formcreatecontract.html`
- `apps/frontend/src/app/views/formcreatecontract/formcreatecontract.css`

Cambios:

- Agregar `requisitos: []` al objeto `contrato`.
- Agregar `nuevoRequisito: Requisito = { nombre: '', nivel_minimo: 'principiante', exigencia: 'deseable', tipo: 'tecnica' }`.
- Métodos:
  - `agregarRequisito()`: valida nombre no vacío y no duplicado; agrega.
  - `quitarRequisito(i)`: elimina.
- Template:
  - Sección “Requisitos del puesto”.
  - Input de nombre, select de nivel, select de exigencia, select de tipo, botón “Agregar”.
  - Chips con los requisitos agregados y botón para quitar.
  - Texto de ayuda: “Los requisitos excluyentes son los que la empresa necesita desde el
    inicio. Los deseables suman. Los que se aprenden en el puesto no se cuentan como
    brecha. Las habilidades blandas se evalúan en entrevista.”
- Validación:
  - Al menos un requisito para publicar (recomendado).
  - Si no hay requisitos, mostrar advertencia: “Sin requisitos, los estudiantes no verán
    informe de compatibilidad”.
- Al enviar, incluir `requisitos` en el body.

### 8.4 Detalle de la oferta (estudiante)

Archivos:

- `apps/frontend/src/app/componentes/contrato-detail/contrato-detail.ts`
- `apps/frontend/src/app/componentes/contrato-detail/contrato-detail.html`
- `apps/frontend/src/app/componentes/contrato-detail/contrato-detail.css`

Cambios:

- Agregar inputs:
  ```ts
  @Input() miResultado?: ResultadoCompatibilidad;
  @Input() orientacion?: Orientacion;
  ```
- Bloque “Requisitos del puesto”:
  - Si `miResultado?.sin_requisitos`: “La oferta no especificó requisitos”.
  - Si hay checklist: lista con estado `cumple` / `falta` / `parcial` / `se_aprende` /
    `blanda`.
  - Mostrar el resumen: “Cumplís X de Y requisitos (Z%)”.
  - Nota fija: “Este análisis se basa en tu perfil declarado. No es una evaluación ni un
    requisito para postularte. **Podés postularte igual.**”
- El botón “Postularme” no se deshabilita por el resultado.
- Si ya se postuló, mostrar el bloque “Tu informe de postulación” con las tres secciones
  y la orientación:
  - Título: “Tu informe de postulación”.
  - “Nivel de coincidencia”.
  - “Aptitudes compatibles”.
  - “Aptitudes a capacitar”.
  - Notas: “Se aprende en el puesto” y “A evaluar en entrevista”.
  - Orientación:
    - Si no hay: botón “Generar orientación”.
    - Si hay: texto + etiqueta “Orientación generada por IA” o “Orientación (sin IA
      disponible)” + botón “Regenerar”.
    - Nota: “Es una sugerencia para prepararte, no una evaluación de tu perfil.”
- Manejar estados de carga y error con `AlertService`.

### 8.5 Historial “Mis postulaciones”

Archivos:

- `apps/frontend/src/app/componentes/contratos/contratos.ts`
- `apps/frontend/src/app/componentes/contratos/contratos.html`

Cambios:

- En `ngOnInit`, si `rolActual === 'estudiante'`, llamar a `getMisPostulaciones()` y
  guardar un mapa por `contrato.id`:
  ```ts
  this.informesPorContrato = new Map<number, { resultado, orientacion }>();
  ```
- Al seleccionar un contrato pendiente, pasar `miResultado` y `orientacion` a
  `app-contrato-detail`.
- En la tarjeta del drawer, agregar un indicador compacto:
  - `{{ resultado.coincidencia }}%` o `{{ resultado.total_compatibles }}/{{ resultado.total_requisitos }}`.
  - Texto “Ver informe”.
- No cambiar el orden de las tarjetas ni ocultar ninguna.
- Si no hay informe (por ejemplo, oferta sin requisitos), mostrar “Sin requisitos
  cargados”.

### 8.6 Postulantes (empresa)

Archivos:

- `apps/frontend/src/app/componentes/contrato-detail/contrato-detail.ts`
- `apps/frontend/src/app/componentes/contrato-detail/contrato-detail.html`

Cambios:

- Agregar input `resultadosPostulantes`.
- En “Postulaciones Recibidas”, mostrar por cada postulante:
  - email,
  - `coincidencia` (ej. “2 de 4”),
  - un botón “Ver informe”.
- El modal existente (`abrirModal(postulante)`) puede incluir el informe determinista:
  - nivel de coincidencia,
  - compatibles,
  - a capacitar,
  - se aprenden,
  - blandas.
- No mostrar el texto de IA al gerente.
- No agregar etiquetas de “mejor” ni “peor”.
- No deshabilitar la asignación por el resultado.

### 8.7 Textos y estilos

Textos obligatorios:

- “Este análisis se basa en tu perfil declarado.”
- “Podés postularte igual.”
- “No es una evaluación ni un ranking.”
- “La orientación es una sugerencia para prepararte, no una evaluación.”
- “Esto no implica rechazo.”
- “La empresa ve este mismo resumen; la orientación es solo para vos.”

Estilos:

- Compatible: verde suave.
- A capacitar: ámbar suave.
- Se aprende: gris/azul informativo.
- Blanda: azul informativo.
- Evitar rojo de “error” o “rechazo” para las brechas.
- No usar íconos de “aprobado/rechazado”.

**Criterios de aceptación:**

- [ ] `npm run build` pasa.
- [ ] El formulario de oferta permite cargar, quitar y enviar requisitos.
- [ ] El estudiante ve el checklist antes de postularse.
- [ ] El botón “Postularme” siempre está habilitado si la oferta está libre.
- [ ] El historial muestra las tres secciones por postulación.
- [ ] La orientación se puede generar y regenerar.
- [ ] La empresa ve el indicador por postulante.
- [ ] No hay ningún texto que diga “no calificás” o “rechazado”.

---

## 9. Fase 5 — IA: workflow de orientación

### 9.1 Archivo

`infra/n8n/udela-orientacion.json` (nuevo workflow exportado, sin credenciales).

### 9.2 Nodos

| Nodo | Tipo | Función |
|---|---|---|
| Webhook Orientación | Webhook `POST /webhook/udela-orientacion` | Recibe el payload; Header Auth `X-Udela-Secret` |
| Normalizar | Set | Recorta textos, arma listas y valida campos |
| ¿Hay brechas? | IF | `a_capacitar.length > 0` |
| Prompt Orientación | Set/Code | Arma el prompt con las reglas |
| Modelo | DeepSeek Chat Model o HTTP Request | Genera el texto (reutilizar credencial `DeepSeek account`) |
| Validar | Code | Texto no vacío, ≤ 600 caracteres, sin frases de rechazo |
| Responder | Respond to Webhook | `{ "texto": "...", "modelo": "..." }` |
| Sin brechas | Set | Mensaje corto de “cumplís todos los requisitos declarados” |
| Fallback | Set | Texto determinista si la validación falla |

La decisión obligatoria es **¿Hay brechas?**. El workflow tiene dos caminos y ambos
responden.

### 9.3 Prompt

```text
Sos un orientador laboral de Udela Conecta. Recibís el resultado de una comparación
entre el perfil declarado de un estudiante y los requisitos de una oferta.

Datos:
- Oferta: {{ $json.oferta }}
- Coincidencia: {{ $json.coincidencia }}%
- Aptitudes compatibles: {{ $json.compatibles.join(", ") }}
- Aptitudes a capacitar: {{ $json.a_capacitar.join(", ") }}
- Se aprenden en el puesto: {{ $json.se_aprenden.join(", ") }}
- Habilidades blandas a evaluar en entrevista: {{ $json.blandas.join(", ") }}

Escribí un texto de 3 a 4 líneas, en español rioplatense, para el postulante.

Reglas obligatorias:
- No digas que no califica, que será rechazado o que no es apto.
- No inventes requisitos que no estén en la lista.
- No evalúes habilidades blandas.
- No prometas resultados.
- Empezá por la brecha más importante y sugerí un paso concreto.
- Aclará que es una orientación para prepararse, no una evaluación.
- Máximo 600 caracteres.
- Texto plano, sin markdown.
```

### 9.4 Validación y fallback

En el nodo `Validar`:

- Rechazar si el texto está vacío.
- Rechazar si supera 600 caracteres.
- Rechazar si contiene (en minúsculas): `no calificás`, `rechazado`, `no sos apto`,
  `no cumple`, `no sirve`.
- Si falla, usar el fallback:

> “Te faltan {a_capacitar}. Podés reforzarlos con cursos introductorios y proyectos
> pequeños. Esto es una orientación para prepararte, no una evaluación.”

El backend también valida la respuesta. Si n8n devuelve algo inválido, guarda `fallback`.

### 9.5 Configuración

- n8n: credencial Header Auth `Udela-Secret` (header `X-Udela-Secret`) y credencial
  `DeepSeek account`.
- Backend: `N8N_ORIENTACION_WEBHOOK_URL`, `N8N_AUTOMATION_SECRET`,
  `N8N_ORIENTACION_TIMEOUT_SEGUNDOS`.
- Si no se configura, el endpoint devuelve fallback. No rompe la postulación.

### 9.6 Criterios de aceptación

- [ ] El workflow se importa en n8n.
- [ ] Con brechas, genera un texto y lo devuelve.
- [ ] Sin brechas, devuelve el mensaje corto.
- [ ] Si el modelo falla, responde con fallback.
- [ ] El texto no contiene frases de rechazo.
- [ ] El backend guarda el resultado en `informe_postulacion`.
- [ ] Regenerar actualiza el registro existente, no duplica.

---

## 10. Fase 6 — Workflow de comunicación y Docker

### 10.1 Workflow 3: digest de oportunidades

Archivo: `infra/n8n/udela-digest.json`

Objetivo: comunicar resultados y fomentar postulaciones, sin rankear personas.

| Nodo | Tipo | Función |
|---|---|---|
| Schedule | Schedule Trigger semanal | Lunes 9:00 |
| Obtener digests | HTTP Request `GET /api/automatizacion/digests` | Header `X-Udela-Secret` |
| ¿Hay novedades? | IF | `items.length > 0` |
| Enviar | Email o Telegram | Un mensaje por estudiante con 2-3 ofertas y su coincidencia |
| Sin novedades | NoOp | No molestar |

Endpoint `GET /api/automatizacion/digests`:

- Para cada estudiante, buscar ofertas libres donde no se postuló.
- Calcular `comparar(perfil, oferta.requisitos)`.
- Quedarse con las 2-3 de mayor coincidencia y que superen 60 %.
- Si no hay, omitir al estudiante.
- Devolver:
  ```json
  {
    "data": [
      {
        "email": "dev@udelaconecta.edu.ar",
        "nombre": "Valentina",
        "ofertas": [
          {
            "contrato_id": 4,
            "titulo": "Data Analyst Trainee",
            "coincidencia": 80,
            "faltantes": ["Power BI"]
          }
        ]
      }
    ]
  }
  ```

Reglas:

- No incluir ofertas a las que ya se postuló.
- No incluir datos sensibles.
- No enviar más de un digest por estudiante por ejecución.
- Si no hay SMTP/Telegram configurado, documentar la credencial y dejar el nodo de envío
  deshabilitado; el workflow debe poder ejecutarse y mostrar el resultado en n8n.

### 10.2 Docker

Archivo: `infra/local/docker-compose.yml`

Agregar:

```yaml
  n8n:
    image: n8nio/n8n:1.70.0
    container_name: udela-local-n8n
    ports:
      - "5678:5678"
    environment:
      N8N_HOST: localhost
      N8N_PORT: 5678
      N8N_PROTOCOL: http
      WEBHOOK_URL: http://localhost:5678/
      GENERIC_TIMEZONE: America/Argentina/Buenos_Aires
      N8N_ENCRYPTION_KEY: ${N8N_ENCRYPTION_KEY:-udela-local-n8n-key}
      N8N_SECURE_COOKIE: "false"
      N8N_DIAGNOSTICS_ENABLED: "false"
    volumes:
      - n8n_data:/home/node/.n8n
      - ../n8n:/workflows:ro
    depends_on:
      - backend
```

Agregar el volumen `n8n_data`.

En el servicio `backend`, agregar:

```yaml
      N8N_CHAT_WEBHOOK_URL: http://n8n:5678/webhook/udela-chat
      N8N_ORIENTACION_WEBHOOK_URL: http://n8n:5678/webhook/udela-orientacion
      N8N_AUTOMATION_SECRET: ${N8N_AUTOMATION_SECRET:-udela-local-secret}
      CHAT_DATOS_URL: http://backend:3000/api/chat/datos
```

Cuidado: no hardcodear secretos reales en el compose. Usar variables de `.env.local` o
`.env.chat`.

### 10.3 Importación de workflows

Documentar en `context_agent/n8n.md` y en el README:

```bash
# Con n8n ya levantado
docker compose -f infra/local/docker-compose.yml exec n8n \
  n8n import:workflow --input=/workflows/udela-chatbot.json

docker compose -f infra/local/docker-compose.yml exec n8n \
  n8n import:workflow --input=/workflows/udela-orientacion.json

docker compose -f infra/local/docker-compose.yml exec n8n \
  n8n import:workflow --input=/workflows/udela-digest.json
```

Después, en la UI de n8n:

1. Asignar la credencial `Udela-Secret` a los webhooks.
2. Asignar `DeepSeek account` a los nodos de IA.
3. Activar los workflows.
4. Probar el webhook con `curl`.

**Criterios de aceptación:**

- [ ] `docker compose ... up -d` levanta n8n en `http://localhost:5678`.
- [ ] Los 3 workflows se importan.
- [ ] El backend llega a n8n por `http://n8n:5678`.
- [ ] El chat sigue funcionando.
- [ ] El workflow de orientación responde desde el backend.
- [ ] El workflow de digest se ejecuta y devuelve datos.

---

## 11. Fase 7 — Documentación de entrega

Crear o actualizar:

| Archivo | Contenido |
|---|---|
| `README.md` | Sección “Compatibilidad y orientación”: flujo, endpoints, textos, comandos |
| `docs/ARQUITECTURA.md` | Diagrama Mermaid de componentes y recorrido de datos |
| `docs/BITACORA_IA.md` | Herramientas usadas, decisiones, dificultades y correcciones |
| `docs/RESPONSABILIDADES.md` | Rol de cada integrante (completar nombres reales) |
| `docs/DEMO.md` | Guion de demostración y casos de error |
| `docs/COBERTURA_CONSIGNA.md` | Matriz requisito → evidencia |
| `apps/backend/requirements.txt` | Dependencias directas fijadas |
| `context_agent/AGENTS.md` | Estado actual, nuevos módulos y endpoints |
| `context_agent/backend.md` | Modelo, endpoints y reglas nuevas |
| `context_agent/endpoint.md` | Inventario actualizado |
| `context_agent/n8n.md` | Workflows 2 y 3, credenciales y problemas frecuentes |

### 11.1 `requirements.txt`

Generar desde Poetry o escribir las dependencias directas con versiones compatibles:

```bash
cd apps/backend
poetry export -f requirements.txt --without-hashes --output requirements.txt
```

Si no se usa `poetry export`, copiar las versiones de `pyproject.toml` y `poetry.lock`.

### 11.2 Bitácora de IA

Incluir:

- Herramientas usadas (por ejemplo, Codex/Claude/ChatGPT/DeepSeek).
- Para qué se usó cada una.
- Decisiones técnicas tomadas con ayuda de IA.
- Dificultades y correcciones.
- Qué se verificó manualmente.
- Qué no se delegó a la IA (el cálculo, las decisiones de producto, la validación).

No inventar participación. Ajustar a lo que realmente hizo el equipo.

### 11.3 Responsabilidades

Usar los contribuyentes reales del repo y asignar:

- Backend / datos.
- Frontend.
- n8n / automatización.
- IA / documentación.
- Testing / demo.

**Criterio de aceptación:** el repositorio permite reproducir el flujo siguiendo el README.

---

## 12. Fase 8 — Verificación y demo

### 12.1 Casos de prueba manuales

| # | Caso | Resultado esperado |
|---|---|---|
| 1 | Estudiante con algunas skills se postula a una oferta con requisitos | Se registra la postulación y el historial muestra las tres secciones |
| 2 | Estudiante con todas las skills | 100 %, sin “a capacitar”; orientación breve y positiva |
| 3 | Estudiante sin skills | 0 %, todo “a capacitar”; la postulación se registra igual |
| 4 | Oferta sin requisitos | “Sin requisitos cargados”; no se genera orientación; no rompe |
| 5 | Requisito “se aprende en el puesto” | No cuenta como brecha; aparece como oportunidad |
| 6 | Requisito blando | No se puntúa; aparece “a evaluar en entrevista” |
| 7 | n8n apagado | La postulación funciona; la orientación usa fallback |
| 8 | IA devuelve texto inválido | Se guarda fallback; no se muestra texto ofensivo |
| 9 | Estudiante actualiza su perfil | El indicador sube al recargar; la orientación se puede regenerar |
| 10 | Empresa ve postulantes | Ve indicador y listas; no ve la orientación de IA |
| 11 | Otro estudiante intenta ver el informe | 403 |
| 12 | Gerente intenta ver el informe de un estudiante | 403 |
| 13 | Oferta con muchos postulantes | La vista no se rompe; el cálculo es correcto |
| 14 | Seed ejecutado dos veces | No duplica datos |

### 12.2 Comandos

```bash
# Backend
cd apps/backend
poetry install
poetry run alembic upgrade head
poetry run pytest

# Frontend
npm install
npm run build
npm run test:front

# Stack completo
npm run local:up
# Abrir http://localhost:4200

# n8n
docker compose -f infra/local/docker-compose.yml exec n8n n8n import:workflow \
  --input=/workflows/udela-orientacion.json
```

> Nota: el entorno de esta sesión no tiene Docker, dependencias Python ni `node_modules`.
> Para verificar de punta a punta hay que instalar Docker Desktop/Engine, ejecutar
> `npm install` y `poetry install`.

### 12.3 Guion de demo (10-12 minutos)

1. Empresa crea una oferta con requisitos (mostrar excluyente/deseable/se aprende).
2. Estudiante ve la oferta, el checklist y el texto “Podés postularte igual”.
3. Estudiante se postula.
4. Abrir “Mis postulaciones” y mostrar:
   - nivel de coincidencia,
   - compatibles,
   - a capacitar,
   - orientación de IA.
5. Empresa abre “Postulaciones Recibidas” y muestra el informe por postulante.
6. Mostrar el workflow de orientación en n8n y su ejecución.
7. Mostrar el workflow de digest y explicar la decisión.
8. Mostrar el chatbot respondiendo sobre la misma postulación.
9. Caso de error: apagar n8n y mostrar el fallback.
10. Caso de error: oferta sin requisitos y perfil sin skills.

---

## 13. Matriz de cobertura de la consigna

| Requisito | Evidencia en el proyecto |
|---|---|
| 4.1 Python: módulos, funciones, validación, excepciones | `app/dominio/compatibilidad.py`, tests unitarios, manejo de requisitos inválidos |
| 4.2 FastAPI: ≥ 5 endpoints funcionales | `mis-postulaciones`, orientación GET/POST, automatización, endpoints existentes |
| 4.3 Angular: formularios y resultados | Formulario de oferta con requisitos, checklist, informe en historial, vista de postulantes |
| 4.4 n8n: ≥ 3 workflows con decisión | Chatbot, orientación (IF brechas), digest (IF novedades) |
| 4.5 IA integrada, justificación y supervisión | Orientación por postulación, prompt acotado, validación, fallback, revisión del estudiante |
| 4.6 Persistencia | PostgreSQL, `contrato.requisitos`, `informe_postulacion` |
| 4.7 Docker | `infra/local/docker-compose.yml` con backend, frontend, Postgres, Adminer y n8n |
| 5 Bitácora de IA | `docs/BITACORA_IA.md` |
| 6 Repositorio | README, workflows JSON, seed, requirements.txt, .gitignore, arquitectura |
| 7 Verificación | `docs/DEMO.md` y casos de la sección 12 |
| 9 Entrega | Repo actualizado, README, diagrama, workflows, bitácora, responsabilidades |
| 11 Evaluación | Proceso completo, Docker, Python/FastAPI/Angular, n8n, IA, errores, repo |

---

## 14. Riesgos y decisiones abiertas

| Riesgo / decisión | Impacto | Mitigación |
|---|---|---|
| Ofertas viejas sin requisitos | No muestran informe | Devolver `sin_requisitos` y avisar en la UI |
| N+1 al calcular postulantes | Lentitud con muchas postulaciones | Una consulta `email.in_(...)`; cachear por request |
| n8n no configurado | Sin orientación IA | Fallback determinista; la postulación sigue |
| IA devuelve texto inapropiado | Riesgo reputacional | Validación de longitud y frases; fallback |
| Credenciales de n8n | Los workflows no corren | Documentar importación y credenciales; no versionar secretos |
| Build de Angular | Regresiones | `npm run build` en cada fase |
| Docker no disponible en el entorno actual | No se puede verificar el compose | Instalar Docker antes de la prueba final |
| Blandas mal modeladas | Se vuelve a puntuar personas | Excluirlas del cálculo; solo listarlas |
| “Se aprende en el puesto” mal usado | Se convierte en brecha | No contarlo en el total; mostrarlo como oportunidad |
| La empresa usa el informe como filtro | Sesgo | No enviar la orientación de IA; mostrar el detalle y aclarar que no es un veredicto |
| El indicador se lee como ranking | Desalienta postulaciones | Textos claros; no ordenar por defecto; no mostrar posición |

### Decisiones que debe confirmar el equipo

- [ ] ¿La empresa ve el mismo informe determinista que el estudiante? (recomendado: sí,
      sin la orientación de IA).
- [ ] ¿El formulario de oferta exige al menos un requisito para publicar? (recomendado:
      sí, con advertencia si no hay).
- [ ] ¿El digest semanal es para estudiantes, para empresas o para ambos? (recomendado:
      estudiantes, para fomentar postulaciones).
- [ ] ¿Se usa DeepSeek (ya configurado) o se agrega Ollama local? (recomendado: DeepSeek
      para la entrega; Ollama como alternativa documentada).
- [ ] ¿Se agrega una notificación in-app además del email del digest? (opcional).

---

## 15. Checklist final

### Backend

- [ ] `Contrato.requisitos` en el modelo.
- [ ] `InformePostulacion` en el modelo y exportado.
- [ ] Migración `0004` con `upgrade` y `downgrade`.
- [ ] Seed con requisitos en las 11 ofertas.
- [ ] `dominio/compatibilidad.py` sin dependencias externas.
- [ ] Tests unitarios del comparador.
- [ ] `GET /api/mis-postulaciones`.
- [ ] `GET/POST /api/postulaciones/{id}/orientacion`.
- [ ] Enriquecimiento de `contratoslibres` y `contratos/{email_gerente}`.
- [ ] Configuración de n8n y secreto.
- [ ] Tests de API y permisos.

### Frontend

- [ ] Modelos `Requisito`, `ResultadoCompatibilidad`, `Orientacion`.
- [ ] Servicio `getMisPostulaciones` y `pedirOrientacion`.
- [ ] Formulario de oferta con requisitos.
- [ ] Checklist en el detalle de la oferta.
- [ ] Informe de tres secciones en el historial.
- [ ] Orientación con estados de carga, error y regeneración.
- [ ] Vista de postulantes con indicador.
- [ ] Textos y estilos no elitistas.
- [ ] `npm run build` pasa.

### n8n

- [ ] `udela-orientacion.json` exportado.
- [ ] `udela-digest.json` exportado.
- [ ] Cada workflow tiene una decisión.
- [ ] Los 3 workflows se importan.
- [ ] Credenciales documentadas.
- [ ] n8n en Docker Compose.
- [ ] Backend llega a n8n por red interna.

### Documentación

- [ ] README actualizado.
- [ ] `docs/ARQUITECTURA.md`.
- [ ] `docs/BITACORA_IA.md`.
- [ ] `docs/RESPONSABILIDADES.md`.
- [ ] `docs/DEMO.md`.
- [ ] `docs/COBERTURA_CONSIGNA.md`.
- [ ] `apps/backend/requirements.txt`.
- [ ] `context_agent/*` actualizado.

### Verificación

- [ ] `alembic upgrade head` y `alembic check`.
- [ ] `pytest` completo.
- [ ] `npm run build`.
- [ ] Casos manuales 1-14.
- [ ] Demo ensayada.

---

## 16. Definición de terminado

La entrega se considera completa cuando:

1. Una empresa puede publicar una oferta con requisitos excluyentes, deseables y “se
   aprende en el puesto”.
2. Un estudiante puede ver esos requisitos, postularse aunque no cumpla todo, y recibir
   en su historial un informe con las tres secciones.
3. El indicador se calcula en Python, es reproducible y está testeado.
4. La orientación de IA aparece por postulación, está etiquetada, tiene fallback y no
   implica rechazo.
5. La empresa ve el informe determinista por postulante y decide humanamente.
6. Existen 3 workflows de n8n con decisión, integrados y documentados.
7. El stack levanta con Docker, incluido n8n.
8. El README, la arquitectura, la bitácora, las responsabilidades y los workflows están
   en el repositorio.
9. La demo se puede ejecutar de punta a punta y también mostrar los errores.
10. Ningún texto del sistema sugiere que la persona “no califica” o que el sistema
    “rechaza”.
