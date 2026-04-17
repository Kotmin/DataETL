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
