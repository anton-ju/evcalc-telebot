CREATE DATABASE PD
    WITH 
    OWNER = postgres
    ENCODING = 'UTF8'
    CONNECTION LIMIT = -1;

CREATE TABLE EvCalc (
	--ec_id			int PRIMARY KEY,
	date			timestamp,
    table_id		bigint,
	hand_id			bigint,
	hero			varchar(25),
	hero_cards		varchar(4),
	ai_equity		DECIMAL(7,2), 
    won_amount		DECIMAL(7,2),
	icm_ev_diff		int,
	icm_ev_diff_cur	DECIMAL(7,2),
	chip_won		DECIMAL(7,2),
	chip_ev_diff	DECIMAL(7,2),
	bi				DECIMAL(7,2)
);

CREATE INDEX "TableHandHero"
    ON public.evcalc USING btree
    (date ASC NULLS LAST, hero ASC NULLS LAST)
;
