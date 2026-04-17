# PRD — AdventureWorks ETL Teaching Lab

## 1. Document Control
- **Project name:** AdventureWorks ETL Teaching Lab
- **Version:** 0.1
- **Status:** Draft
- **Audience:** University students, instructors
- **Primary owner:** Course team

## 2. Problem Statement
Students need a deterministic, reproducible lab that demonstrates how a normalized OLTP schema is transformed into a dimensional model with fact and dimension tables. The lab should be simple to run on student laptops, visual enough for teaching, and structured so it can later be extended to Spark / Databricks.

## 3. Goals
1. Demonstrate OLTP → dimensional modeling using AdventureWorks.
2. Keep almost the entire environment dockerized.
3. Support Ubuntu natively and Windows via WSL2.
4. Use Apache Airflow for orchestration.
5. Load a target warehouse that can be connected to BI tools such as Power BI or Tableau.
6. Deliver a first working PoC for `DimProduct`.

## 4. Non-Goals (Phase 1)
- SCD Type 2
- CDC / streaming ingestion
- Production secrets vault
- HA Airflow deployment
- Kubernetes
- Databricks as the primary runtime
- Full fact-table parity before source-to-target mapping is finalized

## 5. Users
### Primary users
- Students learning ETL, orchestration, dimensional modeling, and BI basics

### Secondary users
- Instructors running guided labs
- Course assistants debugging student setups

## 6. Scope
### In scope
- Local runnable lab
- Dockerized source and warehouse databases
- Airflow running locally outside Docker
- Source data supplied in one of two modes:
  - SQL Server container seeded with AdventureWorks OLTP
  - CSV-backed source package loaded into a relational source facade
- Initial target warehouse in PostgreSQL
- First dimensional PoC: `DimProduct`
- Basic observability, logs, and row-count validation

### Out of scope
- Finalized full fact schema
- Enterprise deployment patterns
- Advanced Spark optimization
- Multi-user shared lab platform

## 7. Recommended Architecture

### 7.1 Runtime choice
**Recommended Phase 1 architecture**
- **Host OS:** Ubuntu, or Windows with WSL2
- **Orchestrator:** Apache Airflow (installed locally, not containerized)
- **Source option A (preferred):** SQL Server container seeded with AdventureWorks OLTP
- **Source option B:** CSV package loaded into a lightweight relational source facade
- **Target warehouse:** PostgreSQL container
- **Visualization:** Power BI, Tableau, DBeaver, Azure Data Studio, pgAdmin, Metabase, Superset

### 7.2 Why this choice
- Airflow is easier to explain visually as a DAG-based ETL orchestrator.
- Local Airflow avoids classroom instability caused by quota-limited cloud workspaces.
- PostgreSQL is easy to run, inspect, and connect to from BI tools.
- SQL Server in Docker preserves the true AdventureWorks OLTP structure.

## 8. Platform Constraints and Assumptions
1. Students may use Ubuntu or Windows laptops.
2. Windows users are expected to run the lab through **WSL2**.
3. Docker Desktop or Docker Engine must be available.
4. Containers must use persistent volumes so that database state survives restarts.
5. The lab must support offline re-runs once images and seed files are downloaded.
6. Airflow will orchestrate full reloads first; incremental loads are deferred.

## 9. Source Data Options

### Option A — SQL Server container with AdventureWorks OLTP (recommended)
**Description**
Run SQL Server in Docker and seed it with AdventureWorks OLTP.

**Pros**
- Closest to the real Microsoft sample
- Best for teaching normalized OLTP joins
- Easiest source-to-target mapping discussion
- Lets students query the real source schema

**Cons**
- Heavier than CSV
- Requires SQL Server image and seeding step
- ARM/Mac support may need extra handling if introduced later

**Decision**
Use as the default teaching source.

### Option B — CSV edition with relational facade
**Description**
Use the AdventureWorks CSV package and load it into a lightweight relational store so the app still queries SQL tables.

**Implementation choices**
- PostgreSQL source schema named `src_*`
- SQLite for a very small local PoC
- DuckDB for read-oriented demonstrations

**Recommended approach for CSV mode**
Load CSV files into a **PostgreSQL source schema** and treat that schema as the OLTP facade.

**Why not SQLite as the primary facade**
- weaker parity with SQL Server types and constraints
- more differences in SQL behavior
- less useful when teaching real ETL into a separate warehouse

**Pros**
- Very portable
- Simple to reseed from CSV
- Works well if SQL Server is unavailable

**Cons**
- Less faithful to the original OLTP platform
- Requires custom DDL and load scripts
- Relationship enforcement is your responsibility

**Decision**
Keep as fallback mode, not the primary path.

## 10. Target Warehouse Options

### Recommended target
**PostgreSQL** as the dimensional warehouse.

### Why PostgreSQL
- easy local Docker setup
- simple SQL for warehouse tables
- strong compatibility with BI tools
- easy for students to inspect and reset

### Other possible targets
- SQL Server as both source and target
- DuckDB for tiny local-only demonstrations
- SQLite only for the smallest conceptual demo

### Decision
Use **PostgreSQL** as the default target warehouse.

## 11. Visualization / Dashboarding Options
The warehouse should be queryable by:
- **Power BI**
- **Tableau**
- **Metabase**
- **Apache Superset**
- **pgAdmin / DBeaver / Azure Data Studio** for direct SQL exploration

### Recommended classroom BI path
- Primary: **Power BI** or **Tableau** if available institutionally
- Fully dockerized alternative: **Metabase** or **Superset**

## 12. Functional Requirements
1. The environment must start with a small number of commands.
2. The source database must be pre-seeded or seedable deterministically.
3. Airflow must expose a DAG that students can trigger manually.
4. The DAG must extract from the source, transform, and load the target warehouse.
5. The first PoC must build `DimProduct`.
6. The target must be connectable by at least one BI tool.
7. The lab must support a reset path that returns the environment to a known state.

## 13. Non-Functional Requirements
- **Reproducibility:** same result on repeated lab runs
- **Simplicity:** minimal setup friction for students
- **Observability:** logs and task-level status visible in Airflow
- **Portability:** support Ubuntu and Windows via WSL2
- **Performance:** finish PoC loads in classroom-friendly time
- **Maintainability:** SQL and Python code readable by juniors

## 14. Initial Data Model Scope
### Confirmed first dimension
- `DimProduct`

### Planned later dimensions
- `DimDate`
- `DimCustomer`
- `DimGeography`
- `DimSalesTerritory`
- potentially modeled `DimPaymentMethod`
- potentially modeled `DimDeliveryMethod`

### Planned fact area
- `FactOnlineSales`

> Note: final fact field mapping is explicitly deferred until source-to-target mapping is finalized.

## 15. PoC — DimProduct

### Objective
Build `DimProduct` deterministically from AdventureWorks OLTP.

### Target columns
- `ProductKey`
- `ProductCode`
- `ProductName`
- `SubcategoryKey`
- `SubcategoryName`
- `CategoryKey`
- `CategoryName`

### Expected source tables
- `Production.Product`
- `Production.ProductSubcategory`
- `Production.ProductCategory`

### Load pattern
- Phase 1: full reload (`TRUNCATE + INSERT`)
- Phase 2: optional idempotent upsert

### Validation checks
- row count > 0
- `ProductKey` is unique
- `ProductKey` is not null
- row count equals source product count

## 16. Environment Design

### 16.1 Components
- `sqlserver` container — AdventureWorks source
- `postgres` container — warehouse target
- optional `metabase` or `superset` container — dashboarding
- local `airflow` install — orchestration and UI

### 16.2 Suggested repository structure
```text
project/
  docker/
    sqlserver/
      init/
    postgres/
      init/
  airflow/
    dags/
    plugins/
    include/
  sql/
    source/
    warehouse/
    transforms/
  seeds/
    adventureworks/
  docs/
    PRD.md
    source_to_target_mapping.md
  scripts/
    bootstrap.sh
    reset_env.sh
```

### 16.3 Reset strategy
- remove and recreate warehouse schema
- optionally rebuild source database from seed
- clear Airflow task history only when needed for teaching

## 17. Risks and Mitigations

### Risk 1 — Student OS differences
**Mitigation:** standardize on Ubuntu or Windows+WSL2 only.

### Risk 2 — SQL Server container setup complexity
**Mitigation:** provide a prebuilt seeding script and fallback CSV mode.

### Risk 3 — BI licensing or desktop install friction
**Mitigation:** support Metabase or Superset as optional browser-based alternatives.

### Risk 4 — Airflow environment drift
**Mitigation:** pin Python and Airflow versions; provide a bootstrap script.

## 18. Decisions Taken So Far
1. Use **Apache Airflow** as the primary orchestrator.
2. Keep **Airflow outside Docker** for the first lab iteration.
3. Dockerize almost everything else.
4. Prefer **SQL Server + AdventureWorks OLTP** as the primary source.
5. Keep **CSV-backed relational facade** as fallback source mode.
6. Use **PostgreSQL** as the target warehouse.
7. Deliver **PRD + source-to-target mapping + DimProduct PoC** first.

## 19. Open Questions
1. Which exact AdventureWorks version will be used?
2. Should source seeding be from `.bak`, SQL script, or CSV loader?
3. Do we want one-command bootstrap for both Ubuntu and WSL2?
4. Which BI tool is guaranteed to be available in the university environment?
5. Should the first release include a browser-based BI container by default?
6. Should source and warehouse both persist to local Docker volumes?

## 20. Milestones
### Milestone 1 — Architecture lock
- finalize runtime choice
- finalize source mode A/B
- finalize warehouse target

### Milestone 2 — Environment bootstrap
- Docker Compose for SQL Server + PostgreSQL
- Airflow local install instructions
- health checks and reset scripts

### Milestone 3 — Mapping spec
- source-to-target mapping for `DimProduct`
- data type normalization rules
- null handling rules

### Milestone 4 — PoC implementation
- build and run `DimProduct`
- validate row counts and constraints
- expose results in SQL and dashboard tool

### Milestone 5 — Phase 2 planning
- `DimDate`
- draft `FactOnlineSales`
- optional Databricks/Spark comparison lab

## 21. Success Criteria
The PoC is successful when:
1. A student can start the environment on Ubuntu or Windows+WSL2.
2. Airflow can run a DAG that loads `DimProduct` end-to-end.
3. The target PostgreSQL warehouse can be queried from a BI tool.
4. The results are deterministic across reruns.
5. The setup can be explained and executed in a classroom session.
