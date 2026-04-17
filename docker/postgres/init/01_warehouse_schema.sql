CREATE SCHEMA IF NOT EXISTS dim;
CREATE SCHEMA IF NOT EXISTS fact;

CREATE TABLE IF NOT EXISTS dim.dim_product (
    product_key       INTEGER      NOT NULL,
    product_code      VARCHAR(25)  NOT NULL,
    product_name      VARCHAR(50)  NOT NULL,
    subcategory_key   INTEGER,
    subcategory_name  VARCHAR(50),
    category_key      INTEGER,
    category_name     VARCHAR(50),
    CONSTRAINT pk_dim_product PRIMARY KEY (product_key)
);

CREATE TABLE IF NOT EXISTS dim.dim_date (
    date_key        INTEGER     NOT NULL,
    full_date       DATE        NOT NULL,
    year            SMALLINT    NOT NULL,
    quarter         SMALLINT    NOT NULL,
    month           SMALLINT    NOT NULL,
    month_name      VARCHAR(9)  NOT NULL,
    week_of_year    SMALLINT    NOT NULL,
    day_of_month    SMALLINT    NOT NULL,
    day_of_week     SMALLINT    NOT NULL,
    day_name        VARCHAR(9)  NOT NULL,
    is_weekend      BOOLEAN     NOT NULL,
    CONSTRAINT pk_dim_date PRIMARY KEY (date_key)
);

CREATE TABLE IF NOT EXISTS dim.dim_customer (
    customer_key    INTEGER      NOT NULL,
    account_number  VARCHAR(10)  NOT NULL,
    first_name      VARCHAR(50),
    last_name       VARCHAR(50),
    full_name       VARCHAR(101),
    territory_key   INTEGER,
    territory_name  VARCHAR(50),
    CONSTRAINT pk_dim_customer PRIMARY KEY (customer_key)
);

CREATE TABLE IF NOT EXISTS dim.dim_territory (
    territory_key         INTEGER      NOT NULL,
    territory_name        VARCHAR(50)  NOT NULL,
    country_region_code   VARCHAR(3)   NOT NULL,
    region_group          VARCHAR(50)  NOT NULL,
    CONSTRAINT pk_dim_territory PRIMARY KEY (territory_key)
);

CREATE TABLE IF NOT EXISTS fact.fact_online_sales (
    sales_order_key     BIGINT          NOT NULL,
    order_date_key      INTEGER         NOT NULL,
    customer_key        INTEGER,
    product_key         INTEGER         NOT NULL,
    territory_key       INTEGER,
    order_qty           SMALLINT        NOT NULL,
    unit_price          NUMERIC(19,4)   NOT NULL,
    unit_price_discount NUMERIC(19,4)   NOT NULL DEFAULT 0,
    line_total          NUMERIC(19,4)   NOT NULL,
    sub_total           NUMERIC(19,4),
    tax_amt             NUMERIC(19,4),
    freight             NUMERIC(19,4),
    total_due           NUMERIC(19,4),
    CONSTRAINT pk_fact_online_sales PRIMARY KEY (sales_order_key)
);
