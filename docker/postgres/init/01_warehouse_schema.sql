CREATE SCHEMA IF NOT EXISTS dim;

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
