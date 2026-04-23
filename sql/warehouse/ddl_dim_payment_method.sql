CREATE TABLE IF NOT EXISTS dim.dim_payment_method (
    payment_method_key   SMALLINT    NOT NULL,
    payment_method_name  VARCHAR(20) NOT NULL,
    CONSTRAINT pk_dim_payment_method PRIMARY KEY (payment_method_key)
);
