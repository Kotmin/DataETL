# DataETL — Project Instructions

## DAG Reference

`docs/dag_reference.md` is the canonical catalog of all Airflow DAGs.
**Update it whenever a DAG is added, removed, or its source/target changes.**
It includes execution order, FK resolution notes, and instructions for adding new DAGs.

## Adding a New Dimension or Fact

Follow the checklist in `docs/dag_reference.md` → "Adding a New DAG".
Key files to touch: DAG file, extract SQL, warehouse DDL, init schema, mapping doc, dag_reference.

## Schema Source of Truth

- Target warehouse schema: `docker/postgres/init/01_warehouse_schema.sql`
- Column mapping with transform rules: `docs/source_to_target_mapping.md`
- OLTP source diagram: `docs/AdventureWorks OLTP Schema November.png`
- Target data mart diagram: `docs/desired_schema_datamark.png`

## Python

Always use `.venv/` for all Python work. Activate with `source .env && .venv/bin/python`.

## Airflow

Version: 3.2.0, standalone mode.
Start: `./scripts/start_airflow.sh`
Stop: `./scripts/reset_env.sh`
DAG execution order: see `docs/dag_reference.md`.

## Conventional Commits

All commits must follow `type(scope): description` format. Atomic commits per file or logical group.
