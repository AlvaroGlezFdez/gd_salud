-- =============================================================================
-- Data Warehouse: saleshealth_dwh
-- Modelo dimensional — Star Schema
-- Motor destino: SQLite 3
-- Autor: Álvaro González Fernández — Gestión de Datos (UAX)
-- =============================================================================

PRAGMA foreign_keys = ON;

-- -----------------------------------------------------------------------------
-- DROPS (idempotencia — permite re-ejecutar el script sin errores)
-- -----------------------------------------------------------------------------
DROP TABLE IF EXISTS fact_sales;
DROP TABLE IF EXISTS dim_customer;
DROP TABLE IF EXISTS dim_product;
DROP TABLE IF EXISTS dim_store;
DROP TABLE IF EXISTS dim_date;
DROP TABLE IF EXISTS dim_offer;

-- =============================================================================
-- DIMENSIONES
-- =============================================================================

-- -----------------------------------------------------------------------------
-- dim_customer — perfil del cliente
-- -----------------------------------------------------------------------------
CREATE TABLE dim_customer (
    customer_id   INTEGER PRIMARY KEY,
    first_name    TEXT    NOT NULL,
    last_name     TEXT    NOT NULL,
    email         TEXT,
    phone         TEXT,
    created_at    TEXT
);

-- -----------------------------------------------------------------------------
-- dim_product — catálogo de producto desnormalizado
--   (incluye atributos de category y brand para evitar joins en consulta)
-- -----------------------------------------------------------------------------
CREATE TABLE dim_product (
    product_id    INTEGER PRIMARY KEY,
    name          TEXT    NOT NULL,
    category      TEXT,
    manufacturer  TEXT,
    unit_cost     REAL,
    unit_price    REAL,
    brand_name    TEXT,
    category_name TEXT
);

-- -----------------------------------------------------------------------------
-- dim_store — tienda física (incluye atributos de city_zone desnormalizados)
-- -----------------------------------------------------------------------------
CREATE TABLE dim_store (
    store_id         INTEGER PRIMARY KEY,
    name             TEXT    NOT NULL,
    address          TEXT,
    city             TEXT,
    postal_code      TEXT,
    district         TEXT,
    area_type        TEXT,
    zone_orientation TEXT
);

-- -----------------------------------------------------------------------------
-- dim_date — calendario (granularidad: día)
-- -----------------------------------------------------------------------------
CREATE TABLE dim_date (
    date_id      INTEGER PRIMARY KEY,    -- formato YYYYMMDD
    date         TEXT    NOT NULL UNIQUE,
    year         INTEGER NOT NULL,
    quarter      INTEGER NOT NULL,
    month        INTEGER NOT NULL,
    week         INTEGER,
    day_of_week  INTEGER,                -- 1=lunes ... 7=domingo
    is_weekend   INTEGER NOT NULL DEFAULT 0  -- 0/1
);

-- -----------------------------------------------------------------------------
-- dim_offer — promociones aplicadas a las ventas
-- -----------------------------------------------------------------------------
CREATE TABLE dim_offer (
    offer_id         INTEGER PRIMARY KEY,
    name             TEXT    NOT NULL,
    discount_percent REAL    NOT NULL,
    start_date       TEXT,
    end_date         TEXT
);

-- =============================================================================
-- TABLA DE HECHOS
-- =============================================================================

-- -----------------------------------------------------------------------------
-- fact_sales — granularidad: línea de venta (sale_item)
--   Métricas aditivas: quantity, subtotal, unit_cost, margin
--   Métricas semi-aditivas: unit_price (no se suma; se promedia)
-- -----------------------------------------------------------------------------
CREATE TABLE fact_sales (
    sale_item_id  INTEGER PRIMARY KEY,
    sale_id       INTEGER NOT NULL,                                    -- agrupador de ticket
    customer_id   INTEGER NOT NULL REFERENCES dim_customer(customer_id),
    product_id    INTEGER NOT NULL REFERENCES dim_product(product_id),
    store_id      INTEGER NOT NULL REFERENCES dim_store(store_id),
    date_id       INTEGER NOT NULL REFERENCES dim_date(date_id),
    offer_id      INTEGER          REFERENCES dim_offer(offer_id),     -- nullable: puede no haber oferta
    quantity      INTEGER NOT NULL CHECK (quantity > 0),
    unit_price    REAL    NOT NULL CHECK (unit_price >= 0),
    subtotal      REAL    NOT NULL CHECK (subtotal >= 0),
    unit_cost     REAL    NOT NULL CHECK (unit_cost  >= 0),
    margin        REAL    NOT NULL
);

-- -----------------------------------------------------------------------------
-- Índices sobre las FKs del fact (aceleran los star joins)
-- -----------------------------------------------------------------------------
CREATE INDEX idx_fact_sales_customer ON fact_sales(customer_id);
CREATE INDEX idx_fact_sales_product  ON fact_sales(product_id);
CREATE INDEX idx_fact_sales_store    ON fact_sales(store_id);
CREATE INDEX idx_fact_sales_date     ON fact_sales(date_id);
CREATE INDEX idx_fact_sales_offer    ON fact_sales(offer_id);
CREATE INDEX idx_fact_sales_sale     ON fact_sales(sale_id);
