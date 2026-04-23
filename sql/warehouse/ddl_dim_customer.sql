CREATE TABLE IF NOT EXISTS dim.dim_customer (
    customer_key   BIGINT       NOT NULL,
    first_name     VARCHAR(25),
    last_name      VARCHAR(45),
    geography_key  SMALLINT,
    CONSTRAINT pk_dim_customer PRIMARY KEY (customer_key)
);
