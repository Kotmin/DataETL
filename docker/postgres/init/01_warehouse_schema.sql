CREATE SCHEMA IF NOT EXISTS dim;
CREATE SCHEMA IF NOT EXISTS fact;

CREATE TABLE IF NOT EXISTS dim.dim_product (
    product_key       INTEGER      NOT NULL,
    product_code      VARCHAR(12)  NOT NULL,
    product_name      VARCHAR(40)  NOT NULL,
    subcategory_key   SMALLINT,
    subcategory_name  VARCHAR(40),
    category_key      SMALLINT,
    category_name     VARCHAR(30),
    CONSTRAINT pk_dim_product PRIMARY KEY (product_key)
);

CREATE TABLE IF NOT EXISTS dim.dim_date (
    date_key              INTEGER     NOT NULL,
    full_date             DATE        NOT NULL,
    calendar_year         SMALLINT    NOT NULL,
    calendar_quarter      SMALLINT    NOT NULL,
    month_number_of_year  SMALLINT    NOT NULL,
    month_name            VARCHAR(12) NOT NULL,
    week_number_of_year   SMALLINT    NOT NULL,
    day_number_of_year    SMALLINT    NOT NULL,
    day_number_of_month   SMALLINT    NOT NULL,
    day_number_of_week    SMALLINT    NOT NULL,
    day_name_of_week      VARCHAR(12) NOT NULL,
    is_weekend            BOOLEAN     NOT NULL,
    CONSTRAINT pk_dim_date PRIMARY KEY (date_key)
);

CREATE TABLE IF NOT EXISTS dim.dim_customer (
    customer_key   BIGINT       NOT NULL,
    first_name     VARCHAR(25),
    last_name      VARCHAR(45),
    geography_key  SMALLINT,
    CONSTRAINT pk_dim_customer PRIMARY KEY (customer_key)
);

CREATE TABLE IF NOT EXISTS dim.dim_sales_territory (
    sales_territory_key  SMALLINT     NOT NULL,
    sales_territory_name VARCHAR(50)  NOT NULL,
    country_key          SMALLINT     NOT NULL,
    country_name         VARCHAR(50)  NOT NULL,
    country_code         CHAR(2)      NOT NULL,
    CONSTRAINT pk_dim_sales_territory PRIMARY KEY (sales_territory_key)
);

CREATE TABLE IF NOT EXISTS dim.dim_order_channel (
    order_channel_key  SMALLINT     NOT NULL,
    channel_name       VARCHAR(20)  NOT NULL,
    CONSTRAINT pk_dim_order_channel PRIMARY KEY (order_channel_key)
);

CREATE TABLE IF NOT EXISTS dim.dim_payment_method (
    payment_method_key   SMALLINT    NOT NULL,
    payment_method_name  VARCHAR(20) NOT NULL,
    CONSTRAINT pk_dim_payment_method PRIMARY KEY (payment_method_key)
);

CREATE TABLE IF NOT EXISTS dim.dim_geography (
    geography_key       SMALLINT     NOT NULL,
    country_key         SMALLINT     NOT NULL,
    country_name        VARCHAR(50)  NOT NULL,
    country_code        CHAR(2)      NOT NULL,
    city_key            SMALLINT     NOT NULL,
    city_name           VARCHAR(30)  NOT NULL,
    sales_territory_key SMALLINT,
    CONSTRAINT pk_dim_geography PRIMARY KEY (geography_key)
);

CREATE TABLE IF NOT EXISTS dim.dim_delivery_method (
    delivery_method_key   SMALLINT        NOT NULL,
    delivery_method_name  VARCHAR(20)     NOT NULL,
    CONSTRAINT pk_dim_delivery_method PRIMARY KEY (delivery_method_key)
);

CREATE TABLE IF NOT EXISTS fact.fact_online_sales (
    order_key           VARCHAR(10)   NOT NULL,
    order_line_number   SMALLINT      NOT NULL,
    customer_key        BIGINT,
    product_key         INTEGER       NOT NULL,
    sales_territory_key SMALLINT,
    channel_key         SMALLINT      NOT NULL DEFAULT 1,
    payment_method_key  SMALLINT,
    delivery_method_key SMALLINT,
    order_date_key      INTEGER       NOT NULL,
    ship_date_key       INTEGER,
    quantity            SMALLINT      NOT NULL,
    catalog_price       NUMERIC(7,2)  NOT NULL,
    discount_amount     NUMERIC(7,2)  NOT NULL DEFAULT 0,
    discount_pctg       SMALLINT      NOT NULL DEFAULT 0,
    transaction_price   NUMERIC(7,2)  NOT NULL,
    delivery_cost       NUMERIC(7,2),
    product_cost        NUMERIC(8,2),
    CONSTRAINT pk_fact_online_sales PRIMARY KEY (order_key, order_line_number)
);
