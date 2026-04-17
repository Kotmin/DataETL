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
