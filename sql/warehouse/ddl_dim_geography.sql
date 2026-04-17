CREATE TABLE IF NOT EXISTS dim.dim_geography (
    geography_key       INTEGER      NOT NULL,
    address_line1       VARCHAR(60),
    city                VARCHAR(30)  NOT NULL,
    state_province_code VARCHAR(3),
    state_province_name VARCHAR(50),
    country_region_code VARCHAR(3)   NOT NULL,
    country_name        VARCHAR(50)  NOT NULL,
    postal_code         VARCHAR(15),
    CONSTRAINT pk_dim_geography PRIMARY KEY (geography_key)
);
