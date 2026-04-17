CREATE TABLE IF NOT EXISTS dim.dim_delivery_method (
    delivery_method_key     INTEGER         NOT NULL,
    delivery_method_name    VARCHAR(50)     NOT NULL,
    ship_base               NUMERIC(19,4),
    ship_rate               NUMERIC(19,4),
    CONSTRAINT pk_dim_delivery_method PRIMARY KEY (delivery_method_key)
);
