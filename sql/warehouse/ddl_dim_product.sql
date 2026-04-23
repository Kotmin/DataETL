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
