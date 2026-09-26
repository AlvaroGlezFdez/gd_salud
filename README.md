# SalesHealth — Data Warehouse & Customer Analytics
 
End-to-end data pipeline for a (fictional) health-products retailer, **SalesHealth**:
from a transactional PostgreSQL database to a dimensional data warehouse, an automated
ETL, business KPIs, customer segmentation and a churn model — plus an interactive
dashboard. Final project for the *Data Management* course (B.Sc. in Mathematical
Engineering, UAX). **Synthetic data.**
 
## Overview
 
The project builds a complete analytical environment on top of the `saleshealth`
transactional database (PostgreSQL 16, 17 tables covering ERP, CRM, sales, logistics and
after-sales) so the business can make data-driven decisions.
 
Volume: ~42,500 sale lines · 20,000 tickets · 5,750 customers · 2,330 returns · 50
products · 20 stores · ~3 years of activity.
 
## Pipeline
 
1. **Exploration** (`01_exploracion/`) — data profiling and Entity-Relationship diagram
   from the source foreign keys.
2. **Data Warehouse** (`02_dwh/`) — a **Kimball star schema** (1 fact + 5 dimensions)
   materialized in SQLite. Fact grain = sale line; dimensions: customer, product, store,
   date (generated calendar) and offer. Design decisions (star vs. snowflake, degenerate
   `sale_id`, additive vs. semi-additive measures, indexing) are documented in the report.
3. **ETL** (`03_etl/`) — transactional pipeline PostgreSQL → SQLite (SQLAlchemy +
   psycopg2, pandas), atomic per stage with `rollback` on failure, plus referential-
   integrity and data-quality validation at the end.
4. **Business metrics** (`04_metricas/`) — per-customer **CLTV**, **churn risk**
   (active / at-risk / lost) and **return rate**, computed on the DWH.
5. **Segmentation & churn model** (`05_clustering/`) — **PCA + K-Means** (k = 4:
   Regular, Lost, VIP Champion, Returner), and a binary **churn classifier** (Random
   Forest / XGBoost) with a temporal train/test split.
An interactive **dashboard** (`dashboard.py`) ties the results together.
 
## Note on the churn model
 
The classifier reaches a near-perfect AUC on this dataset. This is **not data leakage**:
the synthetic customer base is highly polarised (mostly one-time buyers vs. very frequent
VIPs), so *recency* separates the classes almost deterministically. On a production
dataset with more intermediate customers the AUC would drop — the pipeline is built to be
retrained on more gradual data. (Discussed in `memoria_proyecto.md`.)
 
## Tech stack
 
Python · pandas · scikit-learn · XGBoost · SQL (PostgreSQL → SQLite) · SQLAlchemy ·
Matplotlib · Streamlit
 
## Repository structure
 
```
├── 01_exploracion/   # profiling + ER diagram
├── 02_dwh/           # star-schema DDL, dimensional model, saleshealth_dwh.db
├── 03_etl/           # ETL notebook (PostgreSQL → SQLite)
├── 04_metricas/      # CLTV, churn risk, return rate
├── 05_clustering/    # PCA + K-Means segmentation, churn model
├── dashboard.py      # interactive dashboard
├── memoria_proyecto.md/.pdf   # full technical report
├── guia_dashboard.md/.pdf     # dashboard guide
├── saleshealthBackupGD.sql    # source PostgreSQL dump (synthetic)
└── docs/             # assignment brief
```
 
## How to run
 
```bash
pip install -r requirements.txt
# the SQLite data warehouse (02_dwh/saleshealth_dwh.db) is included;
# to rebuild from source, restore saleshealthBackupGD.sql into PostgreSQL and run 03_etl/etl.ipynb
streamlit run dashboard.py
```
 
Full methodology and design rationale in [`memoria_proyecto.md`](memoria_proyecto.md).
 
---
*Academic final project · Data Management · Universidad Alfonso X el Sabio (UAX) · 2025–2026. Synthetic data.*
