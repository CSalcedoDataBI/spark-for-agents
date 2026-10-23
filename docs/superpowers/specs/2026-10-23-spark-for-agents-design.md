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
