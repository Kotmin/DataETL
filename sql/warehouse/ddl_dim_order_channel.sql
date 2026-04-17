CREATE TABLE IF NOT EXISTS dim.dim_order_channel (
    order_channel_key   INTEGER      NOT NULL,
    channel_name        VARCHAR(20)  NOT NULL,
    online_flag         BOOLEAN      NOT NULL,
    CONSTRAINT pk_dim_order_channel PRIMARY KEY (order_channel_key)
);
