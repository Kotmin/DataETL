CREATE TABLE IF NOT EXISTS dim.dim_territory (
    territory_key         INTEGER      NOT NULL,
    territory_name        VARCHAR(50)  NOT NULL,
    country_region_code   VARCHAR(3)   NOT NULL,
    region_group          VARCHAR(50)  NOT NULL,
    CONSTRAINT pk_dim_territory PRIMARY KEY (territory_key)
);
