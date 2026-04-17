CREATE TABLE IF NOT EXISTS dim.dim_date (
    date_key        INTEGER     NOT NULL,
    full_date       DATE        NOT NULL,
    year            SMALLINT    NOT NULL,
    quarter         SMALLINT    NOT NULL,
    month           SMALLINT    NOT NULL,
    month_name      VARCHAR(9)  NOT NULL,
    week_of_year    SMALLINT    NOT NULL,
    day_of_month    SMALLINT    NOT NULL,
    day_of_week     SMALLINT    NOT NULL,
    day_name        VARCHAR(9)  NOT NULL,
    is_weekend      BOOLEAN     NOT NULL,
    CONSTRAINT pk_dim_date PRIMARY KEY (date_key)
);
