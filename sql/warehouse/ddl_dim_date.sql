CREATE TABLE IF NOT EXISTS dim.dim_date (
    date_key              INTEGER     NOT NULL,
    full_date             DATE        NOT NULL,
    calendar_year         SMALLINT    NOT NULL,
    calendar_quarter      SMALLINT    NOT NULL,
    month_number_of_year  SMALLINT    NOT NULL,
    month_name            VARCHAR(12) NOT NULL,
    week_number_of_year   SMALLINT    NOT NULL,
    day_number_of_year    SMALLINT    NOT NULL,
    day_number_of_month   SMALLINT    NOT NULL,
    day_number_of_week    SMALLINT    NOT NULL,
    day_name_of_week      VARCHAR(12) NOT NULL,
    is_weekend            BOOLEAN     NOT NULL,
    CONSTRAINT pk_dim_date PRIMARY KEY (date_key)
);
