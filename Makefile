all: geodata/tl_2016_us_cbsa.shp geodata/tl_2016_us_state.shp

geodata/tl_2016_us_cbsa.shp:
	mkdir -pv geodata/tmp
	curl -sL https://www2.census.gov/geo/tiger/TIGER2016/CBSA/tl_2016_us_cbsa.zip \
		-o geodata/tmp/tl_2016_us_cbsa.zip
	unzip -qd geodata/tmp -o geodata/tmp/tl_2016_us_cbsa.zip tl_2016_us_cbsa.shp \
		tl_2016_us_cbsa.shx tl_2016_us_cbsa.prj tl_2016_us_cbsa.dbf tl_2016_us_cbsa.cpg
	# Limit to just California and Nevada for now
	ogr2ogr -spat -115.07 41.61 -124.89 32.45 -overwrite $@ geodata/tmp/tl_2016_us_cbsa.shp

geodata/tl_2016_us_state.shp:
	mkdir -pv geodata/tmp
	curl -sL https://www2.census.gov/geo/tiger/TIGER2016/STATE/tl_2016_us_state.zip \
		-o geodata/tmp/tl_2016_us_state.zip
	unzip -qd geodata/tmp -o geodata/tmp/tl_2016_us_state.zip tl_2016_us_state.shp \
		tl_2016_us_state.shx tl_2016_us_state.prj tl_2016_us_state.dbf tl_2016_us_state.cpg
	# Limit to just California and Nevada for now
	ogr2ogr -where "STATEFP in ('06', '32')" -overwrite $@ geodata/tmp/tl_2016_us_state.shp
