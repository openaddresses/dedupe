''' Import OpenAddresses data to a new Postgres table.

Initializes addresses table, and searches for OpenAddresses data files
in /tmp/us/??/*.vrt, which should match file structure of a partial U.S.-only
download from https://results.openaddresses.io

Sample shell command to prepare Montana for import:

unzip -l openaddr-collected-us_west.zip \
    | egrep '\sus/mt/.*' -o \
    | xargs unzip -o openaddr-collected-us_west.zip
'''
import glob, psycopg2, re
from osgeo import ogr

with psycopg2.connect('postgres://oa:oa@localhost/oa') as conn:
    with conn.cursor() as db:
        
        db.execute('''
            drop table if exists addresses;
            
            create table addresses
            (
                source      text,
                number      text,
                street      text,
                unit        text,
                city        text,
                district    text,
                region      text,
                postcode    text,
                hash        text,
                location    geometry(point, 4326)
            )
            ''')
    
        filenames = glob.glob('/tmp/us/??/*.vrt')
        
        for (index, fn) in enumerate(filenames):
            print('{}/{} {}...'.format(index + 1, len(filenames), fn))
            source = re.sub(r'^/tmp/(us.+)\.vrt$', r'\1', fn)
            ds = ogr.Open(fn)
            for feat in ds.GetLayer():
                location = feat.GetGeometryRef().ExportToWkt()
                number, street, unit, city, district, region, postcode, hash \
                    = [feat.GetField(k) for k in ('NUMBER', 'STREET', 'UNIT',
                       'CITY', 'DISTRICT', 'REGION', 'POSTCODE', 'HASH')]
                db.execute('''
                    insert into addresses
                    (source, number, street, unit, city, district, region, postcode,
                     hash, location) values (%s, %s, %s, %s, %s, %s, %s, %s, %s,
                     ST_SetSRID(%s::geometry, 4326))''', (source, number, street,
                     unit, city, district, region, postcode, hash, location))

        db.execute('''
            create index addresses_gix on addresses using gist (location);
            ''')
