CREATE TABLE IF NOT EXISTS dim.dim_sales_territory (
    sales_territory_key  SMALLINT     NOT NULL,
    sales_territory_name VARCHAR(50)  NOT NULL,
    country_key          SMALLINT     NOT NULL,
    country_name         VARCHAR(50)  NOT NULL,
    country_code         CHAR(2)      NOT NULL,
    CONSTRAINT pk_dim_sales_territory PRIMARY KEY (sales_territory_key)
);
