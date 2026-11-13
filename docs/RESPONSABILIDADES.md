# Responsabilidades del equipo

> Según el historial del repositorio, en esta entrega el único contribuyente registrado es
> **Roberto Singuri**. La tabla distribuye las áreas de trabajo para que la entrega sea
> evaluable; si el equipo incorpora más personas, reemplazar los nombres y mantener las
> áreas.

| Área | Responsable | Alcance en esta entrega |
|---|---|---|
| **Backend / datos** | Roberto Singuri | `Contrato.requisitos`, `InformePostulacion`, migración `0004`, seed con requisitos, endpoints de informe/orientación/digest |
| **Dominio / cálculo** | Roberto Singuri | `app/dominio/compatibilidad.py` en Python puro y sus 12 tests unitarios |
| **Frontend** | Roberto Singuri | Formulario de requisitos, checklist, informe de tres secciones, orientación, indicador compacto, vista de postulantes |
| **n8n / automatización** | Roberto Singuri | Workflows `udela-orientacion.json` y `udela-digest.json`, servicio n8n en Compose, variables y credenciales documentadas |
| **IA / prompts / documentación** | Roberto Singuri | Prompt acotado, validación y fallback, `README.md`, `docs/*`, `context_agent/*` |
| **Testing / demo** | Roberto Singuri | pytest (dominio + API), build de Angular, verificación de migración/seed, importación de workflows, guion de demo |

## Criterios de revisión antes de entregar

- [ ] El README permite reproducir el flujo local con Docker.
- [ ] `pytest` pasa completo y `npm run build` compila.
- [ ] `alembic upgrade head` y `alembic check` no muestran diferencias.
- [ ] El seed es idempotente.
- [ ] Los tres workflows se importan en n8n.
- [ ] La demo recorre los 14 casos de `docs/DEMO.md` o al menos los 10 del guion.
- [ ] No hay secretos reales versionados.
- [ ] Los textos obligatorios están presentes en la UI.

## Nota sobre el uso de IA

La implementación se apoyó en un asistente de IA para escribir código y documentación. Las
decisiones de producto, las reglas de negocio, la validación y la aprobación final son
responsabilidad de las personas del equipo. El detalle está en
[`BITACORA_IA.md`](./BITACORA_IA.md).
