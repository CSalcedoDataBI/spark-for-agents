# spark-for-agents — diseño inicial

*2026-10-23. Estado: borrador para la épica v0.1.*

## 1. Qué problema resuelve

Un agente que escribe PySpark o Spark SQL inventa funciones, mezcla versiones y no sabe qué trae
el runtime de Fabric. `dax-for-agents` y `powerquery-m-for-agents` resolvieron lo mismo para DAX y
M: el catálogo sale del motor, no de la memoria. Aquí se repite la receta con Spark.

## 2. Fuente de verdad

| Qué | Cómo se exporta |
|---|---|
| Funciones de Spark SQL | `SHOW FUNCTIONS` y `DESCRIBE FUNCTION EXTENDED <f>` (uso, argumentos, ejemplos, `since`) |
| API de PySpark | introspección de `pyspark.sql.functions`, `DataFrame` y `Column` (firma y docstring) |
| Disponibilidad en Fabric | la misma exportación, corrida en cada runtime de Fabric Spark |

La exportación base corre en CI con un Spark fijado por versión, en runners de GitHub (repo
público, minutos gratis). La de Fabric corre a mano en un notebook, y su JSON se commitea.

## 3. Antes de escribir nada (NORTE R2)

Revisar lo que ya existe, para no duplicarlo: `etl:executing-spark`, `fabric-skills:spark-cli`,
la referencia oficial de Spark y los repos públicos de skills de Spark. El hallazgo se anota en la
épica.

### 3.1 Hallazgo (2026-10-23)

| Qué existe | Qué hace | ¿Da un catálogo de funciones exportado del motor? |
|---|---|---|
| `etl:executing-spark` (plugin `etl`) | Ejecuta código PySpark o Python en Fabric por la API de Livy, sin crear un notebook: ciclo de sesión, autenticación con `az`, qué funciona y qué no en esa sesión | No. Es **dónde correr** el código, no qué funciones existen |
| `fabric-skills:spark-cli` | Despachador de modos para Spark en Fabric: escribir celdas de notebook, sesiones Livy, diagnóstico de corridas fallidas y ciclo de vida de las Materialized Lake Views | No. Cubre la **operación** en Fabric y la sintaxis propia de Fabric (MLV), no el catálogo de Spark |
| `databricks/databricks-agent-skills` (367★, empuje 2026-10-23, licencia propia) | Skills de la plataforma Databricks: jobs, pipelines, Unity Catalog, streaming, consulta de documentación | No. Es la plataforma Databricks; la referencia sale de la documentación, no del motor |
| `databricks-solutions/ai-dev-kit` (1965★, empuje 2026-10-23, licencia propia) | Kit de Field Engineering: SDK de Databricks y evaluaciones de skills | No |
| `PatrickGallucci/fabric-skills` (17★, empuje 2026-06-07, MIT) | Skills de Fabric, entre ellas cinco de rendimiento y remediación de PySpark, Delta y el cómputo de Spark | No. El rendimiento queda fuera de este repo: las fichas lo enlazan, no lo duplican |
| `SemyonSinchenko/pyspark-mcp-server` (18★, empuje 2026-02-26, Apache-2.0) | Servidor MCP sobre una sesión de Spark viva: versión, plan de una consulta, esquemas, catálogos y tablas | No. Inspecciona **datos y planes** de una sesión, no las funciones disponibles. Útil como idea: la misma sesión que responde a esto puede correr la exportación |
| `vgiri2015/ai-spark-mcp-server` (29★, último empuje 2025-12-05) | Servidor MCP que genera y optimiza código Spark con un LLM | No. Genera código desde la memoria del modelo, que es justo el problema |
| `lakehq/sail` (3469★, Apache-2.0) | Motor compatible con Spark escrito en Rust | No es una referencia; sirve para recordar que «compatible con Spark» no implica el mismo catálogo |
| Otros resultados de `gh search repos` («pyspark agent», «spark mcp server», «spark agent skills») | Agentes que traducen inglés o SQL a PySpark, y skills de NVIDIA DGX Spark (otro producto con el mismo nombre) | No |

Búsquedas hechas: `spark claude skill`, `pyspark skill agent`, `pyspark mcp`,
`spark sql functions json catalog`, `pyspark llm hallucination`, `spark agent skills`,
`databricks skills claude`, `spark mcp server`, `pyspark agent`, `databricks agent skills`,
`spark functions reference`, con `--sort=stars`.

**Conclusión.** Nadie publica un catálogo de funciones de Spark SQL y PySpark **exportado del
motor** y versionado para que un agente lo consulte. Las dos skills que ya están instaladas cubren
la ejecución y la operación en Fabric, así que `spark-for-agents` no las duplica: las complementa, y
sus fichas deben enlazarlas para «dónde correr esto» en vez de repetir su contenido. La exportación
del §2 puede correr en Fabric por el mismo camino de Livy que documenta `etl:executing-spark`.

## 4. Piezas de la v0.1

1. Script de exportación + JSON del catálogo (Spark SQL y PySpark) para una versión de Spark.
2. Generador de fichas (`skills/spark-reference/generated/`), escrito solo por el script.
3. Skill `spark-reference` que lee las fichas, y skill `spark-feedback`.
4. `.claude-plugin/` (plugin.json + marketplace.json) y `PRIVACY.md`.
5. Columna de Fabric: exportación en el runtime vigente de Fabric.
6. Nodo de la capa `etl` (ADR 0023): `node.json`.

## 5. Salida de pre-release

Cuando las piezas 1–4 estén en `main` y una prueba de invención (como la de
`powerquery-m-for-agents`) muestre la mejora, se quita el aviso de pre-release y se propone a
Cristóbal enviarlo al directorio de plugins.
