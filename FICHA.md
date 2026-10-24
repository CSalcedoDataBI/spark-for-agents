# Ficha — spark-for-agents

> Ficha de esta herramienta. La lee su experto (`.claude/agents/experto.md`) en cada PR.
> Su guía es `FICHA.md` y el agente `experto` fusiona contra ella.
> Cambiarla exige una nueva aprobación de Cristóbal.

## Qué es

- **Qué construye y para quién:** la referencia de Apache Spark (PySpark y Spark SQL) para agentes
  de IA. Cada función sale del propio motor, con su firma, la versión en que apareció, su
  disponibilidad en el runtime de Fabric y las trampas que no cuenta la documentación. Es para
  quien escribe notebooks de Spark con un agente.
- **Papel** (`repo-roles`): tool (plugin de skills)
- **Gemelo público/privado:** ninguno por ahora. Hermanos de familia: `dax-for-agents` y
  `powerquery-m-for-agents`.

## Norte

- **Plan vigente:** [épica v0.1 — catálogo desde el motor](https://github.com/CSalcedoDataBI/spark-for-agents/issues/2)
- **Lo que esta herramienta NO es:**
  - No ejecuta jobs ni gestiona items de Fabric: eso es `fabric-cli` y las skills de Fabric.
  - No diseña ETL ni capas medallion: eso es `etl-blueprints-for-agents`.
  - No es un tutorial de Spark: es una referencia que un agente consulta.

## Zonas protegidas

Lo que no se toca sin un paso del plan que lo nombre:

- Las fichas generadas: solo las escribe el script de exportación. Una ficha a mano rompe la
  promesa de «ningún nombre inventado».
- `LICENSE` (MIT) y la visibilidad pública del repo.

## Capa y feedback

- **Capa de nodo** (ADR 0023): `etl`
- **Skill de feedback:** `spark-for-agents:spark-feedback` (planeada en la v0.1)

## Check y experto

- **Check de CI requerido:** `Validate` (ruleset `main protegida` de `main`)
- **Suite de pruebas:** `python scripts/check_repo.py`
- **Runner:** GitHub (repo público)
- **Formato de tag:** `vX.Y.Z`, con release-please (`release-please-config.json`).
- **Experto:** `.claude/agents/experto.md`
- **¿Plugin del directorio?:** todavía no. Se envía cuando salga de pre-release; desde entonces,
  `stable` no se toca y publicar sigue R5.
- **Partes visibles que aprueba Cristóbal:** el README de cara al público y la salida de
  pre-release.

## Aprobación

Aprobada: 2026-10-24 (mantenedor)