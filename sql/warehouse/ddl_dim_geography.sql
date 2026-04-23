CREATE TABLE IF NOT EXISTS dim.dim_geography (
    geography_key       SMALLINT     NOT NULL,
    country_key         SMALLINT     NOT NULL,
    country_name        VARCHAR(50)  NOT NULL,
    country_code        CHAR(2)      NOT NULL,
    city_key            SMALLINT     NOT NULL,
    city_name           VARCHAR(30)  NOT NULL,
    state_province_code VARCHAR(3),
    state_province_name VARCHAR(50),
    sales_territory_key SMALLINT,
    CONSTRAINT pk_dim_geography PRIMARY KEY (geography_key)
);
